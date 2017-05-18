# -*- coding: utf-8 -*-
from mock import Mock

from openprocurement.api.models import plain_role
from openprocurement.tender.core.utils import *
from openprocurement.tender.core.models import enquiries_role
from openprocurement.tender.core.models import (
    Tender as BaseTender, Cancellation, ListType, ModelType)
from openprocurement.tender.core.tests.base import BaseWebTest


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


class UtilsModuleTestException(Exception):
    pass


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
                'registry.db': self.db,
                'errors.add.side_effect': UtilsModuleTestException
            }
        )


class UtilsModuleTest(BaseUtilsModuleTest):

    def test_generate_tender_id(self):
        now = get_now()

        id1 = generate_tender_id(now, self.db)
        self.assertTrue(id1 is not None)

        id2 = generate_tender_id(now, self.db)
        self.assertTrue(id2 is not None)

        self.assertEqual(id1[:-1], id2[:-1])

    def test_tender_serialize(self):
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
        try:
            self.assertTrue(save_tender(self.request))
        except UtilsModuleTestException:
            pass

    def test_apply_patch(self):
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
        self.tender.bids = [Mock(status='draft')]
        self.request.validated['tender'] = self.tender

        # all bids in draft status
        remove_draft_bids(self.request)
        self.assertEqual(self.tender.bids, [])

        # active bid should remain
        self.tender.bids = [Mock(status='draft'), Mock(status='active')]
        remove_draft_bids(self.request)
        self.assertEqual(len(self.tender.bids), 1)

    def test_cleanup_bids_for_cancelled_lots(self):
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

        # without questions and lots
        self.assertFalse(has_unanswered_questions(self.tender))

        # without lots
        self.tender.questions = [Mock(answer=False, questionOf='tender')]
        self.assertTrue(has_unanswered_questions(self.tender))

        # with lot and question
        self.tender.lots = [Mock(id=1, status='active')]
        self.assertTrue(has_unanswered_questions(self.tender))

    def test_has_unanswered_complaints(self):

        # without lots and complaints
        self.assertFalse(has_unanswered_complaints(self.tender))

        # without lots
        self.tender.complaints = [Mock(status='claim')]
        self.assertTrue(has_unanswered_complaints(self.tender))

        # with lot and complaint
        self.tender.lots = [Mock(id=1, status='active')]
        self.tender.complaints[0].relatedLot = 1
        self.assertTrue(has_unanswered_complaints(self.tender))

    def test_extract_tender(self):
        self.tender.title = '[TESTING]'
        self.tender.store(self.db)

        path = 'localhost:80/api/2.3'

        # invalid path
        self.assertEqual(extract_tender(self.request), None)

        # invalid unicode path
        self.request.environ['PATH_INFO'] = '\x81'
        try:
            self.assertEqual(extract_tender(self.request), None)
        except URLDecodeError:
            pass

        # invalid tender id
        self.request.environ['PATH_INFO'] = path + '/tenders/{}'.format('some_id')
        try:
            self.assertEqual(extract_tender(self.request), None)
        except UtilsModuleTestException:
            pass

        # valid path and id
        self.request.environ['PATH_INFO'] = path + '/tenders/{}'.format(self.tender.id)
        extract_tender(self.request)
        self.request.tender_from_data.assert_called_with(self.tender.serialize())

    def test_tender_from_data(self):
        tender = Tender
        tender.procurementMethodType = Mock(default='belowThreshold')

        # not implementde procurementMethodType
        self.request.registry.tender_procurementMethodTypes = {}
        try:
            tender_from_data(self.request, {})
        except UtilsModuleTestException:
            pass

        # should return tender with data
        register_tender_procurementMethodType(self.request, tender)
        res = tender_from_data(self.request, {'title': '[TESTING]'})
        self.assertTrue(isinstance(res, Tender))
        self.assertEqual(res.title, '[TESTING]')

    def test_rounding_shouldStartAfter(self):
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
        now = get_now()

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
