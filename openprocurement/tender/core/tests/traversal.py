# -*- coding: utf-8 -*-

import os
import unittest

from openprocurement.tender.core.traversal import Root, factory
from openprocurement.tender.core.tests.base import BaseWebTest

from pyramid.security import (
    ALL_PERMISSIONS,
    Allow,
    Deny,
    Everyone,
)
from mock import MagicMock, patch
from munch import munchify


class TraversalTest(BaseWebTest):
    test_data = {
        "status": "cancelled",
        "id": '123456789',
        "awards": [{
            "id": "award_id", 'name': 'award',
            "complaints": [
                {"id": "complaint_id", 'name': 'complaint',
                 'documents': [
                     {'id': 'document_id', 'name': 'document'}]}],
            'documents': [
                {'id': 'document_id', 'name': 'document'}]
        }],
        "contracts": [{
            "id": "contract_id", 'name': 'contract',
            "complaints": [
                {"id": "complaint_id", 'name': 'complaint',
                 'documents': [
                     {'id': 'document_id', 'name': 'document'}]}],
            'documents': [
                {'id': 'document_id', 'name': 'document'}]
        }],
        "bids": [{
            "id": "bid_id", 'name': 'bid',
            "complaints": [
                {"id": "complaint_id", 'name': 'complaint',
                 'documents': [
                     {'id': 'document_id', 'name': 'document'}]}],
            'documents': [
                {'id': 'document_id', 'name': 'document'}]
        }],
        "complaints": [{
            "id": "complaint_id", 'name': 'complaint',
            'documents': [
                {'id': 'document_id', 'name': 'document'}]
        }],
        "cancellations": [{
            "id": "cancellation_id", 'name': 'cancellation',
            'documents': [
                {'id': 'document_id', 'name': 'document'}]
        }],
        "documents": [{
            "id": "document_id", 'name': 'document',
        }],
        "questions": [{
            "id": "question_id", 'name': 'question',
        }],
        "lots": [{
            "id": "lot_id", 'name': 'lot',
        }],
    }
    relative_to = os.path.dirname(__file__)
    test_ctl = [
            # (Allow, Everyone, ALL_PERMISSIONS),
            (Allow, Everyone, 'view_listing'),
            (Allow, Everyone, 'view_tender'),
            (Deny, 'broker05', 'create_bid'),
            (Deny, 'broker05', 'create_complaint'),
            (Deny, 'broker05', 'create_question'),
            (Deny, 'broker05', 'create_tender'),
            (Allow, 'g:brokers', 'create_bid'),
            (Allow, 'g:brokers', 'create_complaint'),
            (Allow, 'g:brokers', 'create_question'),
            (Allow, 'g:brokers', 'create_tender'),
            (Allow, 'g:auction', 'auction'),
            (Allow, 'g:auction', 'upload_tender_documents'),
            (Allow, 'g:contracting', 'extract_credentials'),
            (Allow, 'g:competitive_dialogue', 'create_tender'),
            (Allow, 'g:chronograph', 'edit_tender'),
            (Allow, 'g:Administrator', 'edit_tender'),
            (Allow, 'g:Administrator', 'edit_bid'),
            (Allow, 'g:admins', ALL_PERMISSIONS),
            (Allow, 'g:bots', 'upload_tender_documents')
            ]

    def test_root(self):
        ctl = Root.__acl__
        self.assertEqual(ctl, TraversalTest.test_ctl)

    def test_factory(self):
        request = MagicMock()
        request.method = 'POST'
        request.validated = {'tender_src': {}}
        request.matchdict = {}
        response = factory(request)
        self.assertEqual(response.__acl__, TraversalTest.test_ctl)
        self.assertEqual(response.request.matchdict, {})
        request.method = 'GET'
        request.tender = munchify(TraversalTest.test_data)

        request.matchdict = {
            'tender_id': 'id',
            'award_id': 'award_id',
            'complaint_id': 'complaint_id',
            'document_id': 'document_id'
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['awards'][0]['complaints'][0]['documents'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'award_id': 'award_id',
            'complaint_id': 'complaint_id',
        }
        response = factory(request)
        self.assertEqual(response.id,  self.test_data['awards'][0]['complaints'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'award_id': 'award_id',
            'document_id': 'document_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['awards'][0]['documents'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'award_id': 'award_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['awards'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'contract_id': 'contract_id',
            'document_id': 'document_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['contracts'][0]['documents'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'contract_id': 'contract_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['contracts'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'bid_id': 'bid_id',
            'document_id': 'document_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['bids'][0]['documents'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'bid_id': 'bid_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['bids'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'complaint_id': 'complaint_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['complaints'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'complaint_id': 'complaint_id',
            'document_id': 'document_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['complaints'][0]['documents'][0]['id'])


        request.matchdict = {
            'tender_id': 'id',
            'cancellation_id': 'cancellation_id',
            'document_id': 'document_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['cancellations'][0]['documents'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'cancellation_id': 'cancellation_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['cancellations'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'document_id': 'document_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['documents'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'question_id': 'question_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['questions'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
            'lot_id': 'lot_id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['lots'][0]['id'])

        request.matchdict = {
            'tender_id': 'id',
        }
        response = factory(request)
        self.assertEqual(response.id, self.test_data['id'])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TraversalTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
