# -*- coding: utf-8 -*-
import unittest

from mock import patch, MagicMock
from datetime import datetime, timedelta, time
from schematics.exceptions import ModelValidationError, ValidationError
from openprocurement.tender.core.models import (
    PeriodEndRequired, get_tender, Tender, TenderAuctionPeriod,
    Document, bids_validation_wrapper, validate_dkpp, validate_parameters_uniq,
    validate_values_uniq, validate_features_uniq, validate_lots_uniq, LotAuctionPeriod, Item,
    Contract, LotValue, Parameter, Bid, Question, Complaint, Cancellation, Award, Feature, Lot, BaseLot, BaseTender
)
from openprocurement.api.constants import TZ
from munch import munchify
from openprocurement.api.constants import (
    ADDITIONAL_CLASSIFICATIONS_SCHEMES,
    ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017
)
from openprocurement.api.constants import SANDBOX_MODE
from openprocurement.tender.core.utils import calc_auction_end_time, rounding_shouldStartAfter
from openprocurement.tender.core.traversal import Root

from uuid import uuid4
from copy import deepcopy


now = datetime.now()
test_organization = {
    "name": u"Державне управління справами",
    "identifier": {
        "scheme": u"UA-EDR",
        "id": u"00037256",
        "uri": u"http://www.dus.gov.ua/"
    },
    "address": {
        "countryName": u"Україна",
        "postalCode": u"01220",
        "region": u"м. Київ",
        "locality": u"м. Київ",
        "streetAddress": u"вул. Банкова, 11, корпус 1"
    },
    "contactPoint": {
        "name": u"Державне управління справами",
        "telephone": u"0440000000"
    }
}
test_procuringEntity = test_organization.copy()
test_procuringEntity["kind"] = "general"
test_tender_data = {
    "title": u"футляри до державних нагород",
    "procuringEntity": test_procuringEntity,
    "value": {
        "amount": 500,
        "currency": u"UAH"
    },
    "minimalStep": {
        "amount": 35,
        "currency": u"UAH"
    },
    "items": [
        {
            "description": u"футляри до державних нагород",
            "classification": {
                "scheme": u"CPV",
                "id": u"44617100-9",
                "description": u"Cartons"
            },
            "additionalClassifications": [
                {
                    "scheme": u"ДКПП",
                    "id": u"17.21.1",
                    "description": u"папір і картон гофровані, паперова й картонна тара"
                }
            ],
            "unit": {
                "name": u"item",
                "code": u"44617100-9"
            },
            "quantity": 5,
            "deliveryDate": {
                "startDate": (now + timedelta(days=2)).isoformat(),
                "endDate": (now + timedelta(days=5)).isoformat()
            },
            "deliveryAddress": {
                "countryName": u"Україна",
                "postalCode": "79000",
                "region": u"м. Київ",
                "locality": u"м. Київ",
                "streetAddress": u"вул. Банкова 1"
            }
        }
    ],
    "enquiryPeriod": {
        "endDate": (now + timedelta(days=7)).isoformat()
    },
    "tenderPeriod": {
        "endDate": (now + timedelta(days=14)).isoformat()
    },
    "procurementMethodType": "belowThreshold",
}
if SANDBOX_MODE:
    test_tender_data['procurementMethodDetails'] = 'quick, accelerator=1440'
test_features_tender_data = test_tender_data.copy()
test_features_item = test_features_tender_data['items'][0].copy()
test_features_item['id'] = "1"
test_features_tender_data['items'] = [test_features_item]
test_features_tender_data["features"] = [
    {
        "code": "OCDS-123454-AIR-INTAKE",
        "featureOf": "item",
        "relatedItem": "1",
        "title": u"Потужність всмоктування",
        "title_en": "Air Intake",
        "description": u"Ефективна потужність всмоктування пилососа, в ватах (аероватах)",
        "enum": [
            {
                "value": 0.1,
                "title": u"До 1000 Вт"
            },
            {
                "value": 0.15,
                "title": u"Більше 1000 Вт"
            }
        ]
    },
    {
        "code": "OCDS-123454-YEARS",
        "featureOf": "tenderer",
        "title": u"Років на ринку",
        "title_en": "Years trading",
        "description": u"Кількість років, які організація учасник працює на ринку",
        "enum": [
            {
                "value": 0.05,
                "title": u"До 3 років"
            },
            {
                "value": 0.1,
                "title": u"Більше 3 років, менше 5 років"
            },
            {
                "value": 0.15,
                "title": u"Більше 5 років"
            }
        ]
    }
]
test_bids = [
    {
        "tenderers": [
            test_organization
        ],
        "value": {
            "amount": 469,
            "currency": "UAH",
            "valueAddedTaxIncluded": True
        }
    },
    {
        "tenderers": [
            test_organization
        ],
        "value": {
            "amount": 479,
            "currency": "UAH",
            "valueAddedTaxIncluded": True
        }
    }
]
test_lots = [
    {
        'title': 'lot title',
        'description': 'lot description',
        'value': test_tender_data['value'],
        'minimalStep': test_tender_data['minimalStep'],
    }
]
test_features = [
    {
        "code": "code_item",
        "featureOf": "item",
        "relatedItem": "1",
        "title": u"item feature",
        "enum": [
            {
                "value": 0.01,
                "title": u"good"
            },
            {
                "value": 0.02,
                "title": u"best"
            }
        ]
    },
    {
        "code": "code_tenderer",
        "featureOf": "tenderer",
        "title": u"tenderer feature",
        "enum": [
            {
                "value": 0.01,
                "title": u"good"
            },
            {
                "value": 0.02,
                "title": u"best"
            }
        ]
    }
]
test_items = [
        {
            "description": u"футляри до державних нагород",
            "classification": {
                "scheme": u"CPV",
                "id": u"44617100-9",
                "description": u"Cartons"
            },
            "additionalClassifications": [
                {
                    "scheme": u"ДКПП",
                    "id": u"17.21.1",
                    "description": u"папір і картон гофровані, паперова й картонна тара"
                }
            ],
            "unit": {
                "name": u"item",
                "code": u"44617100-9"
            },
            "quantity": 5,
            "deliveryDate": {
                "startDate": (now + timedelta(days=2)).isoformat(),
                "endDate": (now + timedelta(days=5)).isoformat()
            },
            "deliveryAddress": {
                "countryName": u"Україна",
                "postalCode": "79000",
                "region": u"м. Київ",
                "locality": u"м. Київ",
                "streetAddress": u"вул. Банкова 1"
            },
        }
    ]


