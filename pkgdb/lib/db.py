# -*- coding: utf-8 -*-
#
# Copyright © 2007-2010  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2, or (at your option) any later version.  This
# program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the GNU
# General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA. Any Red Hat trademarks that are incorporated in the source
# code or documentation are not subject to the GNU General Public License and
# may only be used or replicated with the express permission of Red Hat, Inc.
#
# Red Hat Author(s): Martin Bacovsky <mbacovsk@redhat.com>
#
from sqlalchemy import DDL, Table, Column
from sqlalchemy.sql.expression import ColumnClause

def View(name, metadata, selectable):
    """Create DB view definition in SA model

    DB view workaround for SA. It is able to create and drop 
    the view properly during metadata.create_all/drop_all.

    :arg name: name of the view in the datatabase
    :arg metadata: metadata where the definition should land
    :arg selectable: SA select representing the view
    :returns: Table instance representing the view
    """

    t = Table(name, metadata)

    for c in selectable.c:
        # make aggregate columns behave like normal columns
        if not isinstance(c, Column) and isinstance(c, ColumnClause):
            c = Column(c.name, c.type)
        c._make_proxy(t)

    create_ddl_1 = "DROP TABLE %s" % (name)
    create_ddl_2 = "CREATE VIEW %s AS %s" % (
        name, selectable)
    drop_ddl_1 = "DROP VIEW %s" % (name)
    drop_ddl_2 = "CREATE TABLE %s(id integer)" % (name)

    DDL(create_ddl_1).execute_at('after-create', metadata)
    DDL(create_ddl_2).execute_at('after-create', metadata)
    DDL(drop_ddl_1).execute_at('before-drop', metadata)
    DDL(drop_ddl_2).execute_at('before-drop', metadata)

    return t


def initial_data(table, column_names, *rows):
    """Insert data into table after creation

    :arg table: Table instance the data have to be inserted in
    :arg column_names: list of column names
    :arg rows: one or more rows (list of values)
    """

    def unify_value(value):
        if callable(value):
            return value()
        else:
            return value

    def onload(event, schema_item, connection):
        insert = table.insert()
        connection.execute(
            insert,
            [dict(zip(
                    column_names, 
                    (unify_value(value) for value in column_values)))
                for column_values in rows])

    table.append_ddl_listener('after-create', onload)


