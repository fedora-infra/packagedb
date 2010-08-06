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
"""
Library with helpers making tests more readable
"""

from sqlalchemy import Table, Column, Integer, String
from sqlalchemy import ForeignKey, MetaData, create_engine

from turbogears import config, update_config
from turbogears.util import get_model
import os
from unittest import TestCase
import atexit

# try to load test.cfg to setup testing database
# in memory sqlite is set by default
if os.path.exists('test.cfg'):
    for w in os.walk('.'):
        if w[0].endswith(os.sep + 'config') and not os.sep + '.' in w[0]:
            modulename = "%s.app" % w[0][2:].replace(os.sep, ".")
            break
    else:
        modulename = None
    update_config(configfile="test.cfg", modulename=modulename)
else:
    database.set_db_uri("sqlite:///:memory:")


class DBTest(TestCase):
    """TestCase using db model of pkgdb

    During init the testcase make sure DB is created.
    For performance reasons the test DB is created only once 
    for whole test suite. Thus each test is responsible for
    cleaning after itself.
    """
    
    def __init__(self, methodName='runTest'):
        super(DBTest, self).__init__(methodName)
        from turbogears.database import set_db_uri, session, metadata
        self.session = session
        self.metadata = metadata
        self.model = get_model()

    def setUp(self):
        self.metadata.create_all()


    def tearDown(self):
        self.metadata.drop_all()


def slow(func):
    """Decorator to mark long-running tests

    nose can filter marked tests 'nose -a \!slow'

    Usualy it is required for the unittests to finish quickly.
    Recommended time limit (in test-driven development approach)
    is one second for whole test suite. So if you write long-running test
    (e.g. cache expiration behaviour test, etc.) mark it with this decorator
    """

    func.slow = True
    return func


def create_stuff_table(metadata):
    """Dummy table 'stuff'
    :arg metadata: metadata
    :returns table: Table instance
    """
    return Table('stuff', metadata, 
        Column('id', Integer, autoincrement=True, primary_key=True),
        Column('data', String(50)),
    )


def create_more_stuff_table(metadata):
    """Dummy table 'more_stuff'
    :arg metadata: metadata
    :returns table: Table instance
    """
    
    return Table('more_stuff', metadata, 
        Column('id', Integer, primary_key=True),
        Column('stuff_id', Integer, ForeignKey('stuff.id')),
        Column('data', String(50)),
    )


def number_of_tables(metadata):
    """Count tables in metadata
    :arg metadata: metadata
    :return int: number of tables
    """
    return len(metadata.tables.keys())


def bound_metadata(echo=False):
    """Create metadata bound to sqlite engine
    :arg echo: set engine to spit out SQL commands
    :return metadata: metadata
    """
    engine = create_engine(config.get('sqlalchemy.dburi'), pool_size=1, echo=echo)
    conn = engine.connect()
    return MetaData(engine)


def unbound_metadata():
    """Create metadata
    :return metadata: metadata
    """
    return MetaData()


def table_names(metadata):
    """List of table names defined in metadata
    :arg metadata: metadata
    :return set: list of table names
    """
    names = [t.name for t in metadata.tables.values()]
    return set(names)