class TestPeriodEndRequired(unittest.TestCase):

    @patch('openprocurement.tender.core.models.get_tender')
    def test_validate_start_date(self, mocked_get_tender):
        start_date = datetime.now(TZ)
        end_date = datetime.now(TZ) + timedelta(minutes=3)
        model = PeriodEndRequired({'startDate': end_date.isoformat(),
                                   'endDate': start_date.isoformat()})
        with self.assertRaises(ModelValidationError) as e:
            model.validate()
        self.assertEqual(
            e.exception.message,
            {'startDate': [u'period should begin before its end']}
        )

        revision = MagicMock()
        revision.date = datetime.now(TZ)
        mocked_get_tender.return_value = {
            'revisions': [revision]
        }
        model = PeriodEndRequired({'endDate': end_date.isoformat()})
        with self.assertRaises(ModelValidationError) as e:
            model.validate()
        self.assertEqual(e.exception.message,
                         {'startDate': [u'This field cannot be deleted']})

        model = PeriodEndRequired({'startDate': start_date.isoformat(),
                                   'endDate': end_date.isoformat()})
        model.validate()
        self.assertEqual(start_date, model.startDate)
        self.assertEqual(end_date, model.endDate)


class TestModelsUtils(unittest.TestCase):

    def test_get_tender(self):
        period = PeriodEndRequired(
            {'startDate': datetime.now(TZ).isoformat(),
             'endDate': datetime.now(TZ).isoformat()}
        )
        second_period = PeriodEndRequired(
            {'startDate': datetime.now(TZ).isoformat(),
             'endDate': datetime.now(TZ).isoformat()}
        )
        tender = Tender()
        period._data['__parent__'] = tender
        second_period._data['__parent__'] = period

        parent_tender = get_tender(second_period)
        self.assertEqual(tender, parent_tender)
        self.assertIsInstance(parent_tender, Tender)
        self.assertIsInstance(tender, Tender)

        period._data['__parent__'] = None
        with self.assertRaises(AttributeError) as e:
            get_tender(second_period)
        self.assertEqual(e.exception.message,
                         "'NoneType' object has no attribute '__parent__'")


class TestTenderAuctionPeriod(unittest.TestCase):

    def test_should_start_after(self):
        tender_period = PeriodEndRequired({
            'startDate': datetime.now(TZ).isoformat(),
            'endDate': (datetime.now(TZ) + timedelta(minutes=10)).isoformat()
        })
        tender_enquiry_period = PeriodEndRequired({
            'startDate': datetime.now(TZ).isoformat(),
            'endDate': (datetime.now(TZ) + timedelta(minutes=10)).isoformat()
        })
        tender = Tender({
            'status': 'active.enquiries'
        })
        tender.lots = []
        tender.numberOfBids = 2
        tender.tenderPeriod = tender_period
        tender.enquiryPeriod = tender_enquiry_period
        start_date = datetime.now(TZ)
        end_date = datetime.now(TZ) + timedelta(minutes=5)
        tender_auction_period = TenderAuctionPeriod({
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat()
        })

        # Test with endDate exist
        serialized = tender_auction_period.serialize()
        self.assertEqual(
            serialized,
            {'startDate': start_date.isoformat(),
             'endDate': end_date.isoformat()}
        )

        # Test with wrong status
        tender_auction_period = TenderAuctionPeriod(
            {'startDate': start_date.isoformat()})
        tender_auction_period.__parent__ = tender

        serialized = tender_auction_period.serialize()
        self.assertEqual(serialized, {'startDate': start_date.isoformat()})

        # Test with get_now() less than calc_auction_end_time()
        tender_auction_period = TenderAuctionPeriod(
            {'startDate': start_date.isoformat()})
        tender.status = 'active.tendering'
        tender_auction_period.__parent__ = tender
        serialized = tender_auction_period.serialize()
        should_start_after = datetime.combine(
            (tender.tenderPeriod.endDate.date() + timedelta(days=1)),
             time(0, tzinfo=tender.tenderPeriod.endDate.tzinfo))
        self.assertEqual(
            serialized,
            {'startDate': start_date.isoformat(),
             'shouldStartAfter': should_start_after.isoformat()}
        )

        # Test with get_now() greater then calc_auction
        tender_auction_period.startDate -= timedelta(days=1)
        serialized = tender_auction_period.serialize()
        should_start_after = datetime.combine(
            (tender_auction_period.startDate.date() + timedelta(days=1)),
             time(0, tzinfo=tender_auction_period.startDate.tzinfo))
        self.assertEqual(
            serialized,
            {'startDate': tender_auction_period.startDate.isoformat(),
             'shouldStartAfter': should_start_after.isoformat()}
        )
        
        
