# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011  Red Hat, Inc.
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
#
'''
Mapping of database tables for logs to python classes.
'''

from sqlalchemy import Table, Column, Integer, Text, DateTime
from sqlalchemy import select, literal_column, not_
from sqlalchemy import ForeignKeyConstraint, func, DDL, Index
from sqlalchemy.orm import polymorphic_union, relation
from turbogears.database import metadata, mapper, get_engine

from fedora.tg.json import SABase

from pkgdb.model.packages import Package, PackageListing
from pkgdb.model.acls import PersonPackageListingAcl, GroupPackageListingAcl

from pkgdb.model import SC_ACTIVE, SC_ADDED, SC_APPROVED, SC_AWAITING_BRANCH  # 1-4
from pkgdb.model import SC_AWAITING_DEVELOPMENT, SC_AWAITING_QA, SC_AWAITING_PUBLISH, SC_AWAITING_REVIEW # 5-8
from pkgdb.model import SC_EOL, SC_DENIED, SC_MAINTENENCE, SC_MODIFIED # 9-12
from pkgdb.model import SC_OBSOLETE, SC_ORPHANED, SC_OWNED, SC_REJECTED # 13-16
from pkgdb.model import SC_REMOVED, SC_UNDER_DEVELOPMENT, SC_UNDER_REVIEW, SC_RETIRED # 17-20

from pkgdb.lib.db import Grant_RW, initial_data

get_engine()

#
# Mapped Classes
#

class Log(SABase):
    '''Base Log record.

    This is a Log record.  All logs will be entered via a subclass of this.

    Table -- Log
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, username, description=None, changetime=None):
        # pylint: disable-msg=R0913
        super(Log, self).__init__()
        self.username = username
        self.description = description
        self.changetime = changetime

    def __repr__(self):
        return 'Log(%r, description=%r, changetime=%r)' % (self.username,
                self.description, self.changetime)

class PackageLog(Log):
    '''Log of changes to Packages.

    Table -- PackageLog
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, username, action, description=None, changetime=None,
            packageid=None):
        # pylint: disable-msg=R0913
        super(PackageLog, self).__init__(username, description, changetime)
        self.action = action
        self.packageid = packageid

    def __repr__(self):
        return 'PackageLog(%r, %r, description=%r, changetime=%r,' \
                ' packageid=%r)' % (self.username, self.action,
                        self.description, self.changetime, self.packageid)

class PackageListingLog(Log):
    '''Log of changes to the PackageListings.

    Table -- PackageListingLog
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, username, action, description=None, changetime=None,
            packagelistingid=None):
        # pylint: disable-msg=R0913
        super(PackageListingLog, self).__init__(username, description,
                changetime)
        self.action = action
        self.packagelistingid = packagelistingid

    def __repr__(self):
        return 'PackageListingLog(%r, %r, description=%r, changetime=%r,' \
                ' packagelistingid=%r)' % (self.username,
                self.action, self.description, self.changetime,
                self.packagelistingid)

class PersonPackageListingAclLog(Log):
    '''Log changes to an Acl that a person owns.

    Table -- PersonPackageListingAcl
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, username, action, description=None, changetime=None,
            personpackagelistingaclid=None):
        # pylint: disable-msg=R0913
        super(PersonPackageListingAclLog, self).__init__(username, description,
                changetime)
        self.action = action
        self.personpackagelistingaclid = personpackagelistingaclid

    def __repr__(self):
        return 'PersonPackageListingAclLog(%r, %r, description=%r,' \
                ' changetime=%r, personpackagelistingaclid=%r)' % (
                        self.username, self.action, self.description,
                        self.changetime, self.personpackagelistingaclid)

