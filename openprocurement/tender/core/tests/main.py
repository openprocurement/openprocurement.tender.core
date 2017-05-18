# -*- coding: utf-8 -*-
import unittest

from openprocurement.tender.core.tests import (
    auth, auction, award, bid, cancellation,
    chronograph, complaint, contract, document,
    models, lot, tender, question, utils
)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(auth.suite())
    suite.addTest(auction.suite())
    suite.addTest(award.suite())
    suite.addTest(bid.suite())
    suite.addTest(cancellation.suite())
    suite.addTest(chronograph.suite())
    suite.addTest(complaint.suite())
    suite.addTest(contract.suite())
    suite.addTest(document.suite())
    suite.addTest(models.suite())
    suite.addTest(lot.suite())
    suite.addTest(tender.suite())
    suite.addTest(question.suite())
    suite.addTest(utils.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