class TestDocument(unittest.TestCase):

    @patch('openprocurement.tender.core.models.get_tender')
    def test_validate_relatedItem(self, mocked_get_tender):
        data = {'__parent__': Lot({'__parent__': Tender()}),
              'title': 'test.pdf',
              'format': 'application/pdf',
              'url': 'https://somewhere',
              'documentOf': 'lot'}

        model = Document(data)

        with self.assertRaises(ValidationError) as e:
            model.validate()
        self.assertEqual(e.exception[0]['relatedItem'][0], u'This field is required.')

        tender = munchify({'lots': [{'id': 'lot'}]})
        mocked_get_tender.return_value = tender
        model.relatedItem = uuid4().hex

        with self.assertRaises(ValidationError) as e:
            model.validate()
        self.assertEqual(e.exception[0]['relatedItem'][0], u"relatedItem should be one of lots")

        tender.items = munchify([{'id': 'item'}])
        mocked_get_tender.return_value = tender
        model.documentOf = 'item'

        with self.assertRaises(ValidationError) as e:
            model.validate()
        self.assertEqual(e.exception[0]['relatedItem'][0], u"relatedItem should be one of items")

        data = {'__parent__': Lot({'__parent__': Tender()}),
                'title': 'test.pdf',
                'format': 'application/pdf',
                'url': 'https://somewhere',
                'documentOf': 'tender'}
        model = Document(data)
        model.validate()
        self.assertEqual(model.documentOf, 'tender')
        self.assertEqual(model.url, 'https://somewhere')
        self.assertEqual(model.format, 'application/pdf')
        self.assertEqual(model.title, 'test.pdf')


class Test_bids_validation_wrapper(unittest.TestCase):
    def test_bids_validation_wrapper(self):
        def validation_func():
            pass
        res = bids_validation_wrapper(validation_func=validation_func())
        self.assertEqual(res.func_name, u'validator')


class TestForOtherValidators(unittest.TestCase):

    def test_validate_dkpp(self):
        items = munchify([{'scheme': '1'}])
        with self.assertRaises(ValidationError) as e:
            validate_dkpp(items=items)
        self.assertEqual(e.exception[0][0], u"One of additional classifications should be one of [{0}].".format(
            ', '.join(ADDITIONAL_CLASSIFICATIONS_SCHEMES)))

    def test_validate_parameters_uniq(self):
        parameters = munchify([{'code': 'test'}, {'code': 'test'}, {'code': 'test1'}])
        with self.assertRaises(ValidationError) as e:
            validate_parameters_uniq(parameters=parameters)
        self.assertEqual(e.exception[0][0], u"Parameter code should be uniq for all parameters")

    def test_validate_values_uniq(self):
        values = munchify([{'value': 'test'}, {'value': 'test'}, {'value': 'test'}])
        with self.assertRaises(ValidationError) as e:
            validate_values_uniq(values=values)
        self.assertEqual(e.exception[0][0], u"Feature value should be uniq for feature")

    def test_validate_features_uniq(self):
        features = munchify([{'code': 'test'}, {'code': 'test'}, {'code': 'test1'}])
        with self.assertRaises(ValidationError) as e:
            validate_features_uniq(features=features)
        self.assertEqual(e.exception[0][0], u"Feature code should be uniq for all features")

    def test_validate_lots_uniq(self):
        lots = munchify([{'id': '1111', 'name': 'first'}, {'id': '2222', 'name': 'second'},
                         {'id': '2222', 'name': 'second'}])
        with self.assertRaises(ValidationError) as e:
            validate_lots_uniq(lots=lots)
        self.assertEqual(e.exception[0][0], u"Lot id should be uniq for all lots")


class TestLotAuctionPeriod(unittest.TestCase):
    @patch('openprocurement.tender.core.models.get_tender')
    def test_shouldStartAfter(self, mocked_get_tender):

        start_date = datetime.today()
        end_date = datetime.now(TZ) + timedelta(minutes=3)
        model = LotAuctionPeriod({'startDate': start_date.isoformat(),
                                  'endDate': end_date.isoformat()})

        first_return = model.shouldStartAfter
        self.assertEquals(first_return, None)

        model = LotAuctionPeriod(munchify({'startDate': start_date.isoformat(),
                                           '__parent__': {'status': 'active', 'id': '1111'}}))
        mocked_get_tender.return_value = munchify({'status': 'active', 'id': '1111'})
        second_return = model.shouldStartAfter
        self.assertEquals(second_return, None)

        tender_enquiry_period = PeriodEndRequired({
            'startDate': datetime.now(TZ).isoformat(),
            'endDate': (datetime.now(TZ) + timedelta(minutes=10)).isoformat()
        })
        model = LotAuctionPeriod(munchify({'startDate': end_date,
                                           '__parent__': {'status': 'active', 'id': '1111', 'numberOfBids': -5}}))
        tender = Tender()
        tender.status = 'active.tendering'
        tender.enquiryPeriod = tender_enquiry_period
        mocked_get_tender.return_value = tender
        third_return = model.shouldStartAfter
        start_after = calc_auction_end_time(-5, model.startDate)
        self.assertEquals(third_return, rounding_shouldStartAfter(start_after, tender).isoformat())


