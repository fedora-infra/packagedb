from datetime import datetime
from turbogears.database import metadata, session, bind_meta_data
from sqlalchemy import *
from turbogears import identity, config
from sqlalchemy.ext.assignmapper import assign_mapper

bind_meta_data()

#
# Python classes
#

#
# StatusCodeTranslation table.  Maps status codes to status names in various
# languages.
#
class StatusTranslation(object):
    def __init__(self, statuscodeid, statusname, language=None,
            description=None):
        self.statuscodeid = statuscodeid
        self.statusname = statusname
        if language:
            self.language
        self.description = description or None

    def __repr__(self):
        return 'StatusTranslation(%s, "%s", "%s")' % (self.statuscodeid,
                self.statusname, self.language)

#
# CollectionStatusCode table.  Subset of status codes that are applicable for
# collections.
#
class CollectionStatus(object):
    def __init__(self, statuscodeid):
        self.statuscodeid = statuscodeid

    def __repr__(self):
        return 'CollectionStatus(%s)' % self.statuscodeid

#
# PackageListingStatusCode table.  Subset of status codes that are applicable
# to package listings.
#
class PackageListingStatus(object):
    def __init__(self, statuscodeid):
        self.statuscodeid = statuscodeid

    def __repr__(self):
        return 'PackageListingStatus(%s)' % self.statuscodeid

#
# PackageAclStatusCode table.  Subset of status codes that apply to
# PersonPackageListingAcl and GroupPackageListingAcls.
#
class PackageAclStatus(object):
    def __init__(self, statuscodeid):
        self.statuscodeid = statuscodeid

    def __repr__(self):
        return 'PackageAclStatus(%s)' % self.statuscodeid

#
# Collection table.  A collection of packages.
#
class Collection(object):
    def __init__(self, name, version, statuscode, owner,
            publishurltemplate=None, pendingurltemplate=None, summary=None,
            description=None):
        self.name = name
        self.version = version
        self.statuscode = statuscode
        self.owner = owner
        self.publishurltemplate = publishurltemplate
        self.pendingurltemplate = pendingurltemplate
        self.summary = summary
        self.description = description

    def __repr__(self):
        return 'Collection("%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s")' % (
                self.name, self.version, self.statuscode, self.owner,
                self.publishurltemplate, selg.pendingurltemplate,
                self.summary, self.description)

#
# Branch table.  A collection of packages which has a physical representation
# in our VCS and download repositories.
#
class Branch(Collection):
    def __init__(self, collectionid, branchname, disttag, parentid, *args):
        self.collectionid = collectionid
        self.branchname = branchname
        self.disttag = disttag
        self.parentid = parentid
        Collection.__init__(self, args)
    
    def __repr__(self):
        return 'Branch(%s, "%s", "%s", "%s", "%s")' % (self.collectionid,
                self.branchname, self.disttag, self.parentid)

#
# Package table.  This is equal to the software in one of our revision control
# directories.  It is unversioned and not associated with a particular
# collection.
#
class Package(object):
    def __init__(self, name, summary, statuscode, description=None,
            reviewurl=None):
        self.name = name
        self.summary = summary
        self.statuscode = statuscode
        self.description = description
        self.reviewurl = reviewurl

    def __repr__(self):
        return 'Package("%s", "%s", "%s", "%s", "%s")' % (self.name,
                self.summary, self.statuscode, self.description, self.reviewurl)

# 
# PackageListing table.  This associates a package with a particular
# collection.
#
class PackageListing(object):
    def __init__(self, packageid, collectionid, owner, statuscode,
            qacontact=None):
        self.packageid = packageid
        self.collectionid = collectionid
        self.owner = owner
        self.qacontact = qacontact
        self.statuscode = statuscode

    def __repr__(self):
        return 'PackageListing(%s, %s, %s, %s, %s)' % (self.packageid,
                self.collectionid, self.owner, self.statuscode, self.qacontact)

#
# PersonPackageListing table.  Each packagelisting has people who can modify
# it.  This table associates acls with a person.
#
class PersonPackageListing(object):
    def __init__(self, userid, packagelistingid):
        self.userid = userid
        self.packagelistingid = packagelistingid

    def __repr__(self):
        return 'PersonPackageListing(%s, %s)' % (self.userid,
                self.packagelistingid)

#
# GroupPackageListing table.  Each packagelisting can have groups which can
# modify it.  This table associates acls with a group.
#
class GroupPackageListing(object):
    def __init__(self, groupid, packagelistingid):
        self.groupid = groupid
        self.packagelistingid = packagelistingid

    def __repr__(self):
        return 'GroupPackageListing(%s, %s)' % (self.groupid,
                self.packagelistingid)

