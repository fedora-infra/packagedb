from nose.tools import *
from turbogears import config
from pkgdb.lib.test import slow, DBTest
from subprocess import Popen, PIPE
import sys

class TestPkgDBSyncYum(DBTest):

    def test_update(self):
        """
        FEATURE: As PkgDB Admin I want package description beeing updated from RAWHIDE builds
        
        FEATURE: As PkgDB Admin I want to have build records for just the builds being available
                 in the active repos.
        """

        from pkgdb.model import Repo, Collection, CollectionTable
        from pkgdb.model import Package, PackageTable, PackageListing
        from pkgdb.model import SC_UNDER_DEVELOPMENT, SC_ACTIVE, SC_APPROVED
        import pkgdb
        
        # db setup, set branch as active
        self.session.begin()
        coll = Collection('Testing', 'devel', SC_ACTIVE, 'owner', 'master', '.f14')
        self.session.add(coll)

        # set up testing repo
        devel_repo = Repo('Testing Devel', 'devel', 'tests/functional/repo/', 
            'file://%s/'%pkgdb.__path__[0], True, None)
        coll.repos.append(devel_repo)
        self.session.add(devel_repo)

        # set up package
        pkg = Package('test-minimal', 'old summary', SC_APPROVED, 'old description')
        self.session.add(pkg)
        self.session.flush()
        pkg_listing = PackageListing('owner', SC_APPROVED, packageid=pkg.id, collectionid=coll.id)
        self.session.add(pkg_listing)

        self.session.commit()
        # end of setup

        # run update script on non-RAWHIDE branch
        output = Popen(['server-scripts/pkgdb-sync-yum', '--verbose', '-c', 'test.cfg', 'update'], stdout=PIPE).communicate()[0]
        print output # output is shown if test fails, absorbed by nose otherwise

        # check that package descr is same
        self.session.refresh(pkg)
        assert_equals(pkg.summary, 'old summary')
        assert_equals(pkg.description, 'old description')


        # set branch as RAWHIDE, clean previously imported data
        self.session.begin()
        conn = self.session.connection(Collection)
        conn.execute("UPDATE collection SET statuscode=%s WHERE id=%s" % (SC_UNDER_DEVELOPMENT, coll.id))
        conn.execute("DELETE FROM packagebuild")
        self.session.commit()
    
        # run update script on RAWHIDE branch
        output = Popen(['server-scripts/pkgdb-sync-yum', '--verbose', '-c', 'test.cfg', 'update'], stdout=PIPE).communicate()[0]
        print output

        # check that package descr was updated
        self.session.refresh(pkg)
        assert_equals(pkg.summary, 'Summary')
        assert_equals(pkg.description, 'Description')

        
        

