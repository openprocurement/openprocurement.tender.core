# -*- coding: utf-8 -*-
import os
import unittest
from datetime import datetime
from pyramid import testing
from pyramid.tests.test_authentication import TestBasicAuthAuthenticationPolicy

from openprocurement.api.auth import AuthenticationPolicy
from openprocurement.api.constants import SANDBOX_MODE
from openprocurement.tender.core.tests.base import (
    TenderContentWebTest
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


class AccreditationTenderTest(TenderContentWebTest):
    relative_to = os.path.dirname(__file__)

    def test_create_tender_accreditation(self):
        self.app.authorization = ('Basic', ('broker1', ''))
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')

        self.app.authorization = ('Basic', ('broker2', ''))
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


class AccreditationTenderQuestionTest(TenderContentWebTest):
    def test_create_tender_question_accreditation(self):
        self.app.authorization = ('Basic', ('broker2', ''))
        response = self.app.post_json('/tenders/{}/questions'.format(self.tender_id),
                                      {'data': {'title': 'question title', 'description': 'question description', 'author': test_organization}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')

        self.app.authorization = ('Basic', ('broker1', ''))
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

        self.app.authorization = ('Basic', ('broker1', ''))
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

        self.app.authorization = ('Basic', ('broker1', ''))
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