#
# PersonPackageListingAcl table.  This is an actual acl on a package that a
# person owns.
#
class PersonPackageListingAcl(object):
    def __init__(self, acl, statuscode, personpackagelistingid=None):
        self.personpackagelistingid = personpackagelistingid
        self.acl = acl
        self.statuscode = statuscode

    def __repr__(self):
        return 'PersonPackageListingAcl(%s, %s, %s)' % (
                self.personpackagelistingid, self.acl, self.statuscode)

#
# GroupPackageListingAcl table.  This is an acl that a group holds on an acl.
#
class GroupPackageListingAcl(object):
    def __init__(self, grouppackagelistingid, acl, statuscode):
        self.grouppackagelistingid = grouppackagelistingid
        self.acl = acl
        self.statuscode = statuscode

    def __repr__(self):
        return 'GroupPackageListingAcl(%s, %s, %s)' % (
                self.grouppackagelistingid, self.acl, self.statuscode)

# Log
class Log(object):
    def __init__(self, userid, description=None, changetime=None):
        self.userid = userid
        self.description = description
        self.changetime = changetime

    def __repr__(self):
        return 'Log(%s, %s, %s)' % (self.userid, self.description,
                self.changetime)

# PackageListingLog
class PackageListingLog(Log):
    def __init__(self, userid, action, description=None, changetime=None,
            packagelistingid=None):
        Log.__init__(self, userid, description, changetime)
        self.action = action
        self.packagelistingid = packagelistingid

    def __repr__(self):
        return 'PackageListingLog(%s, %s, %s, %s, %s)' % (self.userid,
                self.action, self.description, self.changetime,
                self.packagelistingid)

# Mapping status tables
# These are a bit convoluted as we have a 1:1:N relation between
# SpecificStatusTable:StatusCodeTable:StatusTranslationTable
StatusTranslationTable = Table('statuscodetranslation', metadata, autoload=True)
assign_mapper(session.context, StatusTranslation, StatusTranslationTable)

CollectionStatusTable = Table('collectionstatuscode', metadata, autoload=True)
assign_mapper(session.context, CollectionStatus, CollectionStatusTable,
        properties={'collections' : relation(Collection, backref='status'),
            'translations': relation(StatusTranslation,
                order_by=StatusTranslationTable.c.language,
                primaryjoin=StatusTranslationTable.c.statuscodeid==CollectionStatusTable.c.statuscodeid,
                foreignkey=StatusTranslationTable.c.statuscodeid,
                backref=backref('cstatuscode',
                    foreignkey=CollectionStatusTable.c.statuscodeid,
                    primaryjoin=StatusTranslationTable.c.statuscodeid==CollectionStatusTable.c.statuscodeid),
                )})

# Collections and Branches have an inheritance relationship.  ie: Branches are
# just Collections that have additional data.
CollectionTable = Table('collection', metadata, autoload=True)
BranchTable = Table('branch', metadata, autoload=True)

collectionJoin = polymorphic_union (
        {'b' : select((CollectionTable.join(
            BranchTable, CollectionTable.c.id == BranchTable.c.collectionid),
            column("'b'").label('kind'))),
         'c' : select((CollectionTable, column("'c'").label('kind')),
             not_(CollectionTable.c.id.in_(select(
                 (CollectionTable.c.id,),
                 CollectionTable.c.id == BranchTable.c.collectionid)
             )))
         },
        None
        )

collectionMapper = assign_mapper(session.context, Collection, CollectionTable,
        select_table=collectionJoin, polymorphic_on=collectionJoin.c.kind,
        polymorphic_identity='c',
        properties={'listings': relation(PackageListing, backref='collection')})

assign_mapper(session.context, Branch, BranchTable, inherits=collectionMapper,
        inherit_condition=CollectionTable.c.id==BranchTable.c.collectionid,
        polymorphic_identity='b')

# Package and PackageListing are straightforward translations.  Look at these
# if you're looking for a straightforward example.
PackageTable = Table('package', metadata, autoload=True)
PackageListingTable = Table('packagelisting', metadata, autoload=True)

assign_mapper(session.context, Package, PackageTable, properties =
        {'listings':relation(PackageListing, backref='package')})
assign_mapper(session.context, PackageListing, PackageListingTable,
        properties={'people' : relation(PersonPackageListing, backref='packagelisting'),
            'groups' : relation(GroupPackageListing, backref='packagelisting')})

