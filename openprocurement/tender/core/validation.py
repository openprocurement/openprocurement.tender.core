# -*- coding: utf-8 -*-
from openprocurement.api.validation import validate_data, validate_json_data
from openprocurement.api.utils import get_now  # move
from openprocurement.api.utils import update_logging_context  # XXX tender context
from openprocurement.tender.core.utils import calculate_business_date
from schematics.exceptions import ValidationError
from openprocurement.tender.core.utils import error_handler


def validate_tender_data(request):
    update_logging_context(request, {'tender_id': '__new__'})

    data = validate_json_data(request)
    if data is None:
        raise error_handler(request.errors)

    model = request.tender_from_data(data, create=False)
    #if not request.check_accreditation(model.create_accreditation):
    #if not any([request.check_accreditation(acc) for acc in getattr(model, 'create_accreditations', [getattr(model, 'create_accreditation', '')])]):
    if not any([request.check_accreditation(acc) for acc in iter(str(model.create_accreditation))]):
        request.errors.add('procurementMethodType', 'accreditation', 'Broker Accreditation level does not permit tender creation')
        request.errors.status = 403
        raise error_handler(request.errors)
    data = validate_data(request, model, data=data)
    if data and data.get('mode', None) is None and request.check_accreditation('t'):
        request.errors.add('procurementMethodType', 'mode', 'Broker Accreditation level does not permit tender creation')
        request.errors.status = 403
        raise error_handler(request.errors)
    if data and data.get('procuringEntity', {}).get('kind', '') not in model.procuring_entity_kinds:
        request.errors.add('procuringEntity',
                           'kind',
                           '{kind!r} procuringEntity cannot publish this type of procedure. '
                           'Only {kinds} are allowed.'.format(kind=data.get('procuringEntity', {}).get('kind', ''), kinds=', '.join(model.procuring_entity_kinds)))
        request.errors.status = 403


def validate_patch_tender_data(request):
    data = validate_json_data(request)
    if data is None:
        raise error_handler(request.errors)
    if request.context.status != 'draft':
        return validate_data(request, type(request.tender), True, data)
    default_status = type(request.tender).fields['status'].default
    if data.get('status') != default_status:
        request.errors.add('body', 'data', 'Can\'t update tender in current (draft) status')
        request.errors.status = 403
        raise error_handler(request.errors)
    request.validated['data'] = {'status': default_status}
    request.context.status = default_status