class TestItem(unittest.TestCase):
    @patch('openprocurement.tender.core.models.get_tender')
    def test_validate_additionalClassifications(self, mocked_get_tender):
        items = deepcopy(test_items)
        revision = MagicMock()
        revision.date = datetime.now(TZ)
        tender = Tender()
        mocked_get_tender.return_value = {
            'revisions': [revision]
        }
        tender.revisions = revision
        data = items[0]
        data.update({'__parent__': tender})

        item = Item(data)
        item.validate()
        self.assertEqual(item.description, u"футляри до державних нагород")
        self.assertEqual(item.unit.name, u"item")
        self.assertEqual(item.quantity, 5)
        self.assertEqual(item.classification.id, u"44617100-9")

        mocked_get_tender.return_value = munchify({'lots': [{'id': 'test'}]})
        data['relatedLot'] = uuid4().hex
        data['classification']['id'] = '99999999-9'
        item = Item(data)

        with self.assertRaises(ValidationError) as e:
            item.validate()
        self.assertEqual(e.exception[0]['additionalClassifications'][0],
                         u"One of additional classifications should be one of [{0}].".format(
            ', '.join(ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017)))
        self.assertEqual(e.exception[0]['relatedLot'][0], u"relatedLot should be one of lots")

        tender.scheme = '1'
        data.update({'__parent__': tender})
        mocked_get_tender.return_value = munchify({'lots': [{'id': 'test'}]})
        data['relatedLot'] = uuid4().hex
        data['classification']['id'] = '99999999-9'
        item = Item(data)
        item.additionalClassifications = None

        with self.assertRaises(ValidationError) as e:
            item.validate()
        self.assertEqual(e.exception[0]['additionalClassifications'][0], u'This field is required.')
        self.assertEqual(e.exception[0]['relatedLot'][0], u"relatedLot should be one of lots")

        revision.date = datetime.now(TZ) - timedelta(days=365 * 100)
        tender.revisions = revision
        data.update({'__parent__': tender})
        item = Item(data)
        mocked_get_tender.return_value = munchify({
            'revisions': [revision],
            'lots': [{'id': 'test'}]
        })
        item.additionalClassifications[0].scheme = 'test'
        with self.assertRaises(ValidationError) as e:
            item.validate()
        self.assertEqual(e.exception[0]['additionalClassifications'][0],
                         u"One of additional classifications should be one of [{0}].".format(
            ', '.join(ADDITIONAL_CLASSIFICATIONS_SCHEMES)))
        self.assertEqual(e.exception[0]['relatedLot'][0], u"relatedLot should be one of lots")


class TestContract(unittest.TestCase):
    def test_validate_contract(self):
        tender = Tender()
        data = {'__parent__': tender, 'awardID': '12'}
        complaint_period = (
            {'startDate': datetime.now(TZ),
             'endDate': datetime.now(TZ)}
        )
        data['__parent__'].awards = munchify([{'id': '12', 'complaintPeriod': complaint_period},
                                              {'id': '13', 'complaintPeriod': complaint_period}])
        data['title'] = u'test_test_test'
        data['description'] = u'Test_description'
        contract = Contract(data)
        contract.validate()
        self.assertEqual(contract.status, u'pending')
        self.assertEqual(contract.title, u'test_test_test')
        self.assertEqual(contract.awardID, u'12')
        self.assertEqual(contract.description, u'Test_description')

        data.update({'__parent__': tender, 'awardID': 'test_id'})
        contract = Contract(data)

        with self.assertRaises(ValidationError) as e:
            contract.validate()
        self.assertEqual(e.exception[0]['awardID'][0], u'awardID should be one of awards')

        date = datetime.now(TZ)
        data.update({'__parent__': tender, 'awardID': '12'})

        award = [i for i in data['__parent__'].awards if i.id == data['awardID']][0]
        data['dateSigned'] = date.replace(year=2000)
        contract = Contract(data)
        with self.assertRaises(ValidationError) as e:
            contract.validate()
        self.assertEquals(e.exception[0]['dateSigned'][0],
                          u"Contract signature date should be after award complaint period end date ({})".format(
                award.complaintPeriod.endDate.isoformat()))

        data['dateSigned'] = date.replace(year=3000)
        contract = Contract(data)
        with self.assertRaises(ValidationError) as e:
            contract.validate()
        self.assertEqual(e.exception[0]['dateSigned'][0], u"Contract signature date can't be in the future")


class TestLotValue(unittest.TestCase):
    @patch('openprocurement.tender.core.models.validate_LotValue_value')
    @patch('openprocurement.tender.core.models.get_tender')
    def test_validate_lot_value(self, mocked_get_tender,  mocked_validate_LotValue_value):
        tender = Tender()
        lot = Lot({'__parent__': tender, 'value': {'amount': 450}})
        bid = Bid({'__parent__': tender})
        value = {'amount': 479, 'currency': 'UAH',  'valueAddedTaxIncluded': True}
        data = {'__parent__': bid, 'relatedLot': lot.id,
                'value': value}
        lot_value = LotValue(data)
        with self.assertRaises(ValidationError) as e:
            lot_value.validate()
        self.assertEqual(e.exception[0]['relatedLot'][0], u"relatedLot should be one of lots")

        mocked_get_tender.return_value = munchify({'lots': munchify([{'id': lot.id}])})
        data = {'__parent__': bid, 'relatedLot': lot.id, 'value': value}
        lot_value = LotValue(data)
        lot_value.validate()
        self.assertEqual(lot_value.relatedLot, lot.id)
        self.assertEqual(lot_value.value.amount, 479.0)
        self.assertEqual(lot_value.value.currency, u'UAH')


