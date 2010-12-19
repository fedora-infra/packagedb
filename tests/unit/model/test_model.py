from nose.tools import *
from turbogears import config
from turbojson import jsonify
from pkgdb.lib.test import slow, DBTest, rollback
from migrate.versioning.api import version
from fedora.tg.json import SABase

class TestModel(DBTest):

    @rollback
    def _test_MigrateTable_init(self):
        MigrateVersion = self.model.MigrateVersion

        # test if migrate_version was initialized
        migrate = self.session.query(MigrateVersion).one()
        assert_equals(migrate.repository_id, 'Fedora Package DB')
        assert_equals(migrate.repository_path, config.get('database.repo'))
        assert_equals(migrate.version, int(version(config.get('database.repo'))))


    @rollback
    def _test_Application(self):

        from pkgdb.model import Application, Tag
        app = Application('name', 'description', 'url', 'desktop', 'summary')

        # every model member has to inherit from SABase
        assert_true(isinstance(app, SABase))

        # test tags addition
        tag = app.tag('tag')
        assert_true(isinstance(tag, Tag))
        assert_equals(tag.name, 'tag')

        # test scores - tags nad votes collection
        assert_equals(app.scores, {tag: 1})
        assert_equals(jsonify.encode(app.scores), '{"tag": 1}')

        # jsonify Application
        # check App can jesonify scores
        app.json_props = {'Application':['scores']}
        assert_true('{"tag": 1}' in jsonify.encode(app))
       

    @rollback
    def _test_Collection(self):
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
     

    @rollback 
    def _test_PackageListing(self):
        """
        Test PackageListing public API
        """
        from pkgdb.model import PackageListing, Collection, Package
        from pkgdb.model import SC_APPROVED , SC_UNDER_DEVELOPMENT
        from pkgdb.model import GroupPackageListing, GroupPackageListingAcl
        from pkgdb.model import PersonPackageListing, PersonPackageListingAcl
        
        # create new listing
        # prepare collections
        col = Collection('Test', '1', SC_UNDER_DEVELOPMENT, 'owner', 'ft1', '.ft1')
        self.session.add(col)
        col2 = Collection('Test', '2', SC_UNDER_DEVELOPMENT, 'owner', 'ft2', '.ft2')
        self.session.add(col2)

        # prepare package
        package = Package('package', 'Package for testing', SC_APPROVED)
        self.session.add(package)

        # prepare acls 
        gpl = GroupPackageListing('testgroup')
        gpla = GroupPackageListingAcl('commit', SC_APPROVED)
        gpl.acls2['commit'] = gpla
        ppl = PersonPackageListing('testperson')
        ppla = PersonPackageListingAcl('commit', SC_APPROVED)
        ppl.acls2['commit'] = ppla

        # relate them in listing
        listing = PackageListing('owner', SC_APPROVED)
        listing.collection_ = col
        listing.package_ = package
        listing.groups2['testgroup'] = gpl
        listing.people2['testperson'] = ppl
        self.session.add(listing)
        # FIXME: it would be better to use the alternative collection and package attrs
        # but filling one expects the other to be already set due to many proxies trying 
        # to be clever on us

        # check the data fit all the DB constraints
        self.session.flush()

        # packagename - has to be called after flush, otherwise the proxy does not 
        # have the ids to connect the objects #FIXME
        assert_equals(listing.packagename, package.name)

        # every model member has to inherit from SABase
        assert_true(isinstance(listing, SABase))

        # clone(branchname, author)
        listing2 = listing.clone('ft2', 'author')
        self.session.flush()

        # check cloned listing connects proper objects
        assert_equals(listing2.packagename, package.name)
        assert_equals(listing2.collection.branchname, col2.branchname)

        # check the acls were cloned too
        assert_true(listing2.groups2['testgroup'])
        assert_true(listing2.groups2['testgroup'].acls2['commit'])
        assert_true(listing2.people2['testperson'])
        assert_true(listing2.people2['testperson'].acls2['commit'])


    def _test_Package(self):
        from pkgdb.model import PackageListing, Collection, Package
        from pkgdb.model import SC_UNDER_DEVELOPMENT, SC_APPROVED

        # prepare collections
        col = Collection('Test', '1', SC_UNDER_DEVELOPMENT, 'owner', 'ft1', '.ft1')
        self.session.add(col)
        
        # create package
        package = Package('package', 'Package for testing', SC_APPROVED, 
            description='Description', reviewurl=None, shouldopen=None, 
            upstreamurl=None)
        self.session.add(package)
        self.session.flush()

        # create_listing
        # FIXME: create_listing expect package to have id already set
        # FIXME: collection.add_package(pkg,...) would be much more intuitive
        listing = package.create_listing(col, 'owner', 'Approved', qacontact=None, author_name='me')
        self.session.flush() 

        assert_true(isinstance(listing, PackageListing))
        assert_equals(listing.packagename, package.name)
        assert_equals(listing.collection.branchname, col.branchname)
        # test if default acl were created 
        # FIXME: this should IMO be responsibility of PackageListing
        assert_true(listing.groups2['provenpackager'].acls2['commit'])
        assert_true(listing.groups2['provenpackager'].acls2['build'])
        assert_true(listing.groups2['provenpackager'].acls2['checkout'])


    def test_model(self):
        self._test_MigrateTable_init()
        self._test_Application()
        self._test_Collection()
        self._test_PackageListing()
        self._test_Package()


