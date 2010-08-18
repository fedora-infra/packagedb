from nose.tools import *
from turbogears import config
from pkgdb.lib.test import slow, DBTest
from turbojson import jsonify

class TestApps(DBTest):

    def test_Application(self):
        from pkgdb.model import Application, Tag
        
        app = Application('name', 'description', 'url', 'apptype', 'summary')

        # test tag()
        tag = app.tag('tag')
        assert_true(isinstance(tag, Tag))
        assert_equals(tag.name, 'tag')

        # test scores
        assert_equals(app.scores, {tag: 1})
        assert_equals(jsonify.encode(app.scores), '{"tag": 1}')

        # jsonify Application
        app.json_props = {'Application':['scores']}
        assert_true('{"tag": 1}' in jsonify.encode(app))