class TestParameter(unittest.TestCase):
    @patch('openprocurement.tender.core.models.get_tender')
    def test_validate_code_and_value(self, mocked_get_tender):
        tender = Tender()
        bid = Bid({'__parent__': tender})
        data = {'code': 'some code', 'value': 0.01}
        parameter = Parameter(data)
        parameter.validate()
        self.assertEqual(parameter.code, u'some code')
        self.assertEqual(parameter.value, 0.01)

        data = {'__parent__': bid, 'code': 'some code', 'value': 0.01}
        parameter = Parameter(data)
        with self.assertRaises(ValidationError) as e:
            parameter.validate()
        self.assertEqual(e.exception[0]['code'][0], u"code should be one of feature code.")

        mocked_get_tender.return_value = munchify({'id': '1', 'name': 'tender', 'features': [
            {'code': 'test', 'enum': [{'value': '1'}, {'value': '2'}]}]})
        data['code'] = 'test'
        parameter.import_data(data)

        with self.assertRaises(ValidationError) as e:
           parameter.validate()
        self.assertEqual(e.exception[0]['value'][0], u"value should be one of feature value.")


class TestBid(unittest.TestCase):
    def test__local_roles__(self):
        model = Bid()
        model.owner = 'test_owner'
        model.owner_token = 'test_token'
        res = model.__local_roles__()
        self.assertEquals(res, {'test_owner_test_token': 'bid_owner'})

    def test__import_data(self):
        model = Bid()
        res = model.import_data(raw_data={})
        self.assertEquals(res, model)

    def test__acl__(self):
        model = Bid()
        model.owner = 'test_owner'
        model.owner_token = 'test_token'
        res = model.__acl__()
        self.assertEquals(res, [('Allow', 'test_owner_test_token', 'edit_bid')])

    def positive_test_for_bid(self):
        data = deepcopy(test_bids[0])
        data['participationUrl'] = 'https://somewhere.ua'
        bid = Bid(data)
        bid.validate()
        self.assertEquals(bid.value.amount, 469.0)
        self.assertEquals(bid.participationUrl, u'https://somewhere.ua')

    def test_validate_participationUrl(self):
        tender = Tender()
        tender.items = munchify([{'id': 1, 'relatedLot': 'lot'}])
        tender.lots = munchify([{'id': '1'}])
        feature = Feature({'code': 'feature code'})
        tender.features = [feature]
        data = deepcopy(test_bids[0])
        data['__parent__'] = tender
        data['participationUrl'] = 'https://somewhere.ua'
        bid = Bid(data)

        with self.assertRaises(ValidationError) as e:
            bid.validate()
        self.assertEqual(e.exception[0]['participationUrl'][0], u"url should be posted for each lot of bid")
        self.assertEqual(e.exception[0]['parameters'][0], u'All features parameters is required.')
        self.assertEqual(e.exception[0]['value'][0], u'value should be posted for each lot of bid')
        self.assertEqual(e.exception[0]['lotValues'][0], u'This field is required.')

    def test_validate_lotValues(self):
        tender = Tender()
        tender.lots = munchify({'id': '1111', 'name': 'lot1'})
        data = munchify({'__parent__': tender})
        model_bid = Bid(data)

        with self.assertRaises(ValidationError) as e:
            model_bid.validate()
        self.assertEqual(e.exception[0]['tenderers'][0], u'This field is required.')

        tender.revisions = [munchify({'date': datetime.now(TZ)})]
        data = munchify({'__parent__': tender})
        model_bid = Bid(data)

        with self.assertRaises(ValidationError) as e:
            model_bid.validate_lotValues(model_bid,  munchify([{'relatedLot': 'test_lot1'},
                                                               {'relatedLot': 'test_lot1'}]))
        self.assertEqual(e.exception[0][0], u'bids don\'t allow duplicated proposals')

    def test_validate_value(self):
        tender = Tender()
        tender.items = munchify([{'id': 1, 'relatedLot': 'lot'}])
        tender.lots = munchify([{'id': '1'}])
        feature = Feature({'code': 'feature code'})
        tender.features = [feature]
        data = deepcopy(test_bids[0])
        data['__parent__'] = tender
        data['participationUrl'] = 'https://somewhere.ua'
        bid = Bid(data)

        with self.assertRaises(ValidationError) as e:
            bid.validate()
        self.assertEqual(e.exception[0]['value'][0], u'value should be posted for each lot of bid')

        tender.lots = None
        tender.value = munchify({
            "amount": 100,
            "currency": "UAH",
            "valueAddedTaxIncluded": True
        })
        data['__parent__'] = tender
        bid = Bid(data)

        with self.assertRaises(ValidationError) as e:
            bid.validate()
        self.assertEqual(e.exception[0]['value'][0], u"value of bid should be less than value of tender")

        tender.value = munchify({
            "amount": 500,
            "currency": "USD",
            "valueAddedTaxIncluded": True
        })
        data['__parent__'] = tender
        bid = Bid(data)

        with self.assertRaises(ValidationError) as e:
            bid.validate()
        self.assertEqual(e.exception[0]['value'][0], u"currency of bid should be identical to currency of value of tender")

        tender.value = munchify({
            "amount": 500,
            "currency": "UAH",
            "valueAddedTaxIncluded": False
        })
        data['__parent__'] = tender
        bid = Bid(data)

        with self.assertRaises(ValidationError) as e:
            bid.validate()
        self.assertEqual(e.exception[0]['value'][0],
                         u"valueAddedTaxIncluded of bid should be identical to valueAddedTaxIncluded of value of tender")
        data['value'] = None
        bid = Bid(data)

        with self.assertRaises(ValidationError) as e:
            bid.validate()
        self.assertEqual(e.exception[0]['value'][0], u'This field is required.')


    def test_validate_parameters(self):
        data = deepcopy(test_bids[0])
        tender = Tender()
        tender.value = MagicMock()
        feature = Feature({'code': 'feature code'})
        tender.features = [feature]
        tender.lots = [1]
        data.update({'__parent__': tender})
        data['__parent__'].items = munchify([{'id': 'test', 'name': 'item1', 'relatedLot': 'test',
                                              'code': 'test', 'enum': [{'value': '12345'}]}])
        bid = Bid(data)

        with self.assertRaises(ValidationError) as e:
            bid.validate()
        self.assertEqual(e.exception[0]['parameters'][0], u"All features parameters is required.")

        tender.lots = []

        with self.assertRaises(ValidationError) as e:
            bid.validate()
        self.assertEqual(e.exception[0]['parameters'][0], u'This field is required.')

        bid.parameters = [{'code': 'invalid code', 'value': 0.01}]

        with self.assertRaises(ValidationError) as e:
            bid.validate()
        self.assertEqual(e.exception[0]['parameters'][0], u"All features parameters is required.")


