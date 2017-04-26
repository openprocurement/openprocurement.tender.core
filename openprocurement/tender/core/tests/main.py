# -*- coding: utf-8 -*-
import unittest

from openprocurement.tender.core.tests import tender, utils, models


def suite():
    suite = unittest.TestSuite()
    suite.addTest(models.suite())
    suite.addTest(utils.suite())
    suite.addTest(tender.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
