from datetime import datetime
from turbogears.database import metadata, session, bind_meta_data
from sqlalchemy import *
from turbogears import identity, config
from sqlalchemy.ext.assignmapper import assign_mapper

bind_meta_data()

#
# Python classes
#
class StatusTranslation(object):
    def __init__(self, statuscodeid, statusname, language=None,
            description=None):
        self.statuscodeid = statuscodeid
        self.statusname = statusname
        if language:
            self.language
        self.description = description or None

class CollectionStatus(object):
    def __init__(self, statuscodeid):
        self.statuscodeid = statuscodeid

class PackageListingStatus(object):
    def __init__(self, statuscodeid):
        self.statuscodeid = statuscodeid

class PackageAclStatus(object):
    def __init__(self, statuscodeid):
        self.statuscodeid = statuscodeid

class Collection(object):
    def __init__(self, name, version, status, owner, publishurltemplate=None,
            pendingurltemplate=None, summary=None, description=None):
        self.name = name
        self.version = version
        self.status = status
        self.owner = owner
        self.publishurltemplate = publishurltemplate
        self.pendingurltemplate = pendingurltemplate
        self.summary = summary
        self.description = description

class Branch(Collection):
    def __init__(self, collectionid, branchname, disttag, parentid, *args):
        self.collectionid = collectionid
        self.branchname = branchname
        self.disttag = disttag
        self.parentid = parentid
        Collection.__init__(self, args)

class Package(object):
    def __init__(self, name, summary, status, description=None, reviewurl=None):
        self.name = name
        self.summary = summary
        self.status = status
        self.description = description
        self.reviewurl = reviewurl

class PackageListing(object):
    def __init__(self, packageid, collectionid, owner, status, qacontact=None):
        self.packageid = packageid
        self.collectionid = collectionid
        self.owner = owner
        self.qacontact = qacontact
        self.status = status

class PackageAcl(object):
    def __init__(self, packagelistingid, acl):
        self.packagelistingid = packagelistingid
        self.acl = acl

class PersonPackageAcl(object):
    def __init__(self, packageaclid, userid, status):
        self.packageaclid = packageaclid
        self.userid = userid
        self.status = status

class GroupPackageAcl(object):
    def __init__(self, packagelistingid, acl, packageaclid, groupid, status):
        self.packageaclid = packageaclid
        self.groupid = groupid
        self.status = status

# Mapping status tables
# These are a bit convoluted as we have a 1:1:N relation between
# SpecificStatusTable:StatusCodeTable:StatusTranslationTable
StatusTranslationTable = Table('statuscodetranslation', metadata, autoload=True)
assign_mapper(session.context, StatusTranslation, StatusTranslationTable)

CollectionStatusTable = Table('collectionstatuscode', metadata, autoload=True)
assign_mapper(session.context, CollectionStatus, CollectionStatusTable,
        properties={'collections' : relation(Collection, backref='statuscode'),
            'translations': relation(StatusTranslation,
                order_by=StatusTranslationTable.c.language,
                primaryjoin=StatusTranslationTable.c.statuscodeid==CollectionStatusTable.c.statuscodeid,
                foreignkey=StatusTranslationTable.c.statuscodeid,
                backref=backref('cstatuscode',
                    foreignkey=CollectionStatusTable.c.statuscodeid,
                    primaryjoin=StatusTranslationTable.c.statuscodeid==CollectionStatusTable.c.statuscodeid),
                )})

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

PackageTable = Table('package', metadata, autoload=True)
PackageListingTable = Table('packagelisting', metadata, autoload=True)

assign_mapper(session.context, Package, PackageTable, properties =
        {'listings':relation(PackageListing, backref='package')})
assign_mapper(session.context, PackageListing, PackageListingTable,
        properties={'acls' : relation(PackageAcl, backref='packagelisting')})

PackageListingStatusTable = Table('packagelistingstatuscode', metadata, autoload=True)
assign_mapper(session.context, PackageListingStatus, PackageListingStatusTable,
        properties={'listings' : relation(PackageListing, backref='statuscode'),
            'translations' : relation(StatusTranslation,
                order_by=StatusTranslationTable.c.language,
                primaryjoin=StatusTranslationTable.c.statuscodeid==PackageListingStatusTable.c.statuscodeid,
                foreignkey=StatusTranslationTable.c.statuscodeid,
                backref=backref('plstatuscode',
                    foreignkey=PackageListingStatusTable.c.statuscodeid,
                    primaryjoin=StatusTranslationTable.c.statuscodeid==PackageListingStatusTable.c.statuscodeid)
                )})

PackageAclTable = Table('packageacl', metadata, autoload=True)
PersonPackageAclTable = Table('personpackageacl', metadata, autoload=True)
GroupPackageAclTable = Table('grouppackageacl', metadata, autoload=True)

assign_mapper(session.context, PackageAcl, PackageAclTable,
        properties={'people' : relation(PersonPackageAcl, backref='acl'),
            'groups' : relation(GroupPackageAcl, backref='acl')})
assign_mapper(session.context, PersonPackageAcl, PersonPackageAclTable)
assign_mapper(session.context, GroupPackageAcl, GroupPackageAclTable)

PackageAclStatusTable = Table('packageaclstatuscode', metadata, autoload=True)
assign_mapper(session.context, PackageAclStatus, PackageAclStatusTable,
        properties={'pacls' : relation(PersonPackageAcl, backref='statuscode'),
            'gacls' : relation(GroupPackageAcl, backref='statuscode'),
            'translations' : relation(StatusTranslation,
                order_by=StatusTranslationTable.c.language,
                primaryjoin=StatusTranslationTable.c.statuscodeid==PackageAclStatusTable.c.statuscodeid,
                foreignkey=StatusTranslationTable.c.statuscodeid,
                backref=backref('pastatuscode',
                    foreignkey=PackageAclStatusTable.c.statuscodeid,
                    primaryjoin=StatusTranslationTable.c.statuscodeid==PackageAclStatusTable.c.statuscodeid)
                )})

### FIXME: Create sqlalchemy schema.
# By and large we'll follow steps similar to the Collection/Branch example
# above.
# List of tables to map::
# StatusCode
# PackageStatusCode
# PackageLogStatusCode
# PackageBuildStatusCode
# PackageBuildLogStatusCode
# PackageListingLogStatusCode
# PackageACLStatusCode
# PackageACLLogStatusCode
# CollectionSet
# PackageBuild
# PackageBuildListing
# Log
# PackageLog
# PackageListingLog
# PackageBuildLog
# PersonPackageACLLog
# GroupPackageACLLog