class TestQuestion(unittest.TestCase):
    @patch('openprocurement.tender.core.models.get_tender')
    def test_validate_relatedItem(self, mocked_get_tender):
        tender = Tender()
        data = {'__parent__': tender, 'author': test_organization, 'title': 'test_title'}
        model = Question(data)
        model.validate()

        self.assertEqual(model.author.name, test_organization['name'])
        self.assertEqual(model.author.identifier.id, test_organization['identifier']['id'])
        self.assertEqual(model.author.identifier.uri, test_organization['identifier']['uri'])
        self.assertEqual(model.author.identifier.id, test_organization['identifier']['id'])
        self.assertEqual(model.title, u'test_title')

        data['questionOf'] = u'lot'
        question_model = Question(data)
        with self.assertRaises(ValidationError) as e:
            question_model.validate()
        self.assertEqual(e.exception[0]['relatedItem'][0], u'This field is required.')

        tender.lots = munchify([{'id': '1234_test_lot'}])
        tender.items = munchify([{'id': '1234_test_item'}])
        mocked_get_tender.return_value = tender

        data['relatedItem'] = 'test'
        data['__parent__'] = tender
        question_model = Question(data)

        with self.assertRaises(ValidationError) as e:
            question_model.validate()
        self.assertEqual(e.exception[0]['relatedItem'][0], u"relatedItem should be one of lots")

        data['questionOf'] = u'item'
        question_model = Question(data)

        with self.assertRaises(ValidationError) as e:
            question_model.validate()
        self.assertEqual(e.exception[0]['relatedItem'][0], u"relatedItem should be one of items")


class TestComplaint(unittest.TestCase):
    @patch('openprocurement.tender.core.models.get_tender')
    def test_serialize(self, mocked_get_tender):
        model = Complaint()
        mocked_get_tender.return_value = munchify({'status': 'active.enquiries'})
        result = Complaint.serialize(model, role='view')
        self.assertEqual(result['status'], u'draft')
        self.assertEqual(result['type'], u'claim')

    def test__local_roles__(self):
        model = Complaint()
        model.owner = 'test_owner'
        model.owner_token = 'token'
        res = Complaint.__local_roles__(model)
        self.assertEqual(res, {'test_owner_token': 'complaint_owner'})

    def test_get_role(self):
        request = MagicMock()
        request.authenticated_role = u'complaint_owner'
        request.json_body = {'data': {'status': u'cancelled'}}
        complaint = Complaint({'__parent__': Root(request)})
        complaint.__parent__.__parent__ = None
        complaint.status = 'cancelled'
        res = complaint.get_role()
        self.assertEqual(res, u'cancellation')

        request.authenticated_role = u'complaint_owner'
        request.json_body = {'data': {'status': u'draft'}}
        complaint = Complaint({'__parent__': Root(request)})
        complaint.__parent__.__parent__ = None
        complaint.status = 'draft'
        res = complaint.get_role()
        self.assertEqual(res, u'draft')

        request.authenticated_role = u'tender_owner'
        request.json_body = {'data': {'status': u'claim'}}
        complaint = Complaint({'__parent__': Root(request)})
        complaint.__parent__.__parent__ = None
        complaint.status = 'claim'
        res = complaint.get_role()
        self.assertEqual(res, u'answer')

        request.authenticated_role = u'complaint_owner'
        request.json_body = {'data': {'status': u'answered'}}
        complaint = Complaint({'__parent__': Root(request)})
        complaint.__parent__.__parent__ = None
        complaint.status = 'answered'
        res = complaint.get_role()
        self.assertEqual(res, u'satisfy')

        request.authenticated_role = u'No_role'
        request.json_body = {'data': {'status': u'no_status'}}
        complaint = Complaint({'__parent__': Root(request)})
        complaint.__parent__.__parent__ = None
        complaint.status = 'no_status'
        res = complaint.get_role()
        self.assertEqual(res, u'invalid')

    def test__acl__(self):
        model = Complaint()
        res = Complaint.__acl__(model)
        self.assertEqual(res, [('Allow', 'g:reviewers', 'edit_complaint'),
                               ('Allow', 'None_None', 'edit_complaint'),
                               ('Allow', 'None_None', 'upload_complaint_documents')])

    @patch('openprocurement.tender.core.models.get_tender')
    def test_validate_complaint(self, mocked_get_tender):
        tender = Tender()
        data = {'__parent__': tender, 'author': test_organization, 'title': u'test_title_complaint'}
        model_complaint = Complaint(data)
        model_complaint.validate()
        self.assertEqual(model_complaint.author.name, test_organization['name'])
        self.assertEqual(model_complaint.author.identifier.id, test_organization['identifier']['id'])
        self.assertEqual(model_complaint.author.identifier.uri, test_organization['identifier']['uri'])
        self.assertEqual(model_complaint.author.identifier.id, test_organization['identifier']['id'])
        self.assertEqual(model_complaint.title, u'test_title_complaint')

        data['status'] = 'answered'
        model_complaint = Complaint(data)

        with self.assertRaises(ValidationError) as e:
            model_complaint.validate()
        self.assertEqual(e.exception[0][u'resolutionType'][0], u'This field is required.')

        data['status'] = 'cancelled'
        model_complaint = Complaint(data)

        with self.assertRaises(ValidationError) as e:
            model_complaint.validate()
        self.assertEqual(e.exception[0][u'cancellationReason'][0], u'This field is required.')

        data['status'] = 'cancelled'
        data['relatedLot'] = uuid4().hex
        mocked_get_tender.return_value = munchify({'lots': [{'id': '1234_test_lot'}]})
        model_complaint = Complaint(data)

        with self.assertRaises(ValidationError) as e:
            model_complaint.validate()
        self.assertEqual(e.exception[0][u'relatedLot'][0], u"relatedLot should be one of lots")


