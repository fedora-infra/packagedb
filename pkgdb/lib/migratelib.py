from sqlalchemy import schema
from migrate.changeset import ConstraintChangeset

# this is this is mocking UniqueConstraintfrom python-migrate 0.6
# because we still depend in v 0.5
# recommended import is
# try:
#     from migrate.changeset.constraint import UniqueConstraint
# except:
#     from pkgdb.lib.migratelib import UniqueConstraint
class UniqueConstraint(object):
    """Construct UniqueConstraint

    Migrate's additional parameters:

    :param cols: Columns in constraint.
    :param table: If columns are passed as strings, this kw is required
    :type table: Table instance
    :type cols: strings or Column instances

    """

    def _normalize_columns(self, cols, fullname=False):
        """Given: column objects or names; return col names and
        (maybe) a table"""
        colnames = []
        table = None
        for col in cols:
            if isinstance(col, schema.Column):
                if col.table is not None and table is None:
                    table = col.table
                if fullname:
                    col = '.'.join((col.table.name, col.name))
                else:
                    col = col.name
            colnames.append(col)
        return colnames, table


    def __init__(self, *cols, **kwargs):
        self.colnames, table = self._normalize_columns(cols)
        self.table = kwargs.pop('table', table)

    def autoname(self):
        """Mimic the database's automatic constraint names"""
        return "%s_%s_key" % (self.table.name, self.colnames[0])

    def create(self):
        self.table.bind.execute('ALTER TABLE "%s" ADD CONSTRAINT "%s" UNIQUE (%s)' %
            (self.table.name, self.autoname(), ','.join(self.colnames)))

    def drop(self):
        self.table.bind.execute('ALTER TABLE "%s" DROP CONSTRAINT "%s"' %
            (self.table.name, self.autoname()))

