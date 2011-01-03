from unittest import TestCase
from nose.tools import *

from sqlalchemy import MetaData

from pkgdb.lib.test import create_stuff_table, create_more_stuff_table
from pkgdb.lib.test import number_of_tables, bound_metadata, unbound_metadata
from pkgdb.lib.test import table_names
from pkgdb.lib.test import DBTest

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


class TestDBTest(DBTest):
    
    def test_setup_collection(self):
        from pkgdb.model import SC_ACTIVE, Collection
        coll = self.setup_collection('Test', '1', SC_ACTIVE)
        assert_true(isinstance(coll, Collection))
        assert_equals(coll.name, 'Test')
        assert_equals(coll.version, '1')
        assert_equals(coll.statuscode, SC_ACTIVE)


    def test_setup_repo(self):
        from pkgdb.model import Repo, SC_ACTIVE
        import pkgdb
        coll = self.setup_collection('Test', '1', SC_ACTIVE)

        repo = self.setup_repo('Testing Devel', 'devel', 'tests/functional/repo/', coll) 
        assert_true(isinstance(repo, Repo))
        assert_equals(repo.name, 'Testing Devel')
        assert_equals(repo.shortname, 'devel')
        assert_equals(repo.url, 'tests/functional/repo/')
        assert_equals(repo.mirror, 'file://%s/' % pkgdb.__path__[0])
        assert_equals(repo.active, True)
        assert_equals(coll.repos, [repo])


    def test_setup_package(self):
        from pkgdb.model import Package, SC_ACTIVE
        coll = self.setup_collection('Test', '1', SC_ACTIVE)

        pkg = self.setup_package('test-pkg', colls=[coll])
        assert_true(isinstance(pkg, Package))
        assert_equals(pkg.name, 'test-pkg')
        assert_equals(coll.listings2['test-pkg'].package, pkg)


        
