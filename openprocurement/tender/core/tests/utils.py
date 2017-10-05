# -*- coding: utf-8 -*-
import unittest
from mock import Mock, patch
from datetime import datetime, time, timedelta

from openprocurement.api.utils import get_now
from openprocurement.api.models import plain_role
from openprocurement.api.constants import WORKING_DAYS, SANDBOX_MODE, TZ
from openprocurement.tender.core.models import (
    Tender as BaseTender, Cancellation, ListType, ModelType)
from openprocurement.tender.core.models import enquiries_role
from openprocurement.tender.core.tests.base import BaseWebTest
from openprocurement.tender.core.tests.nose_todo_plugin import warnTODO


now = get_now()


class Tender(BaseTender):
    class Options:
        roles = {
            'plain': plain_role,
            'active.enquiries': enquiries_role
        }
    block_tender_complaint_status = ['claim', 'answered', 'pending']

    cancellations = ListType(ModelType(Cancellation), default=list())
    lots = []
    bids = []
    items = []
    features = []
    questions = []
    complaints = []


class BaseUtilsModuleTest(BaseWebTest):

    def setUp(self):
        super(BaseUtilsModuleTest, self).setUp()
        self.tender = Tender()
        self.request = Mock(
            context=self.tender,
            authenticated_userid='broker',
            logging_context={},
            validated={},
            environ={},
            **{
                'registry.db': self.db
            }
        )


