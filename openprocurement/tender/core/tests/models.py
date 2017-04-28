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
    CPV_ITEMS_CLASS_FROM, AUCTION_STAND_STILL_TIME
)
from openprocurement.tender.core.models import (
    validate_lots_uniq, validate_features_uniq,
    validate_dkpp, ValidationError, get_now
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

    def test_Tender_model(self):
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
        from mock import Mock
        tender = Tender()
        tender.value = Mock(currency='UAH', valueAddedTaxIncluded=True)
        tender.minimalStep = Mock(currency='UAH', valueAddedTaxIncluded=True)
        tender.guarantee = Mock(currency='UAH')

        data = deepcopy(test_lots[0])
        data['minimalStep']['amount'] = 501
        data.update({'__parent__': tender, 'guarantee': {'amount': 100,
                                                         'currency': 'UAH'}})
        lot = Lot()
        lot.import_data(data)

        self.assertEqual(lot.numberOfBids, 0)
        self.assertEqual(lot.lot_value.amount, 500)
        self.assertEqual(lot.lot_minimalStep.amount, 501)
        self.assertEqual(lot.lot_guarantee.amount, 100)

        try:
            lot.validate()
        except ValidationError as e:
            self.assertIn('value should be less than value of lot',
                          e.message['minimalStep'])

    def test_Feature_model(self):
        data = deepcopy(test_features[1])
        data.update({'__parent__': Tender(), 'featureOf': 'item'})

        feature = Feature()
        feature.import_data(data)
        try:
            feature.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['relatedItem'])

        feature.relatedItem = uuid4().hex
        try:
            feature.validate()
        except ValidationError as e:
            self.assertIn('relatedItem should be one of items', e.message['relatedItem'])

        feature.featureOf = 'lot'
        try:
            feature.validate()
        except ValidationError as e:
            self.assertIn('relatedItem should be one of lots', e.message['relatedItem'])

        # validate_values_uniq
        data = deepcopy(test_features[1])
        data['enum'][1]['value'] = 0.01

        feature = Feature()
        feature.import_data(data)

        try:
            feature.validate()
        except ValidationError as e:
            self.assertIn('Feature value should be uniq for feature', e.message['enum'])

    def test_Award_model(self):
        tender = Tender()
        tender.lots = [Lot()]
        data = {'__parent__': tender, 'status': 'pending',
                'suppliers': [test_organization], 'bid_id': uuid4().hex}

        award = Award()
        award.import_data(data)
        try:
            award.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['lotID'])

        award.lotID = uuid4().hex
        try:
            award.validate()
        except ValidationError as e:
            self.assertIn('lotID should be one of lots', e.message['lotID'])

    def test_Cancellation_model(self):
        data = {'__parent__': Tender(), 'reason': 'cancellation reason', 'cancellationOf': 'lot'}

        cancellation = Cancellation()
        cancellation.import_data(data)
        try:
            cancellation.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['relatedLot'])

        cancellation.relatedLot = uuid4().hex
        try:
            cancellation.validate()
        except ValidationError as e:
            self.assertIn('relatedLot should be one of lots', e.message['relatedLot'])

    def test_Complaint_model(self):
        data = {'__parent__': Tender(), 'title': 'complaint title', 'status': 'answered',
                'description': 'complaint description', 'author': test_organization}

        complaint = Complaint()
        complaint.import_data(data)

        self.assertEqual(set(complaint.serialize()) - set(complaint.serialize(role='view')),
                         set(['author']))
        try:
            complaint.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['resolutionType'])

        complaint.status = 'cancelled'
        try:
            complaint.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['cancellationReason'])

        data.update({'__parent__': Tender(), 'status': 'claim', 'relatedLot': uuid4().hex})
        complaint.import_data(data)
        try:
            complaint.validate()
        except ValidationError as e:
            self.assertIn('relatedLot should be one of lots', e.message['relatedLot'])

    def test_Question_model(self):
        data = {'__parent__': Lot({'__parent__': Tender()}),
                'title': 'question title', 'author': test_organization,
                'description': 'question description', 'questionOf': 'lot'}

        question = Question()
        question.import_data(data)
        try:
            question.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['relatedItem'])

        question.relatedItem = uuid4().hex
        try:
            question.validate()
        except ValidationError as e:
            self.assertIn('relatedItem should be one of lots', e.message['relatedItem'])

        question.questionOf = 'item'
        try:
            question.validate()
        except ValidationError as e:
            self.assertIn('relatedItem should be one of items', e.message['relatedItem'])

    def test_Bid_model(self):
        from mock import Mock

        # validate_participationUrl
        data = deepcopy(test_bids[0])
        tender = Tender()
        tender.lots = [1]

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
        tender = Tender()
        bid = Bid({'__parent__': tender})
        feature = Feature({'__parent__': tender, 'code': 'some code',
                           'enum': [{'value': 0.02}]})
        data = {'__parent__': bid, 'code': 'some code', 'value': 0.01}

        parameter = Parameter()
        parameter.import_data(data)
        try:
            parameter.validate()
        except ValidationError as e:
            self.assertIn('code should be one of feature code.',
                          e.message['code'])

        tender.features = [feature]
        try:
            parameter.validate()
        except ValidationError as e:
            self.assertIn('value should be one of feature value.',
                          e.message['value'])

    def test_LotValue_model(self):
        tender = Tender()
        lot = Lot({'__parent__': tender, 'value': {'amount': 450}})
        data = {'__parent__': lot, 'relatedLot': lot.id,
                'value': {'amount': 479, 'currency': 'UAH',
                          'valueAddedTaxIncluded': True}}

        lotValue = LotValue()
        lotValue.import_data(data)
        try:
            lotValue.validate()
        except ValidationError as e:
            self.assertIn('relatedLot should be one of lots',
                          e.message['relatedLot'])

        tender.lots = [lot]
        try:
            lotValue.validate()
        except ValidationError as e:
            self.assertIn('value of bid should be less than value of lot',
                          e.message['value'])

        tender.lots[0]['value'] = {'currency': 'USD', 'amount': 480}
        try:
            lotValue.validate()
        except ValidationError as e:
            self.assertIn('currency of bid should be identical to currency of value of lot',
                          e.message['value'])

        tender.lots[0]['value'] = {'valueAddedTaxIncluded': False,
                                   'currency': 'UAH', 'amount': 480}
        try:
            lotValue.validate()
        except ValidationError as e:
            self.assertIn('valueAddedTaxIncluded of bid should be identical to valueAddedTaxIncluded of value of lot',
                          e.message['value'])

    def test_Contract_model(self):
        tender = Tender()
        award = Award({'complaintPeriod': {'endDate': get_now() + timedelta(2)}})
        data = {'__parent__': tender, 'awardID': 'some_id'}

        contract = Contract()
        contract.import_data(data)
        try:
            contract.validate()
        except ValidationError as e:
            self.assertIn('awardID should be one of awards',
                          e.message['awardID'])

        tender.awards = [award]
        data.update({'__parent__': tender, 'awardID': award.id, 'dateSigned': get_now()})
        contract.import_data(data)
        try:
            contract.validate()
        except ValidationError as e:
            self.assertIn('Contract signature date should be after award complaint period end date ({})'.format(award.complaintPeriod.endDate.isoformat()),
                          e.message['dateSigned'])

        tender.awards[0].complaintPeriod.endDate = get_now() + timedelta(1)
        contract.dateSigned = get_now() + timedelta(2)
        try:
            contract.validate()
        except ValidationError as e:
            self.assertIn("Contract signature date can't be in the future",
                          e.message['dateSigned'])

    def test_Document_model(self):
        data = {'__parent__': Lot({'__parent__': Tender()}),
                'title': 'test.pdf', 'format': 'application/pdf',
                'url': 'https://somewhere', 'documentOf': 'lot'}

        document = Document()
        document.import_data(data)
        try:
            document.validate()
        except ValidationError as e:
            self.assertIn('This field is required.',
                          e.message['relatedItem'])

        document.relatedItem = uuid4().hex
        try:
            document.validate()
        except ValidationError as e:
            self.assertIn('relatedItem should be one of lots',
                          e.message['relatedItem'])

        document.documentOf = 'item'
        try:
            document.validate()
        except ValidationError as e:
            self.assertIn('relatedItem should be one of items',
                          e.message['relatedItem'])

    def test_Item_model(self):
        data = deepcopy(test_features_item)
        tender = Tender()

        data.update({'__parent__': tender, 'relatedLot': uuid4().hex})
        item = Item()
        item.import_data(data)
        try:
            item.validate()
        except ValidationError as e:
            self.assertIn('relatedLot should be one of lots',
                          e.message['relatedLot'])

        del data['relatedLot']
        data['classification']['id'] = '99999999-9'
        data['additionalClassifications'][0]['scheme'] = 'INVALID'

        item.import_data(data)
        try:
            item.validate()
        except ValidationError as e:
            self.assertIn(u"One of additional classifications should be one of [{0}].".format(', '.join(ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017)),
                          e.message['additionalClassifications'])

        tender = Tender({'revisions': [{'date': CPV_ITEMS_CLASS_FROM - timedelta(1)}]})
        data.update({'__parent__': tender})
        item.import_data(data)
        try:
            item.validate()
        except ValidationError as e:
            self.assertIn(u'One of additional classifications should be one of [{0}].'.format(', '.join(ADDITIONAL_CLASSIFICATIONS_SCHEMES)),
                          e.message['additionalClassifications'])

        data['additionalClassifications'] = []
        item.import_data(data)
        try:
            item.validate()
        except ValidationError as e:
            self.assertIn('This field is required.', e.message['additionalClassifications'])

    def test_LotAuctionPeriod_model(self):
        from mock import Mock
        tender = Tender()
        lot = Lot({'__parent__': tender})
        data = {'__parent__': lot, 'endDate': get_now()}

        lotAuctionPeriod = LotAuctionPeriod()
        lotAuctionPeriod.import_data(data)
        self.assertEqual(lotAuctionPeriod.shouldStartAfter, None)

        del data['endDate']
        lotAuctionPeriod = LotAuctionPeriod()
        lotAuctionPeriod.import_data(data)
        self.assertEqual(lotAuctionPeriod.shouldStartAfter, None)

        tender.status = 'active.tendering'
        tender.enquiryPeriod = Mock()
        start = get_now() - timedelta(1)
        data.update({'__parent__': lot, 'startDate': start})
        lotAuctionPeriod = LotAuctionPeriod()
        lotAuctionPeriod.import_data(data)
        self.assertEqual(lotAuctionPeriod.shouldStartAfter, (start +
                         AUCTION_STAND_STILL_TIME + SERVICE_TIME).isoformat())

        tender.tenderPeriod = Mock(endDate=get_now() + timedelta(7))
        data.update({'__parent__': lot, 'startDate': get_now()})
        lotAuctionPeriod.import_data(data)
        self.assertEqual(lotAuctionPeriod.shouldStartAfter,
                         tender.tenderPeriod.endDate.isoformat())

    def test_TenderAuctionPeriod_model(self):
        from mock import Mock
        tender = Tender()
        data = {'__parent__': tender, 'endDate': get_now()}

        tenderAuctionPeriod = TenderAuctionPeriod()
        tenderAuctionPeriod.import_data(data)
        self.assertEqual(tenderAuctionPeriod.shouldStartAfter, None)

        del data['endDate']
        tenderAuctionPeriod = TenderAuctionPeriod()
        tenderAuctionPeriod.import_data(data)
        self.assertEqual(tenderAuctionPeriod.shouldStartAfter, None)

        tender.status = 'active.tendering'
        tender.enquiryPeriod = Mock()
        tender.numberOfBids = 0
        start = get_now() - timedelta(1)
        data.update({'__parent__': tender, 'startDate': start})
        tenderAuctionPeriod.import_data(data)
        self.assertEqual(tenderAuctionPeriod.shouldStartAfter, (start +
                         AUCTION_STAND_STILL_TIME + SERVICE_TIME).isoformat())

        tender.tenderPeriod = Mock(endDate=get_now() + timedelta(7))
        data.update({'__parent__': tender, 'startDate': get_now()})
        tenderAuctionPeriod.import_data(data)
        self.assertEqual(tenderAuctionPeriod.shouldStartAfter,
                         tender.tenderPeriod.endDate.isoformat())

    def test_PeriodEndRequired_model(self):
        tender = Tender({'revisions': [{'date': get_now()}]})
        data = {'__parent__': tender, 'startDate': get_now() + timedelta(1),
                                      'endDate': get_now()}
        periodEndRequired = PeriodEndRequired()
        periodEndRequired.import_data(data)
        try:
            periodEndRequired.validate()
        except ValidationError as e:
            self.assertIn('period should begin before its end',
                          e.message['startDate'])

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
