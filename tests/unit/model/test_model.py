from nose.tools import *
from turbogears import config
from turbojson import jsonify
from pkgdb.lib.test import slow, DBTest
from migrate.versioning.api import version

class TestModel(DBTest):

    def _test_migrate_table_init(self):
        MigrateVersion = self.model.MigrateVersion

        # test if migrate_version was initialized
        migrate = self.session.query(MigrateVersion).one()
        assert_equals(migrate.repository_id, 'Fedora Package DB')
        assert_equals(migrate.repository_path, config.get('database.repo'))
        assert_equals(migrate.version, int(version(config.get('database.repo'))))


    def _test_application(self):
        self.session.begin()

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
        
        self.session.rollback()

    
    def _test_branch_and_collection(self):
        from pkgdb.model import Collection, CollectionTable, Branch, BranchTable

        self.session.begin()
        conn = self.session.connection(Collection)
        i = CollectionTable.insert()
        conn.execute(i, dict(name='Test', version='2', statuscode=18, owner='owner'))
        s = CollectionTable.select()
        rs = conn.execute(s)
        coll = rs.fetchone()
        i = BranchTable.insert()
        conn.execute(i, dict(collectionid=coll.id, branchname='devel', 
            gitbranchname='master', disttag='.fc2', parentid=None))

        colls = self.session.query(Collection).all()
        assert_equals(len(colls), 1)
        
        self.session.rollback()
    

    def test_model(self):
        self._test_migrate_table_init()
        self._test_application()
        self._test_branch_and_collection() #FIXME: branch and collection concept is broken!


