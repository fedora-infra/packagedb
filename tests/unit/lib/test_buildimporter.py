from nose.tools import *

from pkgdb.lib.test import DBTest
from pkgdb.lib.rpmlib import RPM
from pkgdb.lib.test import RPMMock
from pkgdb.lib.desktop import Desktop

from sqlalchemy.orm.exc import NoResultFound

class TestBuildImporter(DBTest):

    def test_basic_import(self):
        from pkgdb.lib.buildimporter import BuildImporter
        from pkgdb.model import SC_ACTIVE, Application, Executable

        coll = self.setup_collection('Test', '1', SC_ACTIVE)
        repo = self.setup_repo('Testing Devel', 'devel', 'tests/functional/repo/', coll) 
        pkg = self.setup_package('test-pkg', colls=[coll])

        desktop = Desktop('Test App', 'Generic name', 'Comment', command='/usr/bin/test')

        # fake rpm
        rpm = RPMMock('test-pkg', '1.0-1', filelist=[
                '/usr/bin/test',
                '/usr/sbin/test',
                '/usr/share/applications/test.desktop',
                '/usr/share/icons/hicolor/48x48/apps/test.png'], 
            executables = ['/usr/bin/test', '/usr/sbin/test'], desktop=[desktop])

        bi = BuildImporter(repo)
        build = bi.process(rpm)

        app = self.session.query(Application).filter_by(name='Test App').one()
        assert_equals(app.name, 'Test App')

        exe = self.session.query(Executable).filter_by(executable='test').one()
        expected_builds = {build: ['/usr/bin/', '/usr/sbin/']}
        assert_equals(exe.builds, expected_builds)

        assert_equals(app.executable, exe)
        assert_equals(app.builds, [build])

        assert_equals(app.alt_names, {u'Test App': set([(coll, pkg),])})


    def test_appcollection_import(self):
        from pkgdb.lib.buildimporter import BuildImporter
        from pkgdb.model import SC_ACTIVE, Application, Executable

        coll1 = self.setup_collection('Test', '1', SC_ACTIVE, 't1')
        coll2 = self.setup_collection('Test', '2', SC_ACTIVE, 't2')
        repo1 = self.setup_repo('Testing 1', 'T1', 'tests/somerepo/', coll1) 
        repo2 = self.setup_repo('Testing 2', 'T2', 'tests/someotherrepo/', coll2) 
        pkg = self.setup_package('test-pkg', colls=[coll1, coll2])
        other_pkg = self.setup_package('test-other-pkg', colls=[coll1, coll2])

        desktop1 = Desktop('Test App', 'Generic name', 'Comment', command='test')
        desktop2 = Desktop('Test App NG', 'Generic name', 'Comment', command='test')
        desktop3 = Desktop('Test App 2', 'Generic name', 'Comment', command='test')

        # fake rpm
        rpm1 = RPMMock('test-pkg', '1.0-1', filelist=[
                '/usr/bin/test',
                '/usr/share/applications/test.desktop',
                '/usr/share/icons/hicolor/48x48/apps/test.png'], 
            executables = ['/usr/bin/test'], desktop=[desktop1])
        rpm2 = RPMMock('test-other-pkg', '1.0-1', filelist=[
                '/usr/bin/test',
                '/usr/share/applications/test.desktop',
                '/usr/share/icons/hicolor/48x48/apps/test.png'], 
            executables = ['/usr/bin/test'], desktop=[desktop2])
        rpm3 = RPMMock('test-pkg', '1.0-2', filelist=[
                '/usr/bin/test',
                '/usr/share/applications/test.desktop',
                '/usr/share/icons/hicolor/48x48/apps/test.png'], 
            executables = ['/usr/bin/test'], desktop=[desktop3])

        bi1 = BuildImporter(repo1)
        build = bi1.process(rpm1)

        bi2 = BuildImporter(repo2)
        build = bi2.process(rpm1)
        build = bi2.process(rpm2)

        app = self.session.query(Application).filter_by(name='Test App').one()

        assert_equals(app.alt_names, {
            u'Test App': set([
                (coll1, pkg), 
                (coll2, pkg)]),
            u'Test App NG': set([
                (coll2, other_pkg)])})

        # rpm 3 shuld REPLACE Test App with Test App 2 for coll2
        build = bi2.process(rpm3)

        app = self.session.query(Application).filter_by(name='Test App').one()

        assert_equals(app.alt_names, {
            u'Test App': set([
                (coll1, pkg)]),
            u'Test App 2': set([
                (coll2, pkg)]),
            u'Test App NG': set([
                (coll2, other_pkg)])})


    def test_update_of_application_and_package_record(self):
        from pkgdb.lib.buildimporter import BuildImporter
        from pkgdb.model import SC_ACTIVE, Application, Executable
        from pkgdb.model import SC_UNDER_DEVELOPMENT

        coll = self.setup_collection('Test', '1', SC_ACTIVE, 't1')
        coll_devel = self.setup_collection('Test', '2', SC_UNDER_DEVELOPMENT, 't2')
        repo = self.setup_repo('Test 1', '1', 'tests/some-repo/', coll) 
        repo_devel = self.setup_repo('Test 2', '2', 'tests/some-devel-repo/', coll_devel) 
        pkg = self.setup_package('test-pkg', colls=[coll, coll_devel], 
            summary='summary', description='description')

        exe = Executable('test')
        self.session.add(exe)

        app = Application('Test App', 'descr', 'URL', 
                'desktop', 'summary', command='test', commandargs='',
                executable=exe)

        self.session.add(app)

        # Check that app was not updated with data other than from RAWHIDE
        # NON-RAWHIDE
        desktop = Desktop('Test App Old', 'Generic name', 'Comment', command='test')
        rpm = RPMMock('test-pkg', '1.0-1', 
            filelist=[
                '/usr/bin/test',
                '/usr/share/applications/test.desktop'], 
            executables=['/usr/bin/test'], 
            desktop=[desktop], 
            summary='old summary',
            description='old description')

        # save setup
        self.session.flush()

        bi = BuildImporter(repo)
        build = bi.process(rpm)

        assert_raises(NoResultFound, self.session.query(Application).filter_by(name='Test App Old').one)

        app = self.session.query(Application).filter_by(name='Test App').one()
        assert_equals(app.name, 'Test App')
        assert_equals(app.summary, 'summary')
        assert_equals(app.description, 'descr')

        assert_equals(build.package.summary, 'summary')
        assert_equals(build.package.description, 'description')
        
        # RAWHIDE
        desktop_devel = Desktop('Test App NG', 'Generic name NG', 'Comment NG', command='test')
        rpm_devel = RPMMock('test-pkg', '1.0-1.1', 
            filelist=[
                '/usr/bin/test',
                '/usr/share/applications/test.desktop'], 
            executables = ['/usr/bin/test'], 
            desktop=[desktop_devel],
            summary='summary NG',
            description='description NG')

        bi = BuildImporter(repo_devel)
        build = bi.process(rpm_devel)

        app = self.session.query(Application).filter_by(name='Test App NG').one()
        assert_equals(app.name, 'Test App NG')
        assert_equals(app.summary, 'Generic name NG')
        assert_equals(app.description, 'Comment NG')

        assert_equals(build.package.summary, 'summary NG')
        assert_equals(build.package.description, 'description NG')
        

    def test_app_match_by_name(self):
        from pkgdb.lib.buildimporter import BuildImporter
        from pkgdb.model import SC_ACTIVE, Application

        coll = self.setup_collection('Test', '1', SC_ACTIVE)
        repo = self.setup_repo('Testing Devel', 'devel', 'tests/functional/repo/', coll) 
        pkg = self.setup_package('test-pkg', colls=[coll])

        app = Application('Test App', 'descr', 'URL', 'desktop', 'summary', 'descr')
        self.session.add(app)

        desktop = Desktop('Test App', 'Summary', 'Descr', command='test')

        # fake rpm
        rpm = RPMMock('test-pkg', '1.0-1', filelist=[
                '/usr/bin/test',
                '/usr/share/applications/test.desktop',
                '/usr/share/icons/hicolor/48x48/apps/test.png'], 
            executables = ['/usr/bin/test'], desktop=[desktop])

        self.session.flush()

        bi = BuildImporter(repo)
        build = bi.process(rpm)
        
        # command and executable should be added to app
        app = self.session.query(Application).one()
        assert_equals(app.command, 'test')
        assert_equals(app.commandargs, '')
        assert_true(app.executableid)


