# -*- coding: utf-8 -*-
#
# Copyright © 2007-2008  Red Hat, Inc.
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
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#                    Martin Bacovsky <mbacovsk@redhat.com>
#
'''
Mapping of python classes to Database Tables.
'''
# :C0103: Tables and mappers are constants but SQLAlchemy/TurboGears convention
# is not to name them with all uppercase
# pylint: disable-msg=C0103

#from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import DDL
from fedora.tg.json import SABase
from turbogears.database import metadata

# Base class for all of our model classes: By default, the data model is
# defined with SQLAlchemy's declarative extension, but if you need more
# control, you can switch to the traditional method.
DeclarativeBase = declarative_base(cls=SABase, metadata=metadata)

DDL('CREATE PROCEDURAL LANGUAGE plpgsql', on='postgres')\
    .execute_at('before-create', metadata)
DDL('DROP PROCEDURAL LANGUAGE plpgsql CASCADE', on='postgres')\
    .execute_at('after-drop', metadata)


### FIXME:  We've broken up the one model file into several different files
# for each piece of data in the model.  We need to update the code that
# references this to get the classes from the separate files.  Then we can get
# rid of these imports

# :W0401: use wildcard imports until we can deprecate this whole file.
# :W0614: Importing these so that we can use them by importing them from
#  pkgdb.model.
# pylint: disable-msg=W0401,W0614
from pkgdb.model.acls import *
from pkgdb.model.statuses import *
from pkgdb.model.collections import *
#from pkgdb.model.languages import *
from pkgdb.model.logs import *
from pkgdb.model.packages import *
from pkgdb.model.prcof import *
from pkgdb.model.apps import *
from pkgdb.model.yumdb import *
from pkgdb.model.migrate_version import *

