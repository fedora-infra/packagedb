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
from sqlalchemy.ext import compiler
from sqlalchemy import DDL, Table, ForeignKeyConstraint
import sqlalchemy.sql.util
from sqlalchemy import topological
from sqlalchemy.sql import visitors

_dependencies = None
_sort_tables_bak = None

def View(name, metadata, selectable):

    t = Table(name, metadata)

    for c in selectable.c:
        c._make_proxy(t)

    create_ddl_1 = "DROP TABLE %s" % (name)
    create_ddl_2 = "CREATE VIEW %s AS %s" % (
        name, selectable)
    drop_ddl_1 = "DROP VIEW %s" % (name)
    drop_ddl_2 = "CREATE TABLE %s(id integer)" % (name)

    DDL(create_ddl_1).execute_at('after-create', t)
    DDL(create_ddl_2).execute_at('after-create', t)
    DDL(drop_ddl_1).execute_at('before-drop', t)
    DDL(drop_ddl_2).execute_at('before-drop', t)

    return t
    

def _sort_tables(tables):
    """sort a collection of Table objects in order of their foreign-key dependency."""
    
    tables = list(tables)
    tuples = []

    def visit_foreign_key(fkey):
        if fkey.use_alter:
            return
        parent_table = fkey.column.table
        if parent_table in tables:
            child_table = fkey.parent.table
            tuples.append( ( parent_table, child_table ) )

    for table in tables:
        visitors.traverse(table, {'schema_visitor':True}, {'foreign_key':visit_foreign_key})    
    my_deps = []
    if tables:
        my_deps = _dependencies.get(str(tables[0].metadata), []) or []
    return topological.sort(tuples + my_deps, tables)


def add_dependency(metadata, child, parent):
    global _sort_tables_bak
    global _dependencies
    if not _sort_tables_bak:
        _dependencies = {}
        _sort_tables_bak = sqlalchemy.sql.util.sort_tables
        sqlalchemy.sql.util.sort_tables = _sort_tables
    meta_key = str(metadata)
    deps_list = _dependencies.get(meta_key, [])
    deps_list.append((parent, child))
    _dependencies[meta_key] = deps_list


def reset_dependencies(metadata):
    global _sort_tables_bak
    global _dependencies
    if str(metadata) in _dependencies:
        del _dependencies[str(metadata)]
    if len(_dependencies.keys())==0:
        if _sort_tables_bak:
            sqlalchemy.sql.util.sort_tables = _sort_tables_bak 
        _sort_tables_bak = None


    
