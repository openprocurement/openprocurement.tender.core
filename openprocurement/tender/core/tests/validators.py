# -*- coding: utf-8 -*-
import unittest
import munch
from datetime import date, timedelta
from mock import MagicMock, patch
from openprocurement.tender.core.tests.base import BaseWebTest
from schematics.exceptions import ValidationError


from openprocurement.tender.core.validation import (validate_bid_data,
                                                    validate_tender_data,
                                                    validate_question_data,
                                                    validate_complaint_data,
                                                    validate_LotValue_value,
                                                    validate_contract_signing,
                                                    validate_bid_operation_period,
                                                    validate_update_contract_value,
                                                    validate_bid_operation_not_in_tendering,
                                                    validate_bid_status_update_not_to_pending,
                                                    validate_update_contract_only_for_active_lots)


def hello():
    return 'Make hello greate again'


def function_for_check_accreditation(item):
    if item == 'a':
        return False
    else:
        return True


class ClassRequestTenderForType(dict):
    complaints = munch.munchify({'model_class': 'must_be_model_class'})
    questions = munch.munchify({'model_class': 'must_be_model_class'})
    bids = munch.munchify({'model_class': 'must_be_model_class'})
    edit_accreditation = False
    validated = {'bid': {'qwerty': 1}}


class ValidationTest(BaseWebTest):
    def setUp(self):
        super(ValidationTest, self).setUp()
        self.request = MagicMock()

    @patch('openprocurement.tender.core.validation.validate_json_data')
    @patch('openprocurement.tender.core.validation.validate_data')
    @patch('openprocurement.tender.core.validation.update_logging_context')
    def test_validate_tender_data(self,
                                  mocked_update_logging_context,
                                  mocked_validate_data,
                                  mock_validate_json_data):
        data = {'data': '1984'}
        mock_validate_json_data.return_value = data

        self.request.tender_from_data.return_value = munch.munchify(
            {'create_accreditation': 'aaaaa',
             'procuring_entity_kinds': 'look'})
        self.request.check_accreditation = function_for_check_accreditation

        with self.assertRaises(Exception):
            validate_tender_data(self.request)

        mocked_update_logging_context.assert_called_once_with(self.request, {
            'tender_id': '__new__'})
        self.request.tender_from_data.assert_called_once_with(data,
                                                              create=False)
        self.request.errors.add.assert_called_with('procurementMethodType',
                                                   'accreditation',
                                                   'Broker Accreditation level does'
                                                   ' not permit tender creation')
        mocked_validate_data.return_value = {'deggy': 'norby'}
        self.request.tender_from_data.return_value = munch.munchify(
            {'create_accreditation': 'bjork',
             'procuring_entity_kinds': 'look'})

        with self.assertRaises(Exception):
            validate_tender_data(self.request)

        self.request.errors.add.assert_called_with('procurementMethodType',
                                                   'mode',
                                                   'Broker Accreditation level does'
                                                   ' not permit tender creation')
        mocked_validate_data.return_value = {
            'procuringEntity': {'kind': 'dom_come'}, 'mode': 'is'}
        self.request.check_accreditation.return_value = False
        validate_tender_data(self.request)

        self.request.errors.add.assert_called_with('procuringEntity', 'kind',
                                                   "'dom_come' procuringEntity cannot"
                                                   " publish this type of procedure. Only l, o, o, k are allowed.")

    @patch('openprocurement.tender.core.validation.get_now')
    @patch('openprocurement.tender.core.validation.raise_operation_error')
    def test_validate_contract_signing(self, mocked_raise_operation_error,
                                       mocked_get_now):
        mocked_get_now.return_value = 3
        self.request.context.awardID = '1'
        awards = munch.munchify({'awards':
                                     [munch.munchify({'id': '1',
                                                      'complaintPeriod': {
                                                          'endDate': {
                                                              'isoformat': hello}},
                                                      'lotID': 5,
                                                      'complaints': [
                                                          munch.munchify(
                                                              {'status': 'yes',
                                                               'relatedLot': 'qwerty'})]})],
                                 'status': 'active',
                                 'complaints': [munch.munchify({'status': 'yes',
                                                                'relatedLot': 'qwerty'})],
                                 'block_complaint_status': [1, 2, 3, 4, 5, 6]})

        self.request.validated.__getitem__.return_value = awards
        validate_contract_signing(self.request)
        mocked_raise_operation_error.assert_called_once_with(self.request,
                                                             "Can't sign contract before stand-still"
                                                             " period end (Make hello greate again)")

        awards = munch.munchify({'awards':
                                     [munch.munchify({'id': '1',
                                                      'complaintPeriod': {
                                                          'endDate': {
                                                              'isoformat': hello}},
                                                      'lotID': 'qwerty',
                                                      'complaints': [
                                                          munch.munchify(
                                                              {'status': 'yes',
                                                               'relatedLot': 'qwerty'})]})],
                                 'status': 'active',
                                 'complaints': [munch.munchify({'status': 1,
                                                                'relatedLot': 'qwerty'})],
                                 'block_complaint_status': [1, 2, 3, 4, 5, 6]})
        self.request.validated.__getitem__.return_value = awards
        validate_contract_signing(self.request)

        mocked_raise_operation_error.assert_called_with(self.request,
                                                        "Can't sign contract before"
                                                        " reviewing all complaints")

    @patch('openprocurement.tender.core.validation.raise_operation_error')
    def test_update_contract_value(self, mocked_raise_operation_error):
        awards = munch.munchify({'awards':
                                     [munch.munchify({'id': '1',
                                                      'value': {'amount': 3},
                                                      'complaintPeriod': {
                                                          'endDate': {
                                                              'isoformat': hello}},
                                                      'lotID': 5,
                                                      'complaints': [
                                                          munch.munchify(
                                                              {'status': 'yes',
                                                               'relatedLot': 'qwerty'})]})],
                                 'status': 'active',
                                 'complaints': [munch.munchify({'status': 'yes',
                                                                'relatedLot': 'qwerty'})],
                                 'block_complaint_status': [1, 2, 3, 4, 5, 6]})

        self.request.validated = {'tender': 1, 'data': {'not_value': 'yes'}}
        validate_update_contract_value(self.request)
        self.assertEqual(self.request.content_configurator.reverse_awarding_criteria.call_count, 0)

        self.request.validated = {'tender': awards, 'data': {'value': {'valueAddedTaxIncluded': 7,
                                                                       'currency': 7,
                                                                       'amount': 3,
                                                                       }}}
        self.request.context.awardID = '1'
        validate_update_contract_value(self.request)

        call_list = mocked_raise_operation_error.call_args_list
        call_args_first = call_list[0][0]
        call_args_second = call_list[1][0]
        self.assertEqual(call_args_first, (self.request, "Can't update valueAddedTaxIncluded for contract value"))
        self.assertEqual(call_args_second, (self.request, "Can't update currency for contract value"))

        self.request.validated = {'tender': awards, 'data': {'value': {'valueAddedTaxIncluded': 7,
                                                                       'currency': 7,
                                                                       'amount': 7,
                                                                       }}}

        validate_update_contract_value(self.request)
        mocked_raise_operation_error.assert_called_with(self.request,
                                                        'Value amount should be'
                                                        ' equal to awarded amount (3)')

        self.request.content_configurator.reverse_awarding_criteria = False
        validate_update_contract_value(self.request)
        mocked_raise_operation_error.assert_called_with(self.request, 'Value amount'
                                                                      ' should be less or'
                                                                      ' equal to awarded amount (3)')

    @patch('openprocurement.tender.core.validation.raise_operation_error')
    def test_validate_update_contract_only_for_active_lots(self, mocked_raise_operation_error):
        self.request.context.awardID = 7

        tender = munch.munchify({'lots':
                                     [{'id': 7,
                                       'lotID': 8,
                                       'status': 'active'}],
                                 'awards':
                                     [{'id': 7,
                                       'lotID': 7}]})
        self.request.validated = {'tender': tender}
        validate_update_contract_only_for_active_lots(self.request)
        self.assertEqual(mocked_raise_operation_error.called, False)

        tender = munch.munchify({'lots':
                                     [{'id': 8,
                                       'lotID': 7,
                                       'status': 'not_active'}],
                                 'awards':
                                     [{'id': 7,
                                       'lotID': 7}]})
        self.request.validated = {'tender': tender}
        validate_update_contract_only_for_active_lots(self.request)
        self.assertEqual(mocked_raise_operation_error.called, False)

        tender = munch.munchify({'lots':
                                     [{'id': 7,
                                       'lotID': 7,
                                       'status': 'active'}],
                                 'awards':
                                     [{'id': 7,
                                       'lotID': 7}]})
        self.request.validated = {'tender': tender}
        validate_update_contract_only_for_active_lots(self.request)
        self.assertEqual(mocked_raise_operation_error.called, False)

        tender = munch.munchify({'lots':
                                     [{'id': 7,
                                       'lotID': 7,
                                       'status': 'not_active'}],
                                 'awards':
                                     [{'id': 7,
                                       'lotID': 7}]})
        self.request.validated = {'tender': tender}
        validate_update_contract_only_for_active_lots(self.request)
        mocked_raise_operation_error.assert_called_once_with(self.request,
                                                             'Can update contract'
                                                             ' only in active lot status')

    def test_validate_LotValue_value(self):
        value = MagicMock()
        tender = MagicMock()
        relatedLot = 42

        validate_LotValue_value(tender, relatedLot, value)
        value.amount = 1984
        value.currency = 'coin'
        value.valueAddedTaxIncluded = 'not_iam'
        tender.lots = [munch.munchify({'id': 42, 'value': {'amount': 1983,
                                                           'currency': 'motsocoin',
                                                           'valueAddedTaxIncluded': 'iam'}}),
                       munch.munchify({'id': 5})]

        with self.assertRaises(ValidationError) as error:
            validate_LotValue_value(tender, relatedLot, value)
        message_error = error.exception.message[0]
        self.assertEqual(message_error, 'value of bid should be less than value of lot')

        value.amount = 1982

        with self.assertRaises(ValidationError) as error:
            validate_LotValue_value(tender, relatedLot, value)
        message_error = error.exception.message[0]
        self.assertEqual(message_error, 'currency of bid should be identical to'
                                        ' currency of value of lot')
        value.currency = 'motsocoin'

        with self.assertRaises(ValidationError) as error:
            validate_LotValue_value(tender, relatedLot, value)
        message_error = error.exception.message[0]
        self.assertEqual(message_error, 'valueAddedTaxIncluded of bid should be'
                                        ' identical to valueAddedTaxIncluded of value of lot')

    @patch('openprocurement.tender.core.validation.validate_data')
    @patch('openprocurement.tender.core.validation.update_logging_context')
    @patch('openprocurement.tender.core.validation.error_handler')
    def test_validate_complaint_data(self, mocked_error_handler,
                                     mocked_update_logging_context, mocked_validate_data):
        self.request.check_accreditation.return_value = False
        with self.assertRaises(Exception) as err:
            validate_complaint_data(self.request)
        self.request.errors.add.assert_called_with('procurementMethodType',
                                                   'accreditation',
                                                   'Broker Accreditation'
                                                   ' level does not permit'
                                                   ' complaint creation')

        mocked_error_handler.assert_called_with(self.request.errors)

        self.request.check_accreditation.return_value = True
        self.request.tender = munch.munchify({'not_mode': 'is',
                                              'edit_accreditation': None})
        with self.assertRaises(Exception) as err:
            validate_complaint_data(self.request)

        self.request.errors.add.assert_called_with('procurementMethodType',
                                                   'mode', 'Broker Accreditation'
                                                           ' level does not permit'
                                                           ' complaint creation')
        mocked_error_handler.assert_called_with(self.request.errors)

        self.request.tender = munch.munchify({'mode': 'is',
                                              'edit_accreditation': None})

        tender = ClassRequestTenderForType()
        tender['mode'] = 'is'
        self.request.tender = tender
        mocked_validate_data.return_value = 'result'
        result = validate_complaint_data(self.request)
        self.assertEqual(result, 'result')
        mocked_update_logging_context.assert_called_once_with(self.request, {'complaint_id': '__new__'})
        mocked_validate_data.assert_called_once_with(self.request, 'must_be_model_class')

    @patch('openprocurement.tender.core.validation.validate_data')
    @patch('openprocurement.tender.core.validation.update_logging_context')
    @patch('openprocurement.tender.core.validation.error_handler')
    def test_validate_question_data(self, mocked_error_handler,
                                     mocked_update_logging_context, mocked_validate_data):
        self.request.check_accreditation.return_value = False
        with self.assertRaises(Exception) as err:
            validate_question_data(self.request)
        self.request.errors.add.assert_called_with('procurementMethodType',
                                                   'accreditation',
                                                   'Broker Accreditation level'
                                                   ' does not permit question creation')

        mocked_error_handler.assert_called_with(self.request.errors)

        self.request.check_accreditation.return_value = True
        self.request.tender = munch.munchify({'not_mode': 'is',
                                              'edit_accreditation': None})
        with self.assertRaises(Exception) as err:
            validate_question_data(self.request)

        self.request.errors.add.assert_called_with('procurementMethodType',
                                                   'mode', 'Broker Accreditation'
                                                           ' level does not permit'
                                                           ' question creation')
        mocked_error_handler.assert_called_with(self.request.errors)

        self.request.tender = munch.munchify({'mode': 'is',
                                              'edit_accreditation': None})

        tender = ClassRequestTenderForType()
        tender['mode'] = 'is'
        self.request.tender = tender
        mocked_validate_data.return_value = 'result'
        result = validate_question_data(self.request)
        self.assertEqual(result, 'result')
        mocked_update_logging_context.assert_called_once_with(self.request, {'question_id': '__new__'})
        mocked_validate_data.assert_called_once_with(self.request, 'must_be_model_class')

    @patch('openprocurement.tender.core.validation.raise_operation_error')
    def test_validate_bid_status_update_not_to_pending(self, mocked_raise_operation_error):
        self.request.authenticated_role = 'Administrator'

        validate_bid_status_update_not_to_pending(self.request)

        self.assertEqual(0, self.request.validated.__getitem__.call_count)

        self.request.authenticated_role = 'NotAdministrator'
        self.request.validated = {'data': {'status': 'pending'}}
        validate_bid_status_update_not_to_pending(self.request)
        self.assertEqual(0, mocked_raise_operation_error.call_count)

        self.request.validated = {'data': {'status': 'not_pending'}}
        validate_bid_status_update_not_to_pending(self.request)

        mocked_raise_operation_error.assert_called_once_with(self.request, "Can't update bid "
                                                                           "to (not_pending) status")

    @patch('openprocurement.tender.core.validation.raise_operation_error')
    @patch('openprocurement.tender.core.validation.get_now')
    def test_validate_bid_operation_period(self, mocked_get_now, mocked_raise_operation_error):
        yesterday = date.today() - timedelta(1)
        tomorrow = date.today() + timedelta(1)
        today = date.today()
        day_before_yesterday = date.today() - timedelta(2)
        self.request.validated = {'tender': munch.munchify({'tenderPeriod': {'startDate': yesterday,
                                                                             'endDate': tomorrow}})}
        mocked_get_now.return_value = today
        validate_bid_operation_period(self.request)

        self.assertEqual(mocked_raise_operation_error.call_count, 0)

        mocked_get_now.return_value = day_before_yesterday
        validate_bid_operation_period(self.request)
        mocked_raise_operation_error.assert_called_with(self.request,
                                                        'Bid can be deleted only during'
                                                        ' the tendering period:'
                                                        ' from ({}) to ({}).'.format(yesterday.isoformat(),
                                                                                    tomorrow.isoformat()))

        self.request.authenticated_role = 'NotAdministrator'
        self.request.method = 'PUT'
        validate_bid_operation_period(self.request)
        mocked_raise_operation_error.assert_called_with(self.request,
                                                        'Bid can be updated only during'
                                                        ' the tendering period:'
                                                        ' from ({}) to ({}).'.format(yesterday.isoformat(),
                                                                                    tomorrow.isoformat()))

        self.request.method = 'PATCH'
        validate_bid_operation_period(self.request)
        mocked_raise_operation_error.assert_called_with(self.request,
                                                        'Bid can be updated only during'
                                                        ' the tendering period:'
                                                        ' from ({}) to ({}).'.format(yesterday.isoformat(),
                                                                                    tomorrow.isoformat()))
        self.request.authenticated_role = 'Administrator'
        self.request.method = 'PATCH'
        validate_bid_operation_period(self.request)
        mocked_raise_operation_error.assert_called_with(self.request,
                                                        'Bid can be deleted only during'
                                                        ' the tendering period:'
                                                        ' from ({}) to ({}).'.format(yesterday.isoformat(),
                                                                                    tomorrow.isoformat()))

    @patch('openprocurement.tender.core.validation.raise_operation_error')
    def test_validate_bid_operation_not_in_tendering(self, mocked_raise_operation_error):
        self.request.validated = {'tender_status': 'active.tendering'}
        validate_bid_operation_not_in_tendering(self.request)

        self.assertEqual(mocked_raise_operation_error.call_count, 0)

        self.request.validated = {'tender_status': 'not_active.tendering'}

        validate_bid_operation_not_in_tendering(self.request)

        mocked_raise_operation_error.assert_called_with(self.request, "Can't delete bid in current "
                                                                      "(not_active.tendering) tender status" )

        self.request.authenticated_role = 'NotAdministrator'
        self.request.method = 'PUT'
        validate_bid_operation_not_in_tendering(self.request)

        mocked_raise_operation_error.assert_called_with(self.request, "Can't update bid in current "
                                                                      "(not_active.tendering) tender status" )
        self.request.method = 'PATCH'
        validate_bid_operation_not_in_tendering(self.request)

        mocked_raise_operation_error.assert_called_with(self.request, "Can't update bid in current "
                                                                      "(not_active.tendering) tender status" )
        self.request.authenticated_role = 'Administrator'
        self.request.method = 'PATCH'
        validate_bid_operation_not_in_tendering(self.request)

        mocked_raise_operation_error.assert_called_with(self.request, "Can't delete bid in current "
                                                                      "(not_active.tendering) tender status" )

    @patch('openprocurement.tender.core.validation.validate_bid_documents')
    @patch('openprocurement.tender.core.validation.validate_data')
    @patch('openprocurement.tender.core.validation.error_handler')
    @patch('openprocurement.tender.core.validation.update_logging_context')
    def test_validate_bid_data(self, mocked_update_logging_context, mocked_error_handler,
                               mocked_validate_data, mocked_validate_bid_documents):
        self.request.check_accreditation.return_value = False

        with self.assertRaises(Exception) as err:
            validate_bid_data(self.request)

        self.request.errors.add.assert_called_with('procurementMethodType',
                                                   'accreditation', 'Broker Accreditation level '
                                                                    'does not permit bid creation')

        mocked_error_handler.assert_called_with(self.request.errors)

        self.request.check_accreditation.return_value = True
        self.request.tender = ClassRequestTenderForType()
        with self.assertRaises(Exception) as err:
            validate_bid_data(self.request)

        self.request.errors.add.assert_called_with('procurementMethodType', 'mode',
                                                   'Broker Accreditation level does'
                                                   ' not permit bid creation')

        mocked_error_handler.assert_called_with(self.request.errors)

        self.request.tender['mode'] = 'it_is'
        self.request.validated = {'bid': None}
        mocked_validate_data.return_value = 'result'

        result = validate_bid_data(self.request)
        mocked_validate_data.assert_called_with(self.request, 'must_be_model_class')
        mocked_update_logging_context.assert_called_with(self.request, {'bid_id': '__new__'})
        self.assertEqual(result, 'result')

        self.request.validated = {'bid': {'key1':'value1', 'key2':'value2'}}
        result = validate_bid_data(self.request)
        self.assertEqual(mocked_validate_bid_documents.call_count, 0)

        self.request.validated = {'bid': {'documents':'value1', 'key2':'value2'}}
        mocked_validate_bid_documents.return_value = None

        result = validate_bid_data(self.request)

        mocked_validate_bid_documents.assert_called_with(self.request)
        self.assertEqual(result, None)

        mocked_validate_bid_documents.return_value = {'key1': 'value1', 'key2': 'value2'}
        result = validate_bid_data(self.request)

        self.assertEqual(result, 'result')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ValidationTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
