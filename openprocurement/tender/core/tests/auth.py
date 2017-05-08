# -*- coding: utf-8 -*-
import os
import unittest
from webtest import TestApp
from datetime import datetime, timedelta
from pyramid import testing
from pyramid.paster import get_app
from pyramid.tests.test_authentication import TestBasicAuthAuthenticationPolicy

from openprocurement.api.auth import AuthenticationPolicy
from openprocurement.api.utils import apply_data_patch
from openprocurement.api.constants import SANDBOX_MODE
from openprocurement.api.tests.base import PrefixedRequestClass
from openprocurement.tender.core.tests.base import (
    BaseWebTest, BaseTenderWebTest
)
from openprocurement.tender.belowthreshold.tests.base import (
    test_tender_data, test_organization
)


now = datetime.now()
if SANDBOX_MODE:
    test_tender_data['procurementMethodDetails'] = 'quick, accelerator=1440'
test_tender_data_mode_test = test_tender_data.copy()
test_tender_data_mode_test["mode"] = "test"


class AuthTest(TestBasicAuthAuthenticationPolicy):
    def _makeOne(self, check):
        return AuthenticationPolicy('openprocurement/tender/core/tests/auth.ini', 'SomeRealm')

    test_authenticated_userid_utf8 = None
    test_authenticated_userid_latin1 = None

    def test_unauthenticated_userid_bearer(self):
        request = testing.DummyRequest()
        request.headers['Authorization'] = 'Bearer chrisr'
        policy = self._makeOne(None)
        self.assertEqual(policy.unauthenticated_userid(request), 'chrisr')


class AccreditationTenderTest(BaseWebTest):
    relative_to = os.path.dirname(__file__)

    @classmethod
    def setUpClass(self):
        # set up with 'belowThreshold' plugin
        self.app = TestApp(
            get_app('{}/tests.ini'.format(self.relative_to), options={
                'plugins': 'api,tender_core,belowThreshold'}),
            relative_to=self.relative_to
        )
        self.app.RequestClass = PrefixedRequestClass
        self.couchdb_server = self.app.app.registry.couchdb_server
        self.db = self.app.app.registry.db
        self.db_name = self.db.name

    def test_create_tender_accreditation(self):
        self.app.authorization = ('Basic', ('broker1', ''))
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')

        for broker in ['broker2', 'broker3', 'broker4']:
            self.app.authorization = ('Basic', (broker, ''))
            response = self.app.post_json('/tenders', {"data": test_tender_data}, status=403)
            self.assertEqual(response.status, '403 Forbidden')
            self.assertEqual(response.content_type, 'application/json')
            self.assertEqual(response.json['errors'][0]["description"], "Broker Accreditation level does not permit tender creation")

        self.app.authorization = ('Basic', ('broker1t', ''))
        response = self.app.post_json('/tenders', {"data": test_tender_data}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Broker Accreditation level does not permit tender creation")

        response = self.app.post_json('/tenders', {"data": test_tender_data_mode_test})
        self.assertEqual(response.status, '201 Created')


class TenderContentWebTest(BaseTenderWebTest):
    initial_auth = ('Basic', ('broker', ''))
    initial_data = test_tender_data
    relative_to = os.path.dirname(__file__)

    def set_status(self, status, extra=None):
        data = {'status': status}
        if status == 'active.enquiries':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now).isoformat(),
                    "endDate": (now + timedelta(days=7)).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now + timedelta(days=7)).isoformat(),
                    "endDate": (now + timedelta(days=14)).isoformat()
                }
            })
        elif status == 'active.tendering':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now - timedelta(days=10)).isoformat(),
                    "endDate": (now).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now).isoformat(),
                    "endDate": (now + timedelta(days=7)).isoformat()
                }
            })
        if extra:
            data.update(extra)

        tender = self.db.get(self.tender_id)
        tender.update(apply_data_patch(tender, data))
        self.db.save(tender)

        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('chronograph', ''))
        #response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.app.authorization = authorization
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        return response

    def setUp(self):
        super(TenderContentWebTest, self).setUp()
        self.create_tender()

    @classmethod
    def setUpClass(self):
        # set up with 'belowThreshold' plugin
        self.app = TestApp(
            get_app('{}/tests.ini'.format(self.relative_to), options={
                'plugins': 'api,tender_core,belowThreshold'}),
            relative_to=self.relative_to
        )
        self.app.RequestClass = PrefixedRequestClass
        self.couchdb_server = self.app.app.registry.couchdb_server
        self.db = self.app.app.registry.db
        self.db_name = self.db.name


