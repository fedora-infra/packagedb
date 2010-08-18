from unittest import TestCase
from nose.tools import *

from sqlalchemy import MetaData

from pkgdb.lib.test import create_stuff_table, create_more_stuff_table
from pkgdb.lib.test import number_of_tables, bound_metadata, unbound_metadata
from pkgdb.lib.test import table_names

class TestLibTest(TestCase):

    def test_bound_metadata(self):
        # Was MetaData was created
        metadata = bound_metadata()
        assert_true(isinstance(metadata, MetaData))
        # Is MetaData bound?
        assert_true(metadata.is_bound())
        
    def test_unbound_metadata(self):
        metadata = unbound_metadata()
        # Was MetaData was created
        assert_true(isinstance(metadata, MetaData))
        # Is MetaData bound? - it should not
        assert_false(metadata.is_bound())
        

    def test_number_of_tables(self):
        metadata = bound_metadata()
        # 0 is expected on empty metadata
        assert_equals(number_of_tables(metadata), 0)
        stuff_table = create_stuff_table(metadata)
        # Number > 0 is expected on non-empty metadata
        assert_equals(number_of_tables(metadata), 1)


    def test_table_names(self):
        metadata = bound_metadata()

        # On empty metadata empty set is expected
        assert_equals(table_names(metadata), set())

        stuff_table = create_stuff_table(metadata)
        # List of table names is expected
        assert_equals(table_names(metadata), set(['stuff']))

        more_stuff_table = create_more_stuff_table(metadata)
        # List of table names is expected
        assert_equals(table_names(metadata), set(['stuff', 'more_stuff']))