class GroupPackageListingAclLog(Log):
    '''Log changes to an Acl that a group owns.

    Table -- GroupPackageListingAclLog
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, username, action, description=None, changetime=None,
            grouppackagelistingaclid=None):
        # pylint: disable-msg=R0913
        super(GroupPackageListingAclLog, self).__init__(username, description,
                changetime)
        self.action = action
        self.grouppackagelistingaclid = grouppackagelistingaclid

    def __repr__(self):
        return 'GroupPackageListingAclLog(%r, %r, description=%r,' \
                ' changetime=%r, grouppackagelistingaclid=%r)' % (
                        self.username, self.action, self.description,
                        self.changetime, self.grouppackagelistingaclid)

#
# Mapped Tables
#

# The log tables all inherit from the base log table.

# :C0103: Tables and mappers are constants but SQLAlchemy/TurboGears convention
# is not to name them with all uppercase
# pylint: disable-msg=C0103

# Log a change to the packageDB.
#
# Fields:
# :id: Primary key
# :userId: Who made the change.
# :changeTime: Time that the change occurred.
# :description: Additional information about the change.
LogTable = Table('log', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('username', Text(),  nullable=False),
    Column('changetime', DateTime(timezone=False), 
        server_default=func.now(), nullable=False),
    Column('description', Text()),
)
Index('log_changetime_idx', LogTable.c.changetime)
DDL('ALTER TABLE log CLUSTER ON log_changetime_idx', on='postgres')\
    .execute_at('after-create', LogTable)
Grant_RW(LogTable)



PackageLogStatusCodeTable = Table('packagelogstatuscode', metadata,
    Column('statuscodeid', Integer(), autoincrement=False, primary_key=True, nullable=False),
)
initial_data(PackageLogStatusCodeTable,
    ['statuscodeid'],
    [SC_ADDED], [SC_APPROVED], [SC_AWAITING_REVIEW], [SC_DENIED], 
    [SC_MODIFIED], [SC_REMOVED], [SC_UNDER_REVIEW])
Grant_RW(PackageLogStatusCodeTable)


# Log a change made to the Package table.
#
# Fields:
# :logId: The id of the log entry.
# :packageId: The package that changed.
# :action: What happened to the package.
PackageLogTable = Table('packagelog', metadata,
    Column('logid', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('packageid', Integer(), nullable=False),
    Column('action', Integer(), nullable=False),
    ForeignKeyConstraint(['action'],['packagelogstatuscode.statuscodeid'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
    ForeignKeyConstraint(['logid'],['log.id'], 
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['packageid'],['package.id'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
)
Index('packagelog_packageid_idx', PackageLogTable.c.packageid)
DDL('ALTER TABLE packagelog CLUSTER ON packagelog_packageid_idx', on='postgres')\
    .execute_at('after-create', PackageLogTable)
Grant_RW(PackageLogTable)


CollectionLogStatusCodeTable = Table('collectionlogstatuscode', metadata,
    Column('statuscodeid', Integer(),  primary_key=True, autoincrement=False, nullable=False),
)
initial_data(CollectionLogStatusCodeTable,
    ['statuscodeid'],
    [SC_ACTIVE], [SC_ADDED], [SC_EOL], [SC_REJECTED], 
    [SC_REMOVED], [SC_UNDER_DEVELOPMENT])
Grant_RW(CollectionLogStatusCodeTable)


# Log a change made to the Collection table.
#
# Fields:
# :logId: The id of the log entry.
# :collectionId: The collection that changed.
# :action: What happened to the collection.
CollectionLogTable = Table('collectionlog', metadata,
    Column('logid', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('collectionid', Integer(), nullable=False),
    Column('action', Integer(),  nullable=False),
    ForeignKeyConstraint(['action'],['collectionlogstatuscode.statuscodeid'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
    ForeignKeyConstraint(['logid'],['log.id'], 
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['collectionid'],['collection.id'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
)
Index('collectionlog_collectionid_idx', CollectionLogTable.c.collectionid)
DDL('ALTER TABLE collectionlog CLUSTER ON collectionlog_collectionid_idx', on='postgres')\
    .execute_at('after-create', CollectionLogTable)
Grant_RW(CollectionLogTable)


PackageBuildLogStatusCodeTable = Table('packagebuildlogstatuscode', metadata,
    Column('statuscodeid', Integer(),  primary_key=True, autoincrement=False, nullable=False),
)
initial_data(PackageBuildLogStatusCodeTable,
    ['statuscodeid'],
    [SC_ADDED], [SC_APPROVED], [SC_AWAITING_DEVELOPMENT], [SC_AWAITING_QA],
    [SC_AWAITING_PUBLISH], [SC_AWAITING_REVIEW], [SC_DENIED], [SC_OBSOLETE])
Grant_RW(PackageBuildLogStatusCodeTable)


# Log changes to built packages.
#
# Fields:
# :logId: The id of the log entry.
# :packageBuildId: The `PackageBuild` that changed.
# :action: What happened to the `PackageBuild`.
PackageBuildLogTable = Table('packagebuildlog', metadata,
    Column('logid', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('packagebuildid', Integer(),  nullable=False),
    Column('action', Integer(),  nullable=False),
    ForeignKeyConstraint(['action'],['packagebuildlogstatuscode.statuscodeid'], 
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['logid'],['log.id'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
    ForeignKeyConstraint(['packagebuildid'],['packagebuild.id'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
)
Grant_RW(PackageBuildLogTable)


# Log changes to packages in collections.
#
# Fields:
# :logId: The id of the log entry.
# :packageListingId: The packageListing that changed.
# :action: What happened to the package in the collection.
PackageListingLogTable = Table('packagelistinglog', metadata,
    Column('logid', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('packagelistingid', Integer(),  nullable=False),
    Column('action', Integer(),  nullable=False),
    ForeignKeyConstraint(['action'],['packagelistinglogstatuscode.statuscodeid'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
    ForeignKeyConstraint(['logid'],['log.id'], 
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['packagelistingid'],['packagelisting.id'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
)
Index('packagelistinglog_packagelistingid_idx', PackageListingLogTable.c.packagelistingid)
DDL('ALTER TABLE packagelistinglog CLUSTER ON packagelistinglog_packagelistingid_idx', on='postgres')\
    .execute_at('after-create', PackageListingLogTable)
Grant_RW(PackageListingLogTable)


PackageAclLogStatusCodeTable = Table('packageacllogstatuscode', metadata,
    Column('statuscodeid', Integer(), autoincrement=False, primary_key=True, nullable=False),
)
initial_data(PackageAclLogStatusCodeTable,
    ['statuscodeid'],
    [SC_ADDED], [SC_APPROVED], [SC_AWAITING_REVIEW], [SC_DENIED], [SC_OBSOLETE])
Grant_RW(PackageAclLogStatusCodeTable)


PackageListingLogStatusCodeTable = Table('packagelistinglogstatuscode', metadata,
    Column('statuscodeid', Integer(),  primary_key=True, autoincrement=False, nullable=False),
)
initial_data(PackageListingLogStatusCodeTable,
    ['statuscodeid'],
    [SC_ADDED], [SC_APPROVED], [SC_AWAITING_BRANCH], [SC_AWAITING_REVIEW],
    [SC_DENIED], [SC_OBSOLETE], [SC_ORPHANED], [SC_OWNED], [SC_REMOVED], [SC_RETIRED])
Grant_RW(PackageListingLogStatusCodeTable)


# Log changes to the acls someone holds on a package.
#
# Fields:
# :logId: The id of the log entry.
# :personPackageListingAclId: The Person-PackageListing ACL that's changed.
# :action: What happened to the ACLs for the package.
PersonPackageListingAclLogTable = Table('personpackagelistingacllog', metadata,
    Column('logid', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('personpackagelistingaclid', Integer(), nullable=False),
    Column('action', Integer(),  nullable=False),
    ForeignKeyConstraint(['action'],['packageacllogstatuscode.statuscodeid'], 
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['logid'],['log.id'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
    ForeignKeyConstraint(['personpackagelistingaclid'],['personpackagelistingacl.id'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
)
Index('personpackagelistingacllog_personpackagelistingaclid_idx', PersonPackageListingAclLogTable.c.personpackagelistingaclid)
DDL('ALTER TABLE personpackagelistingacllog CLUSTER ON personpackagelistingacllog_personpackagelistingaclid_idx', on='postgres')\
    .execute_at('after-create', PersonPackageListingAclLogTable)
Grant_RW(PersonPackageListingAclLogTable)


# Log changes to the acls a group holds on the package.
#
# Fields:
# :logId: The id of the log entry.
# :groupPackageListingAclId: The group-package acl that's changed.
# :action: What happened to the ACLs for the package.
GroupPackageListingAclLogTable = Table('grouppackagelistingacllog', metadata,
    Column('logid', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('grouppackagelistingaclid', Integer(), nullable=False),
    Column('action', Integer(),  nullable=False),
    ForeignKeyConstraint(['action'],['packageacllogstatuscode.statuscodeid'], 
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['logid'],['log.id'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
    ForeignKeyConstraint(['grouppackagelistingaclid'],['grouppackagelistingacl.id'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
)
Index('grouppackagelistingacllog_grouppackagelistingaclid_idx', GroupPackageListingAclLogTable.c.grouppackagelistingaclid)
DDL('ALTER TABLE grouppackagelistingacllog CLUSTER ON grouppackagelistingacllog_grouppackagelistingaclid_idx', on='postgres')\
    .execute_at('after-create', GroupPackageListingAclLogTable)
Grant_RW(GroupPackageListingAclLogTable)


logJoin = polymorphic_union (
        {'pkglog': select((LogTable.join(
            PackageLogTable,
                LogTable.c.id == PackageLogTable.c.logid),
            literal_column("'pkglog'").label('kind'))),
         'pkglistlog': select((LogTable.join(
            PackageListingLogTable,
                LogTable.c.id == PackageListingLogTable.c.logid),
            literal_column("'pkglistlog'").label('kind'))),
         'personpkglistacllog': select((LogTable.join(
            PersonPackageListingAclLogTable,
                LogTable.c.id == PersonPackageListingAclLogTable.c.logid),
            literal_column("'personpkglistacllog'").label('kind'))),
         'grouppkglistacllog': select((LogTable.join(
            GroupPackageListingAclLogTable,
                LogTable.c.id == GroupPackageListingAclLogTable.c.logid),
            literal_column("'grouppkglistacllog'").label('kind'))),
         'log': select((LogTable, literal_column("'log'").label('kind')),
             not_(LogTable.c.id.in_(select(
                 (LogTable.c.id,),
                 LogTable.c.id == PackageListingLogTable.c.logid)
             )))
         },
        None
        )

#
# Mappers
#

logMapper = mapper(Log, LogTable, with_polymorphic=("*", logJoin),
        polymorphic_on=logJoin.c.kind, polymorphic_identity='log'
        )


mapper(PersonPackageListingAclLog, PersonPackageListingAclLogTable,
        inherits=logMapper, polymorphic_identity='personpkglistacllog',
        inherit_condition=LogTable.c.id == \
                PersonPackageListingAclLogTable.c.logid,
        properties={
            'acl': relation(PersonPackageListingAcl, backref='logs')
            })

mapper(GroupPackageListingAclLog, GroupPackageListingAclLogTable,
        inherits=logMapper, polymorphic_identity='grouppkglistacllog',
        inherit_condition=LogTable.c.id == \
                GroupPackageListingAclLogTable.c.logid,
        properties={
            'acl': relation(GroupPackageListingAcl, backref='logs')
            })

mapper(PackageLog, PackageLogTable,
        inherits=logMapper, polymorphic_identity='pkglog',
        inherit_condition=LogTable.c.id == PackageLogTable.c.logid,
        properties={
            'package': relation(Package, backref='logs')
            })

mapper(PackageListingLog, PackageListingLogTable,
        inherits=logMapper, polymorphic_identity='pkglistlog',
        inherit_condition=LogTable.c.id == PackageListingLogTable.c.logid,
        properties={
            'listing': relation(PackageListing, backref='logs')
            })