class AccreditationTenderQuestionTest(TenderContentWebTest):
    def test_create_tender_question_accreditation(self):
        self.app.authorization = ('Basic', ('broker2', ''))
        response = self.app.post_json('/tenders/{}/questions'.format(self.tender_id),
                                      {'data': {'title': 'question title', 'description': 'question description', 'author': test_organization}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')

        for broker in ['broker1', 'broker3', 'broker4']:
            self.app.authorization = ('Basic', (broker, ''))
            response = self.app.post_json('/tenders/{}/questions'.format(self.tender_id),
                                          {'data': {'title': 'question title', 'description': 'question description', 'author': test_organization}},
                                          status=403)
            self.assertEqual(response.status, '403 Forbidden')
            self.assertEqual(response.content_type, 'application/json')
            self.assertEqual(response.json['errors'][0]["description"], "Broker Accreditation level does not permit question creation")

        self.app.authorization = ('Basic', ('broker2t', ''))
        response = self.app.post_json('/tenders/{}/questions'.format(self.tender_id),
                                      {'data': {'title': 'question title', 'description': 'question description', 'author': test_organization}},
                                      status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Broker Accreditation level does not permit question creation")


class AccreditationTenderQuestionModeTest(TenderContentWebTest):
    initial_data = test_tender_data_mode_test

    def test_create_tender_question_accreditation(self):
        self.app.authorization = ('Basic', ('broker2', ''))
        response = self.app.post_json('/tenders/{}/questions'.format(self.tender_id),
                                      {'data': {'title': 'question title', 'description': 'question description', 'author': test_organization}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')


class AccreditationTenderBidTest(TenderContentWebTest):
    initial_status = 'active.tendering'

    def test_create_tender_bid_accreditation(self):
        self.app.authorization = ('Basic', ('broker2', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(self.tender_id),
                                      {'data': {'tenderers': [test_organization], "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')

        for broker in ['broker1', 'broker3', 'broker4']:
            self.app.authorization = ('Basic', (broker, ''))
            response = self.app.post_json('/tenders/{}/bids'.format(self.tender_id),
                                          {'data': {'tenderers': [test_organization], "value": {"amount": 500}}},
                                          status=403)
            self.assertEqual(response.status, '403 Forbidden')
            self.assertEqual(response.content_type, 'application/json')
            self.assertEqual(response.json['errors'][0]["description"], "Broker Accreditation level does not permit bid creation")

        self.app.authorization = ('Basic', ('broker2t', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(self.tender_id),
                                      {'data': {'tenderers': [test_organization], "value": {"amount": 500}}},
                                      status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Broker Accreditation level does not permit bid creation")


class AccreditationTenderBidModeTest(TenderContentWebTest):
    initial_data = test_tender_data_mode_test
    initial_status = 'active.tendering'

    def test_create_tender_bid_accreditation(self):
        self.app.authorization = ('Basic', ('broker2t', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(self.tender_id),
                                      {'data': {'tenderers': [test_organization], "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')


class AccreditationTenderComplaintTest(TenderContentWebTest):
    def test_create_tender_complaint_accreditation(self):
        self.app.authorization = ('Basic', ('broker2', ''))
        response = self.app.post_json('/tenders/{}/complaints'.format(self.tender_id),
                                      {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')

        for broker in ['broker1', 'broker3', 'broker4']:
            self.app.authorization = ('Basic', (broker, ''))
            response = self.app.post_json('/tenders/{}/complaints'.format(self.tender_id),
                                          {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}},
                                          status=403)
            self.assertEqual(response.status, '403 Forbidden')
            self.assertEqual(response.content_type, 'application/json')
            self.assertEqual(response.json['errors'][0]["description"], 'Broker Accreditation level does not permit complaint creation')

        self.app.authorization = ('Basic', ('broker2t', ''))
        response = self.app.post_json('/tenders/{}/complaints'.format(self.tender_id),
                                      {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}},
                                      status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], 'Broker Accreditation level does not permit complaint creation')


class AccreditationTenderComplaintModeTest(TenderContentWebTest):
    initial_data = test_tender_data_mode_test

    def test_create_tender_complaint_accreditation(self):
        self.app.authorization = ('Basic', ('broker2t', ''))
        response = self.app.post_json('/tenders/{}/complaints'.format(self.tender_id),
                                      {'data': {'title': 'complaint title', 'description': 'complaint description', 'author': test_organization, 'status': 'claim'}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(AuthTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
