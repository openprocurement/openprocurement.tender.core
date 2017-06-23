# -*- coding: utf-8 -*-
import unittest
from uuid import uuid4
from copy import deepcopy
from datetime import timedelta

from openprocurement.api.constants import (
    ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017,
    ADDITIONAL_CLASSIFICATIONS_SCHEMES
)
from openprocurement.tender.core.constants import (
    SERVICE_TIME, BID_LOTVALUES_VALIDATION_FROM,
    CPV_ITEMS_CLASS_FROM, AUCTION_STAND_STILL_TIME,
    CANT_DELETE_PERIOD_START_DATE_FROM
)
from openprocurement.tender.core.models import (
    ValidationError, get_now
)
from openprocurement.tender.core.models import (
    Tender as BaseTender, Lot, Item, Bid, Feature, Award,
    Complaint, Question, Parameter, PeriodEndRequired,
    LotValue, Contract, Document, Cancellation,
    TenderAuctionPeriod, LotAuctionPeriod
)
from openprocurement.tender.core.tests.base import (
    test_tender_data, test_organization,
    test_lots, test_bids, test_features,
    test_features_item
)


class Tender(BaseTender):
    complaints = []
    features = []
    awards = []
    items = []
    lots = []
    bids = []


class DummyModelsTest(unittest.TestCase):
    """
    Test case for checking models'
    serializable fields and validators
    """
    def test_Tender_model(self):
        from openprocurement.tender.core.models import (
            validate_lots_uniq, validate_features_uniq,
            validate_dkpp
        )
        from mock import Mock
        data = deepcopy(test_tender_data)

        tender = Tender({'mode': 'test'})
        tender.import_data(data)
        tender.validate()

        tender.lots = [Mock(id='duplicated_lot_id'),
                       Mock(id='duplicated_lot_id')]
        try:
            validate_lots_uniq(tender.lots)
        except ValidationError as e:
            self.assertIn('Lot id should be uniq for all lots', e.message)

        tender.features = [Mock(code='duplicated feature code'),
                           Mock(code='duplicated feature code')]
        try:
            validate_features_uniq(tender.features)
        except ValidationError as e:
            self.assertIn('Feature code should be uniq for all features', e.message)

        tender.items = [Mock(scheme='[TESTING]'),
                        Mock(scheme='random')]
        try:
            validate_dkpp(tender.items)
        except ValidationError as e:
            self.assertIn(u'One of additional classifications should be one of [{0}].'.format(', '.join(ADDITIONAL_CLASSIFICATIONS_SCHEMES)),
                          e.message)

    def test_Lot_model(self):
        """
        serializable fields:
            lot_value
            numberOfBids
            lot_guarantee
            lot_minimalStep
        validators:
            validate_minimalStep
        """
        from mock import Mock
        data = deepcopy(test_lots[0])
        tender = Tender()
        tender.value = Mock(currency='UAH', valueAddedTaxIncluded=True)
        tender.minimalStep = Mock(currency='UAH', valueAddedTaxIncluded=True)
        tender.guarantee = Mock(currency='UAH')

        data['minimalStep']['amount'] = 501
        data.update({'__parent__': tender,
                     'guarantee': {'amount': 100,
                                   'currency': 'UAH'}})
        lot = Lot()
        lot.import_data(data)
        self.assertEqual(lot.numberOfBids, 0)
        self.assertEqual(lot.lot_value.amount, 500)
        self.assertEqual(lot.lot_minimalStep.amount, 501)
        self.assertEqual(lot.lot_guarantee.amount, 100)

        # validate_minimalStep
        try:
            lot.validate()
        except ValidationError as e:
            self.assertIn('value should be less than value of lot',
                          e.message['minimalStep'])

    def test_Feature_model(self):
        """
        validators:
            validate_relatedItem
            validate_values_uniq
        """
        data = deepcopy(test_features[1])

        # validate_relatedItem
        data.update({'__parent__': Tender(), 'featureOf': 'item'})
        feature = Feature()
        feature.import_data(data)
        # relatedItem is None
        try:
            feature.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['relatedItem'])
        # relatedItem not in tender.items
        feature.relatedItem = uuid4().hex
        try:
            feature.validate()
        except ValidationError as e:
            self.assertIn('relatedItem should be one of items', e.message['relatedItem'])
        # relatedItem not in tender.lots
        feature.featureOf = 'lot'
        try:
            feature.validate()
        except ValidationError as e:
            self.assertIn('relatedItem should be one of lots', e.message['relatedItem'])

        # validate_values_uniq
        data = deepcopy(test_features[1])

        data['enum'][1]['value'] = data['enum'][0]['value']
        feature = Feature()
        feature.import_data(data)

        try:
            feature.validate()
        except ValidationError as e:
            self.assertIn('Feature value should be uniq for feature', e.message['enum'])

    def test_Award_model(self):
        """
        validators:
            validate_lotID
        """
        tender = Tender()
        tender.lots = [Lot()]
        data = {'__parent__': tender,
                'status': 'pending',
                'suppliers': [test_organization],
                'bid_id': uuid4().hex}

        award = Award()
        award.import_data(data)
        # lotID is None
        try:
            award.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['lotID'])
        # lotID not in tender.lots
        award.lotID = uuid4().hex
        try:
            award.validate()
        except ValidationError as e:
            self.assertIn('lotID should be one of lots', e.message['lotID'])

    def test_Cancellation_model(self):
        """
        validators:
            validate_relatedLot
        """
        data = {'__parent__': Tender(),
                'reason': 'cancellation reason',
                'cancellationOf': 'lot'}

        cancellation = Cancellation()
        cancellation.import_data(data)
        # relatedLot is None
        try:
            cancellation.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['relatedLot'])
        # relatedLot not in tender.lots
        cancellation.relatedLot = uuid4().hex
        try:
            cancellation.validate()
        except ValidationError as e:
            self.assertIn('relatedLot should be one of lots', e.message['relatedLot'])

    def test_Complaint_model(self):
        """
        validators:
            validate_resolutionType
            validate_cancellationReason
            validate_relatedLot
        """
        data = {'__parent__': Tender(),
                'title': 'complaint title',
                'status': 'answered',
                'description': 'complaint description',
                'author': test_organization}

        complaint = Complaint()
        complaint.import_data(data)

        self.assertEqual(set(complaint.serialize()) - set(complaint.serialize(role='view')),
                         set(['author']))
        # validate_resolutionType
        try:
            complaint.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['resolutionType'])
        # validate_cancellationReason
        complaint.status = 'cancelled'
        try:
            complaint.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['cancellationReason'])
        # validate_relatedLot
        data.update({'__parent__': Tender(),
                     'status': 'claim',
                     'relatedLot': uuid4().hex})
        complaint.import_data(data)
        try:
            complaint.validate()
        except ValidationError as e:
            self.assertIn('relatedLot should be one of lots', e.message['relatedLot'])

    def test_Question_model(self):
        """
        validators:
            validate_relatedItem
        """
        data = {'__parent__': Lot({'__parent__': Tender()}),
                'title': 'question title',
                'author': test_organization,
                'description': 'question description',
                'questionOf': 'lot'}

        question = Question()
        question.import_data(data)
        # relatedItem is None
        try:
            question.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['relatedItem'])
        # relatedItem not in tender.lots
        question.relatedItem = uuid4().hex
        try:
            question.validate()
        except ValidationError as e:
            self.assertIn('relatedItem should be one of lots', e.message['relatedItem'])
        # relatedItem not in tender.items
        question.questionOf = 'item'
        try:
            question.validate()
        except ValidationError as e:
            self.assertIn('relatedItem should be one of items', e.message['relatedItem'])

    def test_Bid_model(self):
        """
        validators:
            validate_participationUrl
            validate_lotValues
            validate_value
            validate_parameters
        """
        from mock import Mock

        data = deepcopy(test_bids[0])
        tender = Tender()
        tender.lots = [1]

        # validate_participationUrl
        data.update({'__parent__': tender, 'participationUrl': 'https://somewhere.ua'})
        bid = Bid()
        bid.import_data(data)
        try:
            bid.validate()
        except ValidationError as e:
            self.assertIn('url should be posted for each lot of bid',
                          e.message['participationUrl'])

        # validate_lotValues
        data = deepcopy(test_bids[0])
        tender = Tender()
        tender.value = Mock()
        tender.lots = [1]

        data.update({'__parent__': tender})
        bid = Bid()
        bid.import_data(data)
        try:
            bid.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['lotValues'])

        tender.lots = []
        tender.revisions = [Mock(date=BID_LOTVALUES_VALIDATION_FROM + timedelta(1))]
        relatedLot_id = uuid4().hex
        bid.lotValues = [{'relatedLot': relatedLot_id, 'value': {'amount': 100}},
                         {'relatedLot': relatedLot_id, 'value': {'amount': 200}}]
        try:
            bid.validate()
        except ValidationError as e:
            self.assertIn("bids don't allow duplicated proposals", e.message['lotValues'])

        # validate_value
        data = deepcopy(test_bids[0])
        tender = Tender()
        tender.value = Mock(currency='USD', amount=400, valueAddedTaxIncluded=False)
        tender.lots = [1]

        data.update({'__parent__': tender})
        bid = Bid()
        bid.import_data(data)
        try:
            bid.validate()
        except ValidationError as e:
            self.assertIn('value should be posted for each lot of bid', e.message['value'])

        tender.lots = []
        try:
            bid.validate()
        except ValidationError as e:
            self.assertIn('value of bid should be less than value of tender',
                          e.message['value'])

        tender.value.amount = 500
        try:
            bid.validate()
        except ValidationError as e:
            self.assertIn('currency of bid should be identical to currency of value of tender',
                          e.message['value'])

        tender.value.currency = 'UAH'
        try:
            bid.validate()
        except ValidationError as e:
            self.assertIn('valueAddedTaxIncluded of bid should be identical to valueAddedTaxIncluded of value of tender',
                          e.message['value'])

        bid.value = None
        try:
            bid.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['value'])

        # validate_parameters
        data = deepcopy(test_bids[0])
        tender = Tender()
        tender.value = Mock()
        feature = Feature({'code': 'feature code'})
        tender.features = [feature]
        tender.lots = [1]

        data.update({'__parent__': tender})
        bid = Bid()
        bid.import_data(data)
        try:
            bid.validate()
        except ValidationError as e:
            self.assertIn('All features parameters is required.',
                          e.message['parameters'])

        tender.lots = []
        try:
            bid.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['parameters'])

        bid.parameters = [{'code': 'invalid code', 'value': 0.01}]
        try:
            bid.validate()
        except ValidationError as e:
            self.assertIn('All features parameters is required.',
                          e.message['parameters'])

        # validate_parameters_uniq
        data = deepcopy(test_bids[0])
        tender = Tender()
        feature = Feature({'code': 'feature code', 'enum': [{'value': 0.01}]})
        tender.features = [feature]

        data.update({'__parent__': tender, 'parameters': [
            {'code': 'feature code', 'value': 0.01},
            {'code': 'feature code', 'value': 0.01}]})
        bid = Bid()
        bid.import_data(data)
        try:
            bid.validate()
        except ValidationError as e:
            self.assertIn('Parameter code should be uniq for all parameters',
                          e.message['parameters'])

    def test_Parameter_model(self):
        """
        validators:
            validate_code
            validate_value
        """
        tender = Tender()
        bid = Bid({'__parent__': tender})
        feature = Feature({'__parent__': tender, 'code': 'some code',
                           'enum': [{'value': 0.02}]})
        data = {'__parent__': bid, 'code': 'some code', 'value': 0.01}
        # validate_code
        parameter = Parameter()
        parameter.import_data(data)
        # parameter.code not in tender.features codes
        try:
            parameter.validate()
        except ValidationError as e:
            self.assertIn('code should be one of feature code.',
                          e.message['code'])
        # validate_value
        tender.features = [feature]
        # parameter.value not in tender.features values
        try:
            parameter.validate()
        except ValidationError as e:
            self.assertIn('value should be one of feature value.',
                          e.message['value'])

    def test_LotValue_model(self):
        """
        validators:
            validate_value
            validate_relatedLot
        """
        tender = Tender()
        lot = Lot({'__parent__': tender, 'value': {'amount': 450}})
        bid = Bid({'__parent__': tender})
        data = {'__parent__': bid, 'relatedLot': lot.id,
                'value': {'amount': 479, 'currency': 'UAH',
                          'valueAddedTaxIncluded': True}}
        # validate_relatedLot
        lotValue = LotValue()
        lotValue.import_data(data)
        # relatedLot not in tender.lots
        try:
            lotValue.validate()
        except ValidationError as e:
            self.assertIn('relatedLot should be one of lots',
                          e.message['relatedLot'])
        # validate_value
        tender.lots = [lot]
        # lotValue.value.amount > lot.value.amount
        try:
            lotValue.validate()
        except ValidationError as e:
            self.assertIn('value of bid should be less than value of lot',
                          e.message['value'])
        # lotValue.value.currency != lot.value.currency
        tender.lots[0]['value'] = {'currency': 'USD', 'amount': 480}
        try:
            lotValue.validate()
        except ValidationError as e:
            self.assertIn('currency of bid should be identical to currency of value of lot',
                          e.message['value'])
        # lotValue.value.valueAddedTaxIncluded != lot.value.valueAddedTaxIncluded
        tender.lots[0]['value'] = {'valueAddedTaxIncluded': False,
                                   'currency': 'UAH', 'amount': 480}
        try:
            lotValue.validate()
        except ValidationError as e:
            self.assertIn('valueAddedTaxIncluded of bid should be identical to valueAddedTaxIncluded of value of lot',
                          e.message['value'])

    def test_Contract_model(self):
        """
        validators:
            validate_awardID
            validate_dateSigned
        """
        tender = Tender()
        data = {'__parent__': tender, 'awardID': 'some_id'}

        # validate_awardID
        contract = Contract()
        contract.import_data(data)
        # awardID not in tender.awards
        try:
            contract.validate()
        except ValidationError as e:
            self.assertIn('awardID should be one of awards',
                          e.message['awardID'])
        # validate_dateSigned
        tender.awards = [Award({
            'complaintPeriod': {'endDate': get_now() + timedelta(1)}})]
        # dateSigned < award.complaintPeriod.endDate
        data.update({'__parent__': tender, 'awardID': tender.awards[0].id,
                                           'dateSigned': get_now()})
        contract.import_data(data)
        try:
            contract.validate()
        except ValidationError as e:
            self.assertIn('Contract signature date should be after award complaint period end date ({})'.format(tender.awards[0].complaintPeriod.endDate.isoformat()),
                          e.message['dateSigned'])
        # dateSigned > now
        contract.dateSigned = get_now() + timedelta(2)
        try:
            contract.validate()
        except ValidationError as e:
            self.assertIn("Contract signature date can't be in the future",
                          e.message['dateSigned'])

    def test_Document_model(self):
        """
        validators:
            validate_relatedItem
        """
        data = {'__parent__': Lot({'__parent__': Tender()}),
                'title': 'test.pdf',
                'format': 'application/pdf',
                'url': 'https://somewhere',
                'documentOf': 'lot'}

        document = Document()
        document.import_data(data)
        # relatedItem is None
        try:
            document.validate()
        except ValidationError as e:
            self.assertIn('This field is required.',
                          e.message['relatedItem'])
        # relatedItem not in tender.lots
        document.relatedItem = uuid4().hex
        try:
            document.validate()
        except ValidationError as e:
            self.assertIn('relatedItem should be one of lots',
                          e.message['relatedItem'])
        # relatedItem not in tender.items
        document.documentOf = 'item'
        try:
            document.validate()
        except ValidationError as e:
            self.assertIn('relatedItem should be one of items',
                          e.message['relatedItem'])

    def test_Item_model(self):
        """
        validators:
            validate_relatedLot
            validate_additionalClassifications
        """
        data = deepcopy(test_features_item)
        tender = Tender()

        # validate_relatedLot
        data.update({'__parent__': tender, 'relatedLot': uuid4().hex})
        item = Item()
        item.import_data(data)
        # relatedLot not in tender.lots
        try:
            item.validate()
        except ValidationError as e:
            self.assertIn('relatedLot should be one of lots',
                          e.message['relatedLot'])
        # validate_additionalClassifications
        del data['relatedLot']
        data['classification']['id'] = '99999999-9'
        data['additionalClassifications'][0]['scheme'] = 'INVALID'
        # additionalClassifications not in ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017
        item.import_data(data)
        try:
            item.validate()
        except ValidationError as e:
            self.assertIn(u"One of additional classifications should be one of [{0}].".format(', '.join(ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017)),
                          e.message['additionalClassifications'])
        # not tender_from_2017
        tender = Tender({'revisions': [{'date': CPV_ITEMS_CLASS_FROM - timedelta(1)}]})
        # additionalClassifications not in ADDITIONAL_CLASSIFICATIONS_SCHEMES
        data.update({'__parent__': tender})
        item.import_data(data)
        try:
            item.validate()
        except ValidationError as e:
            self.assertIn(u'One of additional classifications should be one of [{0}].'.format(', '.join(ADDITIONAL_CLASSIFICATIONS_SCHEMES)),
                          e.message['additionalClassifications'])
        # no additionalClassifications
        data['additionalClassifications'] = []
        item.import_data(data)
        try:
            item.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['additionalClassifications'])

    def test_LotAuctionPeriod_model(self):
        """
        serializable fields:
            shouldStartAfter
        """
        from mock import Mock
        tender = Tender()
        lot = Lot({'__parent__': tender, 'status': 'unsuccessful'})
        data = {'__parent__': lot, 'endDate': get_now()}

        # should be None, endDate is present
        lotAuctionPeriod = LotAuctionPeriod()
        lotAuctionPeriod.import_data(data)
        self.assertEqual(lotAuctionPeriod.shouldStartAfter, None)

        # should be None, tender.status is 'active.enquiries'
        del data['endDate']
        lotAuctionPeriod = LotAuctionPeriod()
        lotAuctionPeriod.import_data(data)
        self.assertEqual(lotAuctionPeriod.shouldStartAfter, None)

        # should be None, lot.status is 'unsuccessful'
        tender.status = 'active.tendering'
        self.assertEqual(lotAuctionPeriod.shouldStartAfter, None)

        # should start after startDate + calc_auction_end_time(0, startDate)
        lot.status = 'active'
        tender.enquiryPeriod = Mock()
        startDate = get_now() - timedelta(1)

        data.update({'__parent__': lot, 'startDate': startDate})
        lotAuctionPeriod.import_data(data)
        self.assertEqual(lotAuctionPeriod.shouldStartAfter, (startDate +
                         AUCTION_STAND_STILL_TIME + SERVICE_TIME).isoformat())

        # should start after tender.tenderPeriod.endDate
        tender.tenderPeriod = Mock(endDate=get_now() + timedelta(7))

        data.update({'__parent__': lot, 'startDate': get_now()})
        lotAuctionPeriod.import_data(data)
        self.assertEqual(lotAuctionPeriod.shouldStartAfter,
                         tender.tenderPeriod.endDate.isoformat())

    def test_TenderAuctionPeriod_model(self):
        """
        serializable fields:
            shouldStartAfter
        """
        from mock import Mock
        tender = Tender()
        data = {'__parent__': tender, 'endDate': get_now()}

        # should be None, endDate is present
        tenderAuctionPeriod = TenderAuctionPeriod()
        tenderAuctionPeriod.import_data(data)
        self.assertEqual(tenderAuctionPeriod.shouldStartAfter, None)

        # should be None, tender.status is 'active.enquiries'
        del data['endDate']
        tenderAuctionPeriod = TenderAuctionPeriod()
        tenderAuctionPeriod.import_data(data)
        self.assertEqual(tenderAuctionPeriod.shouldStartAfter, None)

        # should start after startDate + calc_auction_end_time(0, startDate)
        tender.status = 'active.tendering'
        tender.enquiryPeriod = Mock()
        tender.numberOfBids = 0
        startDate = get_now() - timedelta(1)

        data.update({'__parent__': tender, 'startDate': startDate})
        tenderAuctionPeriod.import_data(data)
        self.assertEqual(tenderAuctionPeriod.shouldStartAfter, (startDate +
                         AUCTION_STAND_STILL_TIME + SERVICE_TIME).isoformat())

        # should start after tender.tenderPeriod.endDate
        tender.tenderPeriod = Mock(endDate=get_now() + timedelta(7))

        data.update({'__parent__': tender, 'startDate': get_now()})
        tenderAuctionPeriod.import_data(data)
        self.assertEqual(tenderAuctionPeriod.shouldStartAfter,
                         tender.tenderPeriod.endDate.isoformat())

    def test_PeriodEndRequired_model(self):
        """
        validators:
            validate_startDate
        """
        tender = Tender({'revisions': [{
            'date': CANT_DELETE_PERIOD_START_DATE_FROM + timedelta(1)}]})
        data = {'__parent__': tender,
                'startDate': get_now() + timedelta(1),
                'endDate': get_now()}
        periodEndRequired = PeriodEndRequired()
        periodEndRequired.import_data(data)
        # startDate > endDate
        try:
            periodEndRequired.validate()
        except ValidationError as e:
            self.assertIn('period should begin before its end',
                          e.message['startDate'])
        # delete startDate after CANT_DELETE_PERIOD_START_DATE_FROM
        periodEndRequired.startDate = None
        try:
            periodEndRequired.validate()
        except ValidationError as e:
            self.assertIn('This field cannot be deleted',
                          e.message['startDate'])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DummyModelsTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
