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
# Statuses
#

class StatusTranslation(SABase):
    '''Map status codes to status names in various languages.

    Table -- StatusCodeTranslation
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, statuscodeid, statusname, language=None,
            description=None):
        '''
        :statuscodeid: id of the status this translation applies to
        :statusname: translated string
        :language: Languages code that this string is for.  if not given.
            defaults to 'C'
        :description: a description of what this status means.  May be used in
            online help
        '''
        # pylint: disable-msg=R0913
        super(StatusTranslation, self).__init__()
        self.statuscodeid = statuscodeid
        self.statusname = statusname
        self.language = language or None
        self.description = description or None

    def __repr__(self):
        return 'StatusTranslation(%s, "%s", language="%s", description="%s")' \
                % (self.statuscodeid, self.statusname, self.language,
                        self.description)

class BaseStatus(SABase):
    '''Fields common to all Statuses.'''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, statuscodeid):
        # pylint: disable-msg=R0913
        super(BaseStatus, self).__init__()
        self.statuscodeid = statuscodeid

class CollectionStatus(BaseStatus):
    '''Subset of status codes that are applicable to collections.

    Table -- CollectionStatusCode
    '''
    # pylint: disable-msg=R0902, R0903
    def __repr__(self):
        return 'CollectionStatus(%s)' % self.statuscodeid

class PackageStatus(BaseStatus):
    '''Subset of status codes that apply to packages.

    Table -- PackageStatusCode
    '''
    # pylint: disable-msg=R0902, R0903
    def __repr__(self):
        return 'PackageStatus(%s)' % self.statuscodeid

class PackageListingStatus(BaseStatus):
    '''Subset of status codes that are applicable to package listings.

    Table -- PackageListingStatusCode
    '''
    # pylint: disable-msg=R0902, R0903
    def __repr__(self):
        return 'PackageListingStatus(%s)' % self.statuscodeid

class PackageAclStatus(BaseStatus):
    ''' Subset of status codes that apply to Person and Group Package Acls.

    Table -- PackageAclStatusCode
    '''
    # pylint: disable-msg=R0902, R0903
    def __repr__(self):
        return 'PackageAclStatus(%s)' % self.statuscodeid

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

#
# Statuses
#

# These are a bit convoluted as we have a 1:1:N relation between
# SpecificStatusTable:StatusCodeTable:StatusTranslationTable

# I'd like to merely override the pylint regex for this particular section of
# code as # these variables are special.  They chould be treated more like
# class definitions than constants.  Oh well.
# pylint: disable-msg=C0103
StatusTranslationTable = Table('statuscodetranslation', metadata, autoload=True)

CollectionStatusTable = Table('collectionstatuscode', metadata, autoload=True)

# Package Listing Status Table.  Like the other status tables, this one has to
# connect translations to the statuses particular to the PackageListing.  This
# make it somewhat more convoluted but all the status tables follow the same
# pattern.
PackageListingStatusTable = Table('packagelistingstatuscode', metadata,
        autoload=True)

# Package Status Table.
PackageStatusTable = Table('packagestatuscode', metadata, autoload=True)

# Package Acl Status Table
PackageAclStatusTable = Table('packageaclstatuscode', metadata, autoload=True)

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

mapper(StatusTranslation, StatusTranslationTable)
mapper(CollectionStatus, CollectionStatusTable, properties = {
    'collections': relation(Collection, backref='status'),
    'collectionPackages': relation(CollectionPackage, backref='status'),
    'translations': relation(StatusTranslation,
        order_by=StatusTranslationTable.c.language,
        primaryjoin=StatusTranslationTable.c.statuscodeid \
                == CollectionStatusTable.c.statuscodeid,
        foreign_keys=[StatusTranslationTable.c.statuscodeid],
        backref=backref('cstatuscode',
            foreign_keys=[CollectionStatusTable.c.statuscodeid],
            primaryjoin=StatusTranslationTable.c.statuscodeid \
                    == CollectionStatusTable.c.statuscodeid),
        )})

mapper(PackageListingStatus, PackageListingStatusTable, properties = {
    'listings' : relation(PackageListing, backref='status'),
    'translations' : relation(StatusTranslation,
        order_by=StatusTranslationTable.c.language,
        primaryjoin=StatusTranslationTable.c.statuscodeid \
                == PackageListingStatusTable.c.statuscodeid,
        foreign_keys=[StatusTranslationTable.c.statuscodeid],
        backref=backref('plstatuscode',
            foreign_keys=[PackageListingStatusTable.c.statuscodeid],
            primaryjoin=StatusTranslationTable.c.statuscodeid \
                    == PackageListingStatusTable.c.statuscodeid)
        )})

mapper(PackageStatus, PackageStatusTable, properties = {
    'packages' : relation(Package, backref='status'),
    'translations' : relation(StatusTranslation,
        order_by=StatusTranslationTable.c.language,
        primaryjoin=StatusTranslationTable.c.statuscodeid \
                == PackageStatusTable.c.statuscodeid,
        foreign_keys=[StatusTranslationTable.c.statuscodeid],
        backref=backref('pstatuscode',
            foreign_keys=[PackageStatusTable.c.statuscodeid],
            primaryjoin=StatusTranslationTable.c.statuscodeid \
                    == PackageStatusTable.c.statuscodeid)
        )})
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

mapper(PackageAclStatus, PackageAclStatusTable,
        properties={'pacls' : relation(PersonPackageListingAcl,
                backref='status'),
            'gacls' : relation(GroupPackageListingAcl, backref='status'),
            'translations' : relation(StatusTranslation,
                order_by=StatusTranslationTable.c.language,
                primaryjoin=StatusTranslationTable.c.statuscodeid \
                        == PackageAclStatusTable.c.statuscodeid,
                foreign_keys=[StatusTranslationTable.c.statuscodeid],
                backref=backref('pastatuscode',
                    foreign_keys=[PackageAclStatusTable.c.statuscodeid],
                    primaryjoin=StatusTranslationTable.c.statuscodeid \
                            == PackageAclStatusTable.c.statuscodeid)
                )})


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