class TestCancellation(unittest.TestCase):
    def test_validate_relatedLot(self):
        tender = Tender()
        data = {'__parent__': tender, 'reason': 'test_reason'}
        model_cancellation = Cancellation(data)
        model_cancellation.validate()
        self.assertEqual(model_cancellation.reason, u'test_reason')
        self.assertEqual(model_cancellation.status, u'pending')
        self.assertEqual(model_cancellation.cancellationOf, u'tender')

        data.update({'__parent__': tender, 'cancellationOf': 'lot', 'reason': 'test_reason'})
        model_cancellation = Cancellation(data)

        with self.assertRaises(ValidationError) as e:
            model_cancellation.validate()
        self.assertEqual(e.exception[0]['relatedLot'][0], u'This field is required.')

        data['__parent__'].lots = munchify([{'id': '1234_test_lot'}])
        data['relatedLot'] = uuid4().hex
        model_cancellation = Cancellation(data)

        with self.assertRaises(ValidationError) as e:
            model_cancellation.validate()
        self.assertEqual(e.exception[0]['relatedLot'][0], u"relatedLot should be one of lots")


class TestAward(unittest.TestCase):

    def test_validate_lotID(self):
        tender = Tender()
        data = {'__parent__': tender, 'title': 'test_title', 'description': 'test_description',
                'suppliers': [test_organization], 'bid_id': uuid4().hex }
        model_award = Award(data)
        self.assertEqual(model_award.title, u'test_title')
        self.assertEqual(model_award.description, u'test_description')

        data['__parent__'].lots = munchify([{'id': '1234_test_lot'}])
        model_award = Award(data)
        with self.assertRaises(ValidationError) as e:
            model_award.validate()
        self.assertEqual(e.exception[0]['lotID'][0], u'This field is required.')

        data['lotID'] = uuid4().hex
        model_award = Award(data)
        with self.assertRaises(ValidationError) as e:
            model_award.validate()
        self.assertEqual(e.exception[0]['lotID'][0], u"lotID should be one of lots")


class TestFeature(unittest.TestCase):
    def test_validate_relatedItem(self):
        tender = Tender()
        data = {'__parent__': tender, 'title': 'test_title', 'enum': [{"value": 0.1, "title": u"До 1000 Вт"},
                                                                      {"value": 0.15, "title": u"Більше 1000 Вт"}]}
        model_feature = Feature(data)
        model_feature.validate()
        self.assertEqual(model_feature.title, u'test_title')
        self.assertEqual(model_feature.featureOf, u'tenderer')

        data['featureOf'] = 'lot'
        model_feature = Feature(data)

        with self.assertRaises(ValidationError) as e:
            model_feature.validate()
        self.assertEqual(e.exception[0][u'relatedItem'][0], u'This field is required.')


        data['__parent__'].items = munchify([{'id': 'test'}])
        data['featureOf'] = 'item'
        data['relatedItem'] = uuid4().hex
        model_feature = Feature(data)

        with self.assertRaises(ValidationError) as e:
            model_feature.validate()
        self.assertEqual(e.exception[0]['relatedItem'][0], u"relatedItem should be one of items")

        data['__parent__'].lots = munchify([{'id': 'test'}])
        data['featureOf'] = 'lot'
        model_feature = Feature(data)

        with self.assertRaises(ValidationError) as e:
            model_feature.validate()
        self.assertEqual(e.exception[0]['relatedItem'][0], u"relatedItem should be one of lots")


