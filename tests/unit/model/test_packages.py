from nose.tools import *
from pkgdb.lib.test import DBTest
from fedora.tg.json import SABase

class TestPackage(DBTest):

    def test_package(self):
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


class TestPackageListing(DBTest):

    def test_packageListing(self):
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
