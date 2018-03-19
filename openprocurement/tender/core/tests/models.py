# -*- coding: utf-8 -*-
import unittest
from mock import patch, MagicMock
from datetime import datetime, timedelta, time
from schematics.exceptions import ModelValidationError, ValidationError
from openprocurement.tender.core.models import (
    PeriodEndRequired, get_tender, Tender, TenderAuctionPeriod, Question, Item
)
from openprocurement.api.constants import (
    ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017,
    ADDITIONAL_CLASSIFICATIONS_SCHEMES,
    TZ
)
from openprocurement.api.models import AdditionalClassification
from openprocurement.api.utils import get_now
from openprocurement.tender.core.constants import GROUP_336_FROM

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


class TestItemValidation(unittest.TestCase):
    model = Item()
    classification = MagicMock(spec=AdditionalClassification)
    classification.scheme.return_value = 'fake_code'
    date_mock = MagicMock()
    tender = MagicMock(spec=Tender)
    data = {'__parent__': tender, 'classification': {'id': '33651680-8'}}
    classifications = [classification]

    def test_validate_item_classification(self):
        self.tender.get.return_value = []

        if get_now() > GROUP_336_FROM:
            # for 336 code group
            with self.assertRaises(ValidationError) as e:
                self.model.validate_additionalClassifications(self.data, [])
            self.assertEqual(e.exception.message, [u"This field is required."])
 
        self.tender.get.return_value = [self.date_mock]
        if get_now() > GROUP_336_FROM:
            with self.assertRaises(ValidationError) as e:
                self.model.validate_additionalClassifications(self.data, [])
            self.assertEqual(e.exception.message, [u"This field is required."])

        with self.assertRaises(ValidationError) as e:
            self.model.validate_additionalClassifications(self.data, self.classifications)
        self.assertEqual(e.exception.message, [u"One of additional classifications should be one of [{0}].".format(
            ', '.join(ADDITIONAL_CLASSIFICATIONS_SCHEMES))])

        self.date_mock.date.return_value = datetime(2017, 3, 1, tzinfo=TZ)
        self.tender.get.return_value = False
        if get_now() > GROUP_336_FROM:
            with self.assertRaises(ValidationError) as e:
                self.model.validate_additionalClassifications(self.data, self.classifications)
            self.assertEqual(e.exception.message,
                             [u"One of additional classifications should be INN."])

        self.data['classification'] = {'id': '99999999-9'}
        with self.assertRaises(ValidationError) as e:
            self.model.validate_additionalClassifications(self.data, self.classifications)
        self.assertEqual(e.exception.message,
                         [u"One of additional classifications should be one of [{0}].".format(
                             ', '.join(ADDITIONAL_CLASSIFICATIONS_SCHEMES_2017))])


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


class TestQuestionModel(unittest.TestCase):

    def test_serialize_pre_qualification(self):
        question = Question()
        with self.assertRaises(ValueError) as e:
            question.serialize("invalid_role")
        self.assertIsInstance(e.exception, ValueError)
        self.assertEqual(
            e.exception.message,
            "Question Model has no role \"invalid_role\""
        )
        serialized_question = question.serialize("active.pre-qualification")
        self.assertEqual(serialized_question['questionOf'], 'tender')
        self.assertEqual(len(serialized_question['id']), 32)

        serialized_question = question.serialize(
            "active.pre-qualification.stand-still")
        self.assertEqual(serialized_question['questionOf'], 'tender')
        self.assertEqual(len(serialized_question['id']), 32)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPeriodEndRequired))
    suite.addTest(unittest.makeSuite(TestItemValidation))
    suite.addTest(unittest.makeSuite(TestModelsUtils))
    suite.addTest(unittest.makeSuite(TestTenderAuctionPeriod))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
