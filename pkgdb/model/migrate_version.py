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
'''
Mapping sqlalchemy-migrate versioning table
'''

from sqlalchemy import Table, Column, ForeignKey, Integer, Text, String
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, text
from turbogears.database import metadata, mapper, get_engine
from turbogears import config
from pkgdb.model import DeclarativeBase
from pkgdb.lib.db import initial_data

from migrate.versioning.api import version


class MigrateVersion(DeclarativeBase):
    __tablename__ = 'migrate_version'
    repository_id = Column(String(255), primary_key=True)
    repository_path = Column(Text)
    version = Column(Integer)

db_repo = config.get('migrate.db_repo')

initial_data(MigrateVersion.__table__,
    ('repository_id', 'repository_path', 'version'),
    ('Fedora Package DB', db_repo, lambda: int(version(db_repo))))



