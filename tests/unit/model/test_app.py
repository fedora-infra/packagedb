from nose.tools import *
from pkgdb.lib.test import DBTest
from fedora.tg.json import SABase
from turbojson import jsonify
from datetime import datetime

class TestApplication(DBTest):

    def test_json_and_tags(self):
        #TODO: separate nonrelated tests
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


    def test_builds(self):
        from pkgdb.model import Application, Executable, PackageBuild, PkgBuildExecutable, BinaryPackage, SC_ACTIVE
        coll = self.setup_collection('Test', '1', SC_ACTIVE)
        repo = self.setup_repo('Testing Devel', 'devel', 'tests/functional/repo/', coll) 
        pkg = self.setup_package('name', colls=[coll])
        exe = Executable('exe')
        app = self.setup_app('Name 1', executable=exe)

        pkgbuild = self.setup_build('name-pkg', package=pkg, repos=[repo], 
            executables=[exe])

        self.session.flush()

        assert_true(app.builds, [pkgbuild])

