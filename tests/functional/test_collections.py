from nose.tools import *
from pkgdb.lib.test import current, WebAppTest
from turbogears import controllers, expose
import simplejson as json


class TestCollections(WebAppTest):

    def test_by_simple_and_canonical_name(self):
        # populate with test data
        from pkgdb.model import Collection, SC_ACTIVE
        coll = Collection('Testing', 'devel', SC_ACTIVE, 'owner', 'master', '.f14')
        self.session.add(coll)

        #FIXME: wouldn't be by_name and by_branchname more intuitive? 
        # same for  collctn_name -> name and collctn_ver -> version args

        # FEATURE: As a common user I want to search for collection's 
        # full name by branchname and viceversa in JSON format 
        # so I can read the data from my software.
        res = self.app.get('/collections/by_simple_name/Testing/devel?tg_format=json')
        assert_equals(res.status, '200 OK')
        body = json.loads(res.body)
        assert_true(body['status'])
        assert_equals(body['name'], 'master')

        res = self.app.get('/collections/by_canonical_name/master?tg_format=json')
        assert_equals(res.status, '200 OK')
        body = json.loads(res.body)
        assert_true(body['status'])
        assert_equals(body['collctn_name'], 'Testing')
        assert_equals(body['collctn_ver'], 'devel')

