# -*- coding: utf-8 -*-
import unittest

from copy import deepcopy

from openprocurement.tender.core.models import Tender, Contract, Award, Value, Lot
from openprocurement.tender.core.validation import validate_contract_value_data


class TestUpdateContractValue(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestUpdateContractValue, self).__init__(*args, **kwargs)
        self.tender = Tender({
            'status': 'active.enquiries'
        })
        self.tender.value = Value(
            {'amount': 500, 'valueAddedTaxIncluded': True, 'currency': 'UAH'}
        )
        lot = Lot({
            'title': 'lot title',
            'description': 'lot description',
            'value': self.tender.value
        })
        self.tender.lots = [lot]
        award = Award({
            'status': 'active',
            'lotID': lot['id'],
            'value': self.tender.value
        })
        self.tender.awards = [award]
        self.contract = Contract({
            'title': 'contract title',
            'description': 'contract description',
            'awardID': award['id'],
            'value': {'amount': 500, 'amountNet': 500, 'valueAddedTaxIncluded': True, 'currency': 'UAH'}
        })
        self.tender.contracts = [self.contract]
        self.error = lambda data: validate_contract_value_data(
            data=data, tender=self.tender, contract=self.contract
        )

    def test_validation_contract_value_data(self):
        self.assertTrue(self.tender.value.valueAddedTaxIncluded)
        '''
        Conditions:
            tender:value:valueAddedTaxIncluded = True
            lot:value:valueAddedTaxIncluded = True
            award:value:valueAddedTaxIncluded = True
            For lots procedures
        '''
        # update amount
        self.assertEqual(
            self.error(data={'value': {'amount': 0, 'amountNet': 500}}),
            'Can\'t update amount for contract value if lot with valueAddedTaxIncluded'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 1000, 'amountNet': 500}}),
            'Can\'t update amount for contract value if lot with valueAddedTaxIncluded'
        )
        # update amountNet
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 0}}),
            'Value amountNet should be less or equal to amount (500) but not more than 20 percent (400)'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 1000}}),
            'Value amountNet should be less or equal to amount (500) but not more than 20 percent (400)'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 450}}),
            None
        )
        '''
        Conditions:
            tender:value:valueAddedTaxIncluded = True
            lot:value:valueAddedTaxIncluded = True
            award:value:valueAddedTaxIncluded = False
            For lots procedures
        '''
        award = deepcopy(dict(self.tender.awards[0]))
        award['value']['valueAddedTaxIncluded'] = False
        self.tender.awards = [Award(award)]
        self.assertFalse(self.tender.awards[0].value.valueAddedTaxIncluded)
        self.assertTrue(self.tender.lots[0].value.valueAddedTaxIncluded)
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 450}}),
            'Participant is not payer of VAT'
        )

        '''
        Conditions:
            tender:value:valueAddedTaxIncluded = True
            lot.value:valueAddedTaxIncluded = False
            For lots procedures
        '''
        self.assertTrue(self.tender.value.valueAddedTaxIncluded)
        lot = Lot({
            'title': 'lot title',
            'description': 'lot description',
            'value': {'amount': 500, 'valueAddedTaxIncluded': False, 'currency': 'UAH'}
        })
        self.tender.lots = [lot]
        self.tender.awards[0].lotID = lot['id']
        self.assertTrue(self.tender.value.valueAddedTaxIncluded)
        self.assertFalse(self.tender.lots[0].value.valueAddedTaxIncluded)

        # update amount
        self.assertEqual(
            self.error(data={'value': {'amount': 0, 'amountNet': 500}}),
            'Value amount can not be less than amountNet (500)'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 1000, 'amountNet': 500}}),
            'Value amount should be less or equal to awarded amount (500.0)'
        )
        self.tender.awards[0].value.amount = 600
        self.assertEqual(self.tender.awards[0].value.amount, 600)
        self.assertEqual(
            self.error(data={'value': {'amount': 550, 'amountNet': 500}}),
            None
        )
        # update amountNet
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 0}}),
            'Can\'t update amountNet for contract value if lot without valueAddedTaxIncluded'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 1000}}),
            'Can\'t update amountNet for contract value if lot without valueAddedTaxIncluded'
        )
        '''
        Conditions:
            tender:value:valueAddedTaxIncluded = False
            lot.value:valueAddedTaxIncluded = True
            For lots procedures
        '''
        self.tender.value.valueAddedTaxIncluded = False
        lot = Lot({
            'title': 'lot title',
            'description': 'lot description',
            'value': {'amount': 500, 'valueAddedTaxIncluded': True, 'currency': 'UAH'}
        })
        self.tender.lots = [lot]
        self.tender.awards[0].lotID = lot['id']
        self.assertTrue(self.tender.lots[0].value.valueAddedTaxIncluded)
        self.assertFalse(self.tender.value.valueAddedTaxIncluded)

        # update amount
        self.assertEqual(
            self.error(data={'value': {'amount': 0, 'amountNet': 500}}),
            'Can\'t update amount for contract value if lot with valueAddedTaxIncluded'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 1000, 'amountNet': 500}}),
            'Can\'t update amount for contract value if lot with valueAddedTaxIncluded'
        )
        # update amountNet
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 0}}),
            'Value amountNet can not be less then 20 percent of amount (400)'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 1000}}),
            'Value amountNet should be less or equal to awarded amount (600)'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 450}}),
            None
        )
        '''
        Conditions:
            tender:value:valueAddedTaxIncluded = False
            lot.value:valueAddedTaxIncluded = True
            For without lots procedures
        '''
        self.tender.awards[0].lotID = None
        self.assertFalse(self.tender.awards[0].lotID)
        self.assertFalse(self.tender.value.valueAddedTaxIncluded)

        # update amount
        self.assertEqual(
            self.error(data={'value': {'amount': 0, 'amountNet': 500}}),
            'Value amount can not be less than amountNet (500)'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 1000, 'amountNet': 500}}),
            'Value amount should be more or equal to amountNet (500.0) but not more then 20 percent (600.0)'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 550, 'amountNet': 500}}),
            None
        )
        # update amountNet
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 0}}),
            'Can\'t update amountNet for contract value if tender without valueAddedTaxIncluded'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 1000}}),
            'Can\'t update amountNet for contract value if tender without valueAddedTaxIncluded'
        )
        '''
        Conditions:
            tender:value:valueAddedTaxIncluded = False
            lot.value:valueAddedTaxIncluded = True
            For without lots procedures
        '''
        self.tender.value.valueAddedTaxIncluded = True
        self.assertTrue(self.tender.value.valueAddedTaxIncluded)

        # update amount
        self.assertEqual(
            self.error(data={'value': {'amount': 0, 'amountNet': 500}}),
            'Can\'t update amount for contract value if tender with valueAddedTaxIncluded'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 1000, 'amountNet': 500}}),
            'Can\'t update amount for contract value if tender with valueAddedTaxIncluded'
        )
        # update amountNet
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 0}}),
            'Value amountNet should be less or equal to amount (500) but not more than 20 percent (400)'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 1000}}),
            'Value amountNet should be less or equal to amount (500) but not more than 20 percent (400)'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 450}}),
            None
        )
        '''
        Conditions:
            tender:value:valueAddedTaxIncluded = False
            lot.value:valueAddedTaxIncluded = False
            For without lots procedures
        '''
        self.tender.value.valueAddedTaxIncluded = False
        self.tender.lots[0].value.valueAddedTaxIncluded = False
        self.assertFalse(self.tender.value.valueAddedTaxIncluded)
        self.assertFalse(self.tender.lots[0].value.valueAddedTaxIncluded)

        # update amount
        self.assertEqual(
            self.error(data={'value': {'amount': 0, 'amountNet': 500}}),
            'Value amount can not be less than amountNet (500)'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 1000, 'amountNet': 500}}),
            'Value amount should be more or equal to amountNet (500.0) but not more then 20 percent (600.0)'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 550, 'amountNet': 500}}),
            None
        )
        # update amountNet
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 0}}),
            'Can\'t update amountNet for contract value if tender without valueAddedTaxIncluded'
        )
        self.assertEqual(
            self.error(data={'value': {'amount': 500, 'amountNet': 1000}}),
            'Can\'t update amountNet for contract value if tender without valueAddedTaxIncluded'
        )
        # update amount
        '''
        Conditions:
            tender:value:valueAddedTaxIncluded = False
            lot.value:valueAddedTaxIncluded = False
            For lots procedures
        '''
        self.tender.awards[0].lotID = lot['id']
        self.assertFalse(self.tender.awards[0].value.valueAddedTaxIncluded)
        self.assertFalse(self.tender.lots[0].value.valueAddedTaxIncluded)
        self.assertEqual(
            self.error(data={'value': {'amount': 560, 'amountNet': 500}}),
            'Participant is not payer of VAT'
        )


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestUpdateContractValue))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
