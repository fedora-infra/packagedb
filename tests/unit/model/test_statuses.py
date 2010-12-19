from nose.tools import *
from unittest import TestCase


class TestStatuses(TestCase):


    def test_statusdict(self):
        from pkgdb.model import StatusDict

        data = (('a', 1), ('b', 2)) 
        sd = StatusDict(data)

        assert_equals(sd['a'], 1)
        assert_equals(sd[1], 'a')

        try: 
            sd['c']
            raise AssertionError('KeyError was not raised')
        except KeyError, e:
            assert_equals(str(e), "'Unknown status: c'")

        try: 
            sd['c'] = 3
            raise AssertionError('TypeError was not raised')
        except TypeError, e:
            assert_equals(str(e), 'Item assignment is not supported')


    def test_STATUS(self):
        from pkgdb.model import STATUS, SC_APPROVED

        assert_equals(STATUS[SC_APPROVED], 'Approved')
        assert_equals(STATUS['Approved'], SC_APPROVED)


