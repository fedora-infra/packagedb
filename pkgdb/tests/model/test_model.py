from nose.tools import *

from pkgdb.lib.test import slow, DBTest
from migrate.versioning.api import version

class TestModel(DBTest):

    def test_migrate_table_init(self):
        MigrateVersion = self.model.MigrateVersion

        # test if migrate_version was initialized
        migrate = self.session.query(MigrateVersion).one()
        assert_equals(migrate.repository_id, 'Fedora Package DB')
        assert_equals(migrate.repository_path, 'db_repo')
        assert_equals(migrate.version, int(version('db_repo')))



