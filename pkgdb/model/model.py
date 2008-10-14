# -*- coding: utf-8 -*-
#
# Copyright © 2007-2008  Red Hat, Inc. All rights reserved.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.  You should have
# received a copy of the GNU General Public License along with this program;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
# incorporated in the source code or documentation are not subject to the GNU
# General Public License and may only be used or replicated with the express
# permission of Red Hat, Inc.
#
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Mapping of python classes to Database Tables.
'''

from sqlalchemy import Table, Column, ForeignKey, Integer
from sqlalchemy import select, literal_column, not_
from sqlalchemy.orm import polymorphic_union, relation, backref
from turbogears.database import metadata, mapper, get_engine

from fedora.tg.json import SABase

from packages import Package, PackageListing
from collections import CollectionPackage, Collection
from acls import PersonPackageListingAcl, GroupPackageListingAcl

get_engine()

#
# Mapped Classes
#

#
# Logs
#

class Log(SABase):
    '''Base Log record.

    This is a Log record.  All logs will be entered via a subclass of this.

    Table -- Log
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, userid, description=None, changetime=None):
        # pylint: disable-msg=R0913
        super(Log, self).__init__()
        self.userid = userid
        self.description = description
        self.changetime = changetime

    def __repr__(self):
        return 'Log(%s, description="%s", changetime="%s")' % (self.userid,
                self.description, self.changetime)

class PackageLog(Log):
    '''Log of changes to Packages.

    Table -- PackageLog
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, userid, action, description=None, changetime=None,
            packageid=None):
        # pylint: disable-msg=R0913
        super(PackageLog, self).__init__(userid, description, changetime)
        self.action = action
        self.packageid = packageid

    def __repr__(self):
        return 'PackageLog(%s, %s, description="%s", changetime="%s",' \
                ' packageid=%s)' % (self.userid, self.action,
                        self.description, self.changetime, self.packageid)

class PackageListingLog(Log):
    '''Log of changes to the PackageListings.

    Table -- PackageListingLog
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, userid, action, description=None, changetime=None,
            packagelistingid=None):
        # pylint: disable-msg=R0913
        super(PackageListingLog, self).__init__(userid, description, changetime)
        self.action = action
        self.packagelistingid = packagelistingid

    def __repr__(self):
        return 'PackageListingLog(%s, %s, description="%s", changetime="%s",' \
                ' packagelistingid=%s)' % (self.userid,
                self.action, self.description, self.changetime,
                self.packagelistingid)

class PersonPackageListingAclLog(Log):
    '''Log changes to an Acl that a person owns.

    Table -- PersonPackageListingAcl
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, userid, action, description=None, changetime=None,
            personpackagelistingaclid=None):
        # pylint: disable-msg=R0913
        super(PersonPackageListingAclLog, self).__init__(userid, description,
                changetime)
        self.action = action
        self.personpackagelistingaclid = personpackagelistingaclid

    def __repr__(self):
        return 'PersonPackageListingAclLog(%s, %s, description="%s",' \
                ' changetime="%s", personpackagelistingaclid= %s)' % (
                        self.userid, self.action, self.description,
                        self.changetime, self.personpackagelistingaclid)

class GroupPackageListingAclLog(Log):
    '''Log changes to an Acl that a group owns.

    Table -- GroupPackageListingAclLog
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, userid, action, description=None, changetime=None,
            grouppackagelistingaclid=None):
        # pylint: disable-msg=R0913
        super(GroupPackageListingAclLog, self).__init__(userid, description,
                changetime)
        self.action = action
        self.grouppackagelistingaclid = grouppackagelistingaclid

    def __repr__(self):
        return 'GroupPackageListingAclLog(%s, %s, description="%s",' \
                ' changetime="%s", grouppackagelistingaclid= %s)' % (
                        self.userid, self.action, self.description,
                        self.changetime, self.grouppackagelistingaclid)

#
# Mapped Tables
#

# Log tables
# The log tables all inherit from the base log table.

LogTable = Table('log', metadata, autoload=True)
PackageLogTable = Table('packagelog', metadata, autoload=True)
PackageListingLogTable = Table('packagelistinglog', metadata, autoload=True)
PersonPackageListingAclLogTable = Table('personpackagelistingacllog', metadata,
        autoload=True)
GroupPackageListingAclLogTable = Table('grouppackagelistingacllog', metadata,
        autoload=True)

logJoin = polymorphic_union (
        {'pkglog' : select((LogTable.join(
            PackageLogTable,
                LogTable.c.id == PackageLogTable.c.logid),
            literal_column("'pkglog'").label('kind'))),
         'pkglistlog' : select((LogTable.join(
            PackageListingLogTable,
                LogTable.c.id == PackageListingLogTable.c.logid),
            literal_column("'pkglistlog'").label('kind'))),
         'personpkglistacllog' : select((LogTable.join(
            PersonPackageListingAclLogTable,
                LogTable.c.id == PersonPackageListingAclLogTable.c.logid),
            literal_column("'personpkglistacllog'").label('kind'))),
         'grouppkglistacllog' : select((LogTable.join(
            GroupPackageListingAclLogTable,
                LogTable.c.id == GroupPackageListingAclLogTable.c.logid),
            literal_column("'grouppkglistacllog'").label('kind'))),
         'log' : select((LogTable, literal_column("'log'").label('kind')),
             not_(LogTable.c.id.in_(select(
                 (LogTable.c.id,),
                 LogTable.c.id == PackageListingLogTable.c.logid)
             )))
         },
        None
        )

#
# Mappers between Tables and Classes
#
logMapper = mapper(Log, LogTable, select_table=logJoin,
        polymorphic_on=logJoin.c.kind, polymorphic_identity='log')
mapper(PersonPackageListingAclLog, PersonPackageListingAclLogTable,
        inherits=logMapper,
        inherit_condition = LogTable.c.id == \
                PersonPackageListingAclLogTable.c.logid,
        polymorphic_identity='personpkglistacllog',
        properties={'acl': relation(PersonPackageListingAcl, backref='logs')})
mapper(GroupPackageListingAclLog, GroupPackageListingAclLogTable,
        inherits=logMapper,
        inherit_condition=LogTable.c.id==GroupPackageListingAclLogTable.c.logid,
        polymorphic_identity='grouppkglistacllog',
        properties={'acl': relation(GroupPackageListingAcl, backref='logs')})
mapper(PackageLog, PackageLogTable,
        inherits=logMapper,
        inherit_condition=LogTable.c.id==PackageLogTable.c.logid,
        polymorphic_identity='pkglog',
        properties={'package': relation(Package, backref='logs')})
mapper(PackageListingLog, PackageListingLogTable,
        inherits=logMapper,
        inherit_condition=LogTable.c.id==PackageListingLogTable.c.logid,
        polymorphic_identity='pkglistlog',
        properties={'listing': relation(PackageListing, backref='logs')})


### FIXME: Create sqlalchemy schema.
# By and large we'll follow steps similar to the Collection/Branch example
# above.
# List of tables not yet mapped::
# StatusCode
# CollectionLogStatusCode
# PackageLogStatusCode
# PackageBuildStatusCode
# PackageBuildLogStatusCode
# PackageListingLogStatusCode
# PackageACLLogStatusCode
# CollectionSet
# PackageBuild
# PackageBuildListing
# CollectionLog
# PackageBuildLog
