from nose.tools import *
from turbogears import config
from pkgdb.lib.test import slow, DBTest
from migrate.versioning.api import version
from fedora.tg.json import SABase

class TestModel(DBTest):

    def test_migratetable_init(self):
        MigrateVersion = self.model.MigrateVersion

        # test if migrate_version was initialized
        migrate = self.session.query(MigrateVersion).one()
        assert_equals(migrate.repository_id, 'Fedora Package DB')
        assert_equals(migrate.repository_path, config.get('database.repo'))
        assert_equals(migrate.version, int(version(config.get('database.repo'))))



