from nose.tools import *
from pkgdb.lib.test import DBTest
from fedora.tg.json import SABase

class TestCollection(DBTest):

    def test_collection(self):
        """
        Test Collection public API
        """
        from pkgdb.model import Collection, SC_UNDER_DEVELOPMENT

        # create collection
        # with minimal params
        colmin = Collection('Test', '1', SC_UNDER_DEVELOPMENT, 'owner', 'ft1', '.ft1')
        self.session.add(colmin)

        # every model member has to inherit from SABase
        assert_true(isinstance(colmin, SABase))
        # test short_name property
        assert_equals(colmin.short_name, 'FT-1')

        # with full params
        colfull = Collection(name='Test', version='2', statuscode=SC_UNDER_DEVELOPMENT, 
            owner='owner', branchname='master', disttag='.ft2', publishurltemplate=None, 
            pendingurltemplate=None, summary='Testing', description='Testing')
        self.session.add(colfull)

        # test short_name property translate master branch properly
        assert_equals(colfull.short_name, 'devel')

        self.session.flush()

        # test unify_branchname/s
        branchname = Collection.unify_branchname('FT-1')
        assert_equals(branchname, 'ft1')
        branchname = Collection.unify_branchname('ft2')
        assert_equals(branchname, 'ft2')
        branchname = Collection.unify_branchname('devel')
        assert_equals(branchname, 'master')
        branchnames = Collection.unify_branchnames(['devel', 'FT-1', 'ft2'])
        assert_equals(branchnames, ['master', 'ft1', 'ft2'])
        branchnames = Collection.unify_branchnames('FT-1')
        assert_equals(branchnames, ['ft1'])
        assert_raises(TypeError, Collection.unify_branchnames, self)

        # read collections
        colls = self.session.query(Collection).all()
        assert_equals(len(colls), 2)
     

