import simplejson as json
from nose.tools import *
from pkgdb.lib.test import WebAppTest, current

class TestLists(WebAppTest):
    
    def test_buildtags(self):
        from pkgdb.model import SC_ACTIVE, Executable

        coll = self.setup_collection('Test', '1', SC_ACTIVE)
        repo = self.setup_repo('Testing Devel', 'devel', 'tests/functional/repo/', coll) 
        pkg = self.setup_package('name', colls=[coll])

        exe1 = Executable('exe1')
        app1 = self.setup_app('Name 1', executable=exe1)
        app1.tag('tag1')
        app1.tag('tag2')
        self.session.flush()

        exe2 = Executable('exe2')
        app2 = self.setup_app('Name 2', executable=exe2)
        app2.tag('tag2')
        self.session.flush()
        app2.tag('tag2')
        app2.tag('tag3')

        pkgbuild = self.setup_build('name-pkg', package=pkg, repos=[repo], 
            executables=[exe1, exe2])

        self.session.flush()
        
        res = self.app.get('/lists/buildtags/devel?tg_format=json')
        assert_equals(res.status, '200 OK')
        body = json.loads(res.body)
        assert_true(body['status'])

        expected_buildtags = {
            'devel': {
                'name-pkg': dict(tag1=1, tag2=2, tag3=1)}}
        assert_equals(body['buildtags'], expected_buildtags)