# Package Listing Status Table.  Like the other status tables, this one has to
# connect translations to the statuses particular to the PackageListing.  This
# make it somewhat more convoluted but all the status tables follow the same
# pattern.
PackageListingStatusTable = Table('packagelistingstatuscode', metadata, autoload=True)
assign_mapper(session.context, PackageListingStatus, PackageListingStatusTable,
        properties={'listings' : relation(PackageListing, backref='status'),
            'translations' : relation(StatusTranslation,
                order_by=StatusTranslationTable.c.language,
                primaryjoin=StatusTranslationTable.c.statuscodeid==PackageListingStatusTable.c.statuscodeid,
                foreignkey=StatusTranslationTable.c.statuscodeid,
                backref=backref('plstatuscode',
                    foreignkey=PackageListingStatusTable.c.statuscodeid,
                    primaryjoin=StatusTranslationTable.c.statuscodeid==PackageListingStatusTable.c.statuscodeid)
                )})

#
# Person and Group ACL information
#
PersonPackageListingTable = Table('personpackagelisting', metadata,
        autoload=True)
GroupPackageListingTable = Table('grouppackagelisting', metadata, autoload=True)
PersonPackageListingAclTable = Table('personpackagelistingacl', metadata,
        autoload=True)
GroupPackageListingAclTable = Table('grouppackagelistingacl', metadata,
        autoload=True)

assign_mapper(session.context, PersonPackageListing, PersonPackageListingTable,
        properties={'acls':relation(PersonPackageListingAcl,
            backref='personpackagelisting')})
assign_mapper(session.context, GroupPackageListing, GroupPackageListingTable,
        properties={'acls':relation(GroupPackageListingAcl,
            backref='grouppackagelisting')})
assign_mapper(session.context, PersonPackageListingAcl,
        PersonPackageListingAclTable)
assign_mapper(session.context, GroupPackageListingAcl,
        GroupPackageListingAclTable)

PackageAclStatusTable = Table('packageaclstatuscode', metadata, autoload=True)
assign_mapper(session.context, PackageAclStatus, PackageAclStatusTable,
        properties={'pacls' : relation(PersonPackageListingAcl,
                backref='status'),
            'gacls' : relation(GroupPackageListingAcl, backref='status'),
            'translations' : relation(StatusTranslation,
                order_by=StatusTranslationTable.c.language,
                primaryjoin=StatusTranslationTable.c.statuscodeid==PackageAclStatusTable.c.statuscodeid,
                foreignkey=StatusTranslationTable.c.statuscodeid,
                backref=backref('pastatuscode',
                    foreignkey=PackageAclStatusTable.c.statuscodeid,
                    primaryjoin=StatusTranslationTable.c.statuscodeid==PackageAclStatusTable.c.statuscodeid)
                )})

# Log tables
# The log tables all inherit from the base log table.

LogTable = Table('log', metadata, autoload=True)
PackageListingLogTable = Table('packagelistinglog', metadata, autoload=True)

logJoin = polymorphic_union (
        {'pkglistlog' : select((LogTable.join(
            PackageListingLogTable,
                LogTable.c.id == PackageListingLogTable.c.logid),
            column("'pkglistlog'").label('kind'))),
         'log' : select((LogTable, column("'log'").label('kind')),
             not_(LogTable.c.id.in_(select(
                 (LogTable.c.id,),
                 LogTable.c.id == PackageListingLogTable.c.logid)
             )))
         },
        None
        )

logMapper = assign_mapper(session.context, Log, LogTable,
        select_table=logJoin, polymorphic_on=logJoin.c.kind,
        polymorphic_identity='log')
        
assign_mapper(session.context, PackageListingLog, PackageListingLogTable,
        inherits=logMapper,
        inherit_condition=LogTable.c.id==PackageListingLogTable.c.logid,
        polymorphic_identity='pkglistlog',
        properties={'listing': relation(PackageListing, backref='logs')})

### FIXME: Create sqlalchemy schema.
# By and large we'll follow steps similar to the Collection/Branch example
# above.
# List of tables not yet maped::
# StatusCode
# CollectionLogStatusCode
# PackageStatusCode
# PackageLogStatusCode
# PackageBuildStatusCode
# PackageBuildLogStatusCode
# PackageListingLogStatusCode
# PackageACLLogStatusCode
# CollectionSet
# PackageBuild
# PackageBuildListing
# Log
# CollectionLog
# PackageLog
# PackageListingLog
# PackageBuildLog
# PersonPackageListingAclLog
# GroupPackageListingACLLog
