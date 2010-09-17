from nose.tools import *
from pkgdb.lib.test import slow, WebAppTest
from turbogears import controllers, expose
import simplejson as json


class TestApplications(WebAppTest):

    def test_application(self):
        # populate with test data
        from pkgdb.model.apps import Application
        app = Application('App', description="Description", 
            url='http://localhost/', apptype='desktop', summary="Summary")
        self.session.add(app)
        # add tag
        app.tag('tag')

        # FEATURE: As a common user I want to have the application detail page also 
        # in JSON format so I can read the data from my software.
        res = self.app.get('/applications/App?tg_format=json')
        assert_equals(res.status, '200 OK')
        body = json.loads(res.body)
        assert_true(body['status'])
        assert_equals(body['app']['scores'], {'tag': 1})