class UtilsModuleTest(BaseUtilsModuleTest):

    def test_generate_tender_id(self):
        from openprocurement.tender.core.utils import generate_tender_id

        id1 = generate_tender_id(now, self.db)
        self.assertTrue(id1 is not None)

        id2 = generate_tender_id(now, self.db)
        self.assertTrue(id2 is not None)

        self.assertEqual(id1[:-1], id2[:-1])

    def test_tender_serialize(self):
        from openprocurement.tender.core.utils import tender_serialize

        # should return empty dictionary
        self.request.tender_from_data.return_value = self.tender

        res = tender_serialize(self.request, {}, [])
        self.assertEqual(res, {})

        # tender from data is None
        self.request.tender_from_data.return_value = None

        res = tender_serialize(self.request, {}, [])
        self.assertEqual(res.keys(), ['procurementMethodType', 'dateModified', 'id'])
        for key in res:
            self.assertEqual(res[key], '')

    def test_save_tender(self):
        from openprocurement.tender.core.utils import save_tender

        self.tender.mode = 'test'
        self.request.validated.update({
            'tender': self.tender,
            'tender_src': self.tender.serialize()
        })
        self.assertTrue(save_tender(self.request))

        # status change
        cancellation = Cancellation({'reason': '[TESTING]', 'status': 'pending'})
        self.tender.status = 'active.tendering'
        self.tender.cancellations.append(cancellation)
        self.request.validated['tender_src'] = self.tender.serialize()

        cancellation.status = 'active'
        self.tender.status = 'cancelled'
        self.assertTrue(save_tender(self.request))

        # model validation error
        self.tender.mode = self.tender.title = None
        self.request.validated['tender_src'] = self.tender.serialize()

        self.assertEqual(save_tender(self.request), None)
        self.assertEqual(self.request.errors.status, 422)
        self.request.errors.add.assert_called_once_with('body', 'title', [u'This field is required.'])

    def test_apply_patch(self):
        from openprocurement.tender.core.utils import apply_patch

        self.request.validated.update({
            'tender': self.tender,
            'tender_src': self.tender._initial,
            'data': {'title': '[Test]'}
        })

        # without saving
        self.assertEqual(apply_patch(self.request, save=False), None)
        self.assertEqual(self.tender.title, '[Test]')
        self.assertTrue(self.tender.id is None)
        self.assertTrue(self.tender.rev is None)

        # with saving
        self.request.validated['data'] = {'mode': 'test'}
        self.assertTrue(apply_patch(self.request))
        self.assertEqual(self.tender.title_en, '[TESTING] ')
        self.assertTrue(self.tender.dateModified is not None)
        self.assertTrue(self.tender.id is not None)

    def test_remove_draft_bids(self):
        from openprocurement.tender.core.utils import remove_draft_bids

        self.tender.bids = [Mock(status='draft')]
        self.request.validated['tender'] = self.tender

        # all bids in draft status
        remove_draft_bids(self.request)
        self.assertEqual(self.tender.bids, [])

        # active bid should remain
        self.tender.bids = [Mock(status='draft'), Mock(status='active')]
        remove_draft_bids(self.request)
        self.assertEqual(len(self.tender.bids), 1)

    @warnTODO('fix in cleanup_bids_for_cancelled_lots')
    def test_cleanup_bids_for_cancelled_lots(self):
        from openprocurement.tender.core.utils import cleanup_bids_for_cancelled_lots

        self.tender.lots = [Mock(id=1, status='active')]
        self.tender.bids = [Mock(parameters=[], documents=[], **{
                            'lotValues': [Mock(relatedLot=1)]})]
        # no cancelled lots
        cleanup_bids_for_cancelled_lots(self.tender)
        self.assertEqual(len(self.tender.bids), 1)

        # cancel lot
        self.tender.lots[0].status = 'cancelled'
        cleanup_bids_for_cancelled_lots(self.tender)
        self.assertEqual(self.tender.bids, [])

    def test_has_unanswered_questions(self):
        from openprocurement.tender.core.utils import has_unanswered_questions

        # without questions and lots
        self.assertFalse(has_unanswered_questions(self.tender))

        # without lots
        self.tender.questions = [Mock(answer=False, questionOf='tender')]
        self.assertTrue(has_unanswered_questions(self.tender))

        # with lot and question
        self.tender.lots = [Mock(id=1, status='active')]
        self.assertTrue(has_unanswered_questions(self.tender))

    def test_has_unanswered_complaints(self):
        from openprocurement.tender.core.utils import has_unanswered_complaints

        # without lots and complaints
        self.assertFalse(has_unanswered_complaints(self.tender))

        # without lots
        self.tender.complaints = [Mock(status='claim')]
        self.assertTrue(has_unanswered_complaints(self.tender))

        # with lot and complaint
        self.tender.lots = [Mock(id=1, status='active')]
        self.tender.complaints[0].relatedLot = 1
        self.assertTrue(has_unanswered_complaints(self.tender))

    @patch('openprocurement.tender.core.utils.error_handler')
    def test_extract_tender(self, mock_error_handler):
        from openprocurement.tender.core.utils import (
            extract_tender, URLDecodeError
        )

        mock_error_handler.return_value = Exception

        self.tender.title = '[TESTING]'
        self.tender.store(self.db)
        path = 'localhost:80/api/2.3'

        # invalid path
        self.assertEqual(extract_tender(self.request), None)

        # invalid unicode path
        self.request.environ['PATH_INFO'] = '\x81'
        with self.assertRaisesRegexp(URLDecodeError, "'utf8' codec can't decode byte 0x81 in position 0: invalid start byte"):
            extract_tender(self.request)

        # invalid tender id
        self.request.environ['PATH_INFO'] = path + '/tenders/some_id'
        with self.assertRaises(Exception):
            extract_tender(self.request)
        self.assertEqual(self.request.errors.status, 404)
        self.request.errors.add.assert_called_with('url', 'tender_id', 'Not Found')

        # valid path and id
        self.request.environ['PATH_INFO'] = path + '/tenders/{}'.format(self.tender.id)
        extract_tender(self.request)
        self.request.tender_from_data.assert_called_with(self.tender.serialize())

    @patch('openprocurement.tender.core.utils.error_handler')
    def test_tender_from_data(self, mock_error_handler):
        from openprocurement.tender.core.utils import (
            tender_from_data, register_tender_procurementMethodType
        )

        mock_error_handler.return_value = Exception

        tender = Tender
        tender.procurementMethodType = Mock(default='belowThreshold')

        # not implemented procurementMethodType
        self.request.registry.tender_procurementMethodTypes = {}
        with self.assertRaises(Exception):
            tender_from_data(self.request, {})
        self.assertEqual(self.request.errors.status, 415)
        self.request.errors.add.assert_called_once_with('data', 'procurementMethodType', 'Not implemented')

        # should return tender with data
        register_tender_procurementMethodType(self.request, tender)
        res = tender_from_data(self.request, {'title': '[TESTING]'})
        self.assertTrue(isinstance(res, Tender))
        self.assertEqual(res.title, '[TESTING]')

    def test_rounding_shouldStartAfter(self):
        from openprocurement.tender.core.utils import (
            calc_auction_end_time, rounding_shouldStartAfter
        )

        self.tender.enquiryPeriod = Mock()
        start_after = calc_auction_end_time(1, get_now())

        # should return start_after
        self.assertEqual(rounding_shouldStartAfter(start_after, self.tender),
                         start_after)

        # should return next or current midnight
        self.tender.enquiryPeriod.startDate = get_now()
        res = rounding_shouldStartAfter(start_after, self.tender)
        self.assertTrue((res == start_after) or
                        (res.date() - start_after.date() == timedelta(1)))
        self.assertEqual(res.time(), time(0, tzinfo=TZ))

        if SANDBOX_MODE:
            # should return start_after
            self.tender.submissionMethodDetails = 'quick'
            self.assertEqual(rounding_shouldStartAfter(start_after, self.tender),
                             start_after)

    def test_calculate_business_date(self):
        from openprocurement.tender.core.utils import calculate_business_date

        # should just return date + timedelta
        self.assertEqual(calculate_business_date(now, timedelta(3), self.tender),
                         now + timedelta(3))
        self.assertEqual(calculate_business_date(now, timedelta(-1), self.tender),
                         now - timedelta(1))
        if SANDBOX_MODE:
            # should take into acount given accelerator
            self.tender.procurementMethodDetails = 'quick,accelerator=1440'
            self.assertEqual(calculate_business_date(now, timedelta(3), self.tender),
                             now + timedelta(minutes=3))
            self.assertEqual(calculate_business_date(now, timedelta(-3), self.tender),
                             now - timedelta(minutes=3))

        for holiday in WORKING_DAYS:
            date = datetime.strptime(holiday, '%Y-%m-%d')
            for td_days in range(1, 7):
                # weekend and timedelta.days > 0
                res = calculate_business_date(date, timedelta(td_days), working_days=True)
                self.assertTrue(res - date >= timedelta(td_days))
                self.assertTrue(res.weekday() not in [5, 6])
                self.assertFalse(WORKING_DAYS.get(res.date().isoformat(), False))
                count = 0
                while res > date:
                    res -= timedelta(1)
                    if not (WORKING_DAYS.get(res.date().isoformat(), False) or
                            res.weekday() in [5, 6]):
                        count += 1
                self.assertEqual(count, td_days)

                # weekend and timedelta.days < 0
                res = calculate_business_date(date, timedelta(-td_days), working_days=True)
                self.assertTrue(date - res >= timedelta(1))
                self.assertTrue(res.weekday() not in [5, 6])
                self.assertFalse(WORKING_DAYS.get(res.date().isoformat(), False))
                count = 0
                while res < date:
                    if not (WORKING_DAYS.get(res.date().isoformat(), False) or
                            res.weekday() in [5, 6]):
                        count += 1
                    res += timedelta(1)
                self.assertEqual(count, td_days)

            # weekend, timedelta > 0, days=0
            res = calculate_business_date(date, timedelta(minutes=30), working_days=True)
            self.assertTrue(res - date >= timedelta(1))
            self.assertTrue(res.weekday() not in [5, 6])
            self.assertFalse(WORKING_DAYS.get(res.date().isoformat(), False))
            # weekend, timedelta < 0, days=0
            res = calculate_business_date(date, timedelta(minutes=-30), working_days=True)
            self.assertTrue(date - res >= timedelta(1))
            self.assertTrue(res.weekday() not in [5, 6])
            self.assertFalse(WORKING_DAYS.get(res.date().isoformat(), False))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UtilsModuleTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