class TestLot(unittest.TestCase):
    def test_numberOfBids(self):
        tender = Tender()
        data = {'__parent__': tender}
        tender.bids = munchify([{'lotValues': [{'relatedLot': 'test_id'}],
                                 'status': 'active'}])
        model = Lot(data)
        model.id = 'test_id'
        res = model.numberOfBids
        self.assertEqual(res, 1)

    def test_lot_guarantee(self):
        tender = Tender()
        tender.guarantee = munchify({'currency': 'test', 'amount': '100'})
        data = {'__parent__': tender}
        model = Lot(data)
        model.guarantee = munchify({'currency': 'test', 'amount': '100'})

        res = model.lot_guarantee
        self.assertEqual(res.amount, 100.0)
        self.assertEqual(res.currency, u'test')

    def test_lot_minimalStep(self):
        data = munchify({'__parent__': {'minimalStep': {'currency': 'test_currency', 'valueAddedTaxIncluded': True}},
                         'minimalStep': {'amount': '10'}})
        model = Lot(data)
        res = model.lot_minimalStep
        self.assertEqual(res.amount, 10.0)
        self.assertEqual(res.valueAddedTaxIncluded, True)
        self.assertEqual(res.currency, u'test_currency')

    def test_lot_value(self):
        data = munchify({'__parent__': {'value': {'currency': 'test_currency', 'valueAddedTaxIncluded': True}},
                         'value': {'amount': '10'}})
        model = Lot(data)
        res = model.lot_value
        self.assertEqual(res.amount, 10.0)
        self.assertEqual(res.valueAddedTaxIncluded, True)
        self.assertEqual(res.currency, u'test_currency')

    def test_validate_minimalStep(self):
        data = test_lots[0]
        model_min_step = Lot(data)
        self.assertEqual(model_min_step.title, u'lot title')
        self.assertEqual(model_min_step.description, u'lot description')
        self.assertEqual(model_min_step.value.amount, 500.0)

        value = {'amount': 479, 'currency': 'UAH', 'valueAddedTaxIncluded': True}
        data = munchify({'__parent__': {'value': {'currency': 'UAH', 'valueAddedTaxIncluded': True}},
                         'value': {'amount': '10'}, 'title': 'test_title', 'minimalStep': value})
        model_min_step = Lot(data)

        with self.assertRaises(ValidationError) as e:
            model_min_step.validate()
        self.assertEqual(e.exception[0]['minimalStep'][0], u"value should be less than value of lot")


class TestBaseTender(unittest.TestCase):
    def test__repr__(self):
        data = {'id': 'test_id', '_rev': 'rev_test'}
        model = BaseTender(data)
        res = model.__repr__()
        self.assertEqual(res, "<BaseTender:u'test_id'@u'rev_test'>")

    def test__local_roles__(self):
        data = {'owner': 'test_owner', 'owner_token': 'test_owner_token'}
        model = BaseTender(data)
        res = model.__local_roles__()
        self.assertEqual(res, {'test_owner_test_owner_token': 'tender_owner'})

    def test_doc_id(self):
        data = {'id': 'test_id'}
        model = BaseTender(data)
        res = model.doc_id
        self.assertEqual(res, 'test_id')

    def test_import_data(self):
        tender = Tender()
        data = {'__parent__': tender}
        model = BaseTender(data)
        res = model.import_data(model)
        self.assertEqual(res, model)

    def test_validate_procurementMethodDetails(self):
        tender = Tender()
        data = {'__parent__': tender, 'title': 'test_title', 'mode': 'test'}
        model_base_tender = BaseTender(data)
        model_base_tender.validate()
        self.assertEqual(model_base_tender.title, u'test_title')
        self.assertEqual(model_base_tender.mode, u'test')

        model_base_tender = BaseTender(data)
        model_base_tender.procurementMethodDetails = 'test_procurementMethodDetails'

        with self.assertRaises(ValidationError) as e:
            model_base_tender.validate_procurementMethodDetails()
        self.assertEqual(e.exception[0][0], u"procurementMethodDetails should be used with mode test")


class TestTender(unittest.TestCase):
    def test_get_role(self):
        request = MagicMock()
        request.authenticated_role = u'Administrator'
        data = {'__parent__': Root(request)}
        tender = Tender(data)
        res = tender.get_role()
        self.assertEqual(res, u'Administrator')

        request.authenticated_role = u'chronograph'
        data = {'__parent__': Root(request)}
        tender = Tender(data)
        res = tender.get_role()
        self.assertEqual(res, u'chronograph')

        request.authenticated_role = u'contracting'
        data = {'__parent__': Root(request)}
        tender = Tender(data)
        res = tender.get_role()
        self.assertEqual(res, u'contracting')

        request.context.status = u'test_status'
        request.authenticated_role = u'new_role'
        data = {'__parent__': Root(request)}
        tender = Tender(data)
        res = tender.get_role()
        self.assertEqual(res, u'edit_test_status')

    def test__acl__(self):
        request = MagicMock()
        tender = Tender({'__parent__': Root(request)})
        tender.bids = munchify([{'owner': 'test_owner', 'owner_token': 'owner_token_test'}])
        res = tender.__acl__()
        self.assertEqual(res[0], ('Allow', 'test_owner_owner_token_test', 'create_award_complaint'))
        self.assertEqual(res[1], ('Allow', 'None_None', 'edit_tender'))
        self.assertEqual(res[2], ('Allow', 'None_None', 'upload_tender_documents'))
        self.assertEqual(res[3], ('Allow', 'None_None', 'edit_complaint'))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPeriodEndRequired))
    suite.addTest(unittest.makeSuite(TestModelsUtils))
    suite.addTest(unittest.makeSuite(TestTenderAuctionPeriod))
    suite.addTest(unittest.makeSuite(Test_bids_validation_wrapper))
    suite.addTest(unittest.makeSuite(TestDocument))
    suite.addTest(unittest.makeSuite(TestForOtherValidators))
    suite.addTest(unittest.makeSuite(TestLotAuctionPeriod))
    suite.addTest(unittest.makeSuite(TestItem))
    suite.addTest(unittest.makeSuite(TestContract))
    suite.addTest(unittest.makeSuite(TestLotValue))
    suite.addTest(unittest.makeSuite(TestParameter))
    suite.addTest(unittest.makeSuite(TestBid))
    suite.addTest(unittest.makeSuite(TestQuestion))
    suite.addTest(unittest.makeSuite(TestComplaint))
    suite.addTest(unittest.makeSuite(TestCancellation))
    suite.addTest(unittest.makeSuite(TestAward))
    suite.addTest(unittest.makeSuite(TestFeature))
    suite.addTest(unittest.makeSuite(TestLot))
    suite.addTest(unittest.makeSuite(TestBaseTender))
    suite.addTest(unittest.makeSuite(TestTender))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