def validate_tender_auction_data(request):
    data = validate_patch_tender_data(request)
    tender = request.validated['tender']
    if tender.status != 'active.auction':
        request.errors.add('body', 'data', 'Can\'t {} in current ({}) tender status'.format('report auction results' if request.method == 'POST' else 'update auction urls', tender.status))
        request.errors.status = 403
        raise error_handler(request.errors)
    lot_id = request.matchdict.get('auction_lot_id')
    if tender.lots and any([i.status != 'active' for i in tender.lots if i.id == lot_id]):
        request.errors.add('body', 'data', 'Can {} only in active lot status'.format('report auction results' if request.method == 'POST' else 'update auction urls'))
        request.errors.status = 403
        raise error_handler(request.errors)
    if data is not None:
        bids = data.get('bids', [])
        tender_bids_ids = [i.id for i in tender.bids]
        if len(bids) != len(tender.bids):
            request.errors.add('body', 'bids', "Number of auction results did not match the number of tender bids")
            request.errors.status = 422
            raise error_handler(request.errors)
        if set([i['id'] for i in bids]) != set(tender_bids_ids):
            request.errors.add('body', 'bids', "Auction bids should be identical to the tender bids")
            request.errors.status = 422
            raise error_handler(request.errors)
        data['bids'] = [x for (y, x) in sorted(zip([tender_bids_ids.index(i['id']) for i in bids], bids))]
        if data.get('lots'):
            tender_lots_ids = [i.id for i in tender.lots]
            if len(data.get('lots', [])) != len(tender.lots):
                request.errors.add('body', 'lots', "Number of lots did not match the number of tender lots")
                request.errors.status = 422
                raise error_handler(request.errors)
            if set([i['id'] for i in data.get('lots', [])]) != set([i.id for i in tender.lots]):
                request.errors.add('body', 'lots', "Auction lots should be identical to the tender lots")
                request.errors.status = 422
                raise error_handler(request.errors)
            data['lots'] = [
                x if x['id'] == lot_id else {}
                for (y, x) in sorted(zip([tender_lots_ids.index(i['id']) for i in data.get('lots', [])], data.get('lots', [])))
            ]
        if tender.lots:
            for index, bid in enumerate(bids):
                if (getattr(tender.bids[index], 'status', 'active') or 'active') == 'active':
                    if len(bid.get('lotValues', [])) != len(tender.bids[index].lotValues):
                        request.errors.add('body', 'bids', [{u'lotValues': [u'Number of lots of auction results did not match the number of tender lots']}])
                        request.errors.status = 422
                        raise error_handler(request.errors)
                    for lot_index, lotValue in enumerate(tender.bids[index].lotValues):
                        if lotValue.relatedLot != bid.get('lotValues', [])[lot_index].get('relatedLot', None):
                            request.errors.add('body', 'bids', [{u'lotValues': [{u'relatedLot': ['relatedLot should be one of lots of bid']}]}])
                            request.errors.status = 422
                            raise error_handler(request.errors)
            for bid_index, bid in enumerate(data['bids']):
                if 'lotValues' in bid:
                    bid['lotValues'] = [
                        x if x['relatedLot'] == lot_id and (getattr(tender.bids[bid_index].lotValues[lotValue_index], 'status', 'active') or 'active') == 'active' else {}
                        for lotValue_index, x in enumerate(bid['lotValues'])
                    ]

    else:
        data = {}
    if request.method == 'POST':
        now = get_now().isoformat()
        if tender.lots:
            data['lots'] = [{'auctionPeriod': {'endDate': now}} if i.id == lot_id else {} for i in tender.lots]
        else:
            data['auctionPeriod'] = {'endDate': now}
    request.validated['data'] = data


def validate_bid_data(request):
    if not request.check_accreditation(request.tender.edit_accreditation):
        request.errors.add('procurementMethodType', 'accreditation', 'Broker Accreditation level does not permit bid creation')
        request.errors.status = 403
        raise error_handler(request.errors)
    if request.tender.get('mode', None) is None and request.check_accreditation('t'):
        request.errors.add('procurementMethodType', 'mode', 'Broker Accreditation level does not permit bid creation')
        request.errors.status = 403
        raise error_handler(request.errors)
    update_logging_context(request, {'bid_id': '__new__'})
    model = type(request.tender).bids.model_class
    return validate_data(request, model)


def validate_patch_bid_data(request):
    model = type(request.tender).bids.model_class
    return validate_data(request, model, True)


def validate_award_data(request):
    update_logging_context(request, {'award_id': '__new__'})
    model = type(request.tender).awards.model_class
    return validate_data(request, model)


def validate_patch_award_data(request):
    model = type(request.tender).awards.model_class
    return validate_data(request, model, True)


def validate_question_data(request):
    if not request.check_accreditation(request.tender.edit_accreditation):
        request.errors.add('procurementMethodType', 'accreditation', 'Broker Accreditation level does not permit question creation')
        request.errors.status = 403
        raise error_handler(request.errors)
    if request.tender.get('mode', None) is None and request.check_accreditation('t'):
        request.errors.add('procurementMethodType', 'mode', 'Broker Accreditation level does not permit question creation')
        request.errors.status = 403
        raise error_handler(request.errors)
    update_logging_context(request, {'question_id': '__new__'})
    model = type(request.tender).questions.model_class
    return validate_data(request, model)


def validate_patch_question_data(request):
    model = type(request.tender).questions.model_class
    return validate_data(request, model, True)


def validate_complaint_data(request):
    if not request.check_accreditation(request.tender.edit_accreditation):
        request.errors.add('procurementMethodType', 'accreditation', 'Broker Accreditation level does not permit complaint creation')
        request.errors.status = 403
        raise error_handler(request.errors)
    if request.tender.get('mode', None) is None and request.check_accreditation('t'):
        request.errors.add('procurementMethodType', 'mode', 'Broker Accreditation level does not permit complaint creation')
        request.errors.status = 403
        raise error_handler(request.errors)
    update_logging_context(request, {'complaint_id': '__new__'})
    model = type(request.tender).complaints.model_class
    return validate_data(request, model)


def validate_patch_complaint_data(request):
    model = type(request.tender).complaints.model_class
    return validate_data(request, model, True)


def validate_cancellation_data(request):
    update_logging_context(request, {'cancellation_id': '__new__'})
    model = type(request.tender).cancellations.model_class
    return validate_data(request, model)


def validate_patch_cancellation_data(request):
    model = type(request.tender).cancellations.model_class
    return validate_data(request, model, True)


def validate_contract_data(request):
    update_logging_context(request, {'contract_id': '__new__'})
    model = type(request.tender).contracts.model_class
    return validate_data(request, model)


def validate_patch_contract_data(request):
    model = type(request.tender).contracts.model_class
    return validate_data(request, model, True)


def validate_lot_data(request):
    update_logging_context(request, {'lot_id': '__new__'})
    model = type(request.tender).lots.model_class
    return validate_data(request, model)


def validate_patch_lot_data(request):
    model = type(request.tender).lots.model_class
    return validate_data(request, model, True)


def validate_LotValue_value(tender, relatedLot, value):
    lots = [i for i in tender.lots if i.id == relatedLot]
    if not lots:
        return
    lot = lots[0]
    if lot.value.amount < value.amount:
        raise ValidationError(u"value of bid should be less than value of lot")
    if lot.get('value').currency != value.currency:
        raise ValidationError(u"currency of bid should be identical to currency of value of lot")
    if lot.get('value').valueAddedTaxIncluded != value.valueAddedTaxIncluded:
        raise ValidationError(u"valueAddedTaxIncluded of bid should be identical to valueAddedTaxIncluded of value of lot")


#tender
def validate_tender_status_update_in_terminated_status(request, tender=None):
    tender = request.validated['tender']
    if request.authenticated_role != 'Administrator' and tender.status in ['complete', 'unsuccessful', 'cancelled']:
        request.errors.add('body', 'data', 'Can\'t update tender in current ({}) status'.format(tender.status))
        request.errors.status = 403
        raise error_handler(request.errors)


def validate_update_tender_status_not_in_pre_qualification(request, tender, data):
    if request.authenticated_role == 'tender_owner' and 'status' in data and data['status'] not in ['active.pre-qualification.stand-still', tender.status]:
        request.errors.add('body', 'data', 'Can\'t update tender status')
        request.errors.status = 403
        raise error_handler(request.errors)


def validate_tender_period_extension(request, tender, tendering_extra_period):
    if calculate_business_date(get_now(), tendering_extra_period, context=tender) > request.validated['tender'].tenderPeriod.endDate:
        request.errors.add('body', 'data', 'tenderPeriod should be extended by {0.days} days'.format(tendering_extra_period))
        request.errors.status = 403
        raise error_handler(request.errors)


def validate_tender_period_extension_request_validated(request, tendering_extra_period):
    if calculate_business_date(get_now(), tendering_extra_period, request.validated['tender']) > request.validated['tender'].tenderPeriod.endDate:
        request.errors.add('body', 'data', 'tenderPeriod should be extended by {0.days} days'.format(tendering_extra_period))
        request.errors.status = 403
        raise error_handler(request.errors)

#tender documents
def validate_operation_with_tender_document_in_not_allowed_status(request, operation):
    if request.authenticated_role != 'auction' and request.validated['tender_status'] != 'active.tendering' or \
       request.authenticated_role == 'auction' and request.validated['tender_status'] not in ['active.auction', 'active.qualification']:
        request.errors.add('body', 'data', 'Can\'t {} document in current ({}) tender status'.format(operation, request.validated['tender_status']))
        request.errors.status = 403
        raise error_handler(request.errors)


def validate_tender_period_extension_in_active_tendering(request, tendering_extra_period):
    if request.validated['tender_status'] == 'active.tendering' and calculate_business_date(get_now(), tendering_extra_period, request.validated['tender']) > request.validated['tender'].tenderPeriod.endDate:
        request.errors.add('body', 'data', 'tenderPeriod should be extended by {0.days} days'.format(tendering_extra_period))
        request.errors.status = 403
        raise error_handler(request.errors)
