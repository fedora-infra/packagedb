from datetime import datetime
from turbogears.database import metadata, session, bind_meta_data
from sqlalchemy import *
from turbogears import identity, config
from sqlalchemy.ext.assignmapper import assign_mapper

bind_meta_data()

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
        self.packageid = packagelistingid
        self.acl = acl

class PersonPackageAcl(object):
    def __init__(self, packagelistingid, acl, packageaclid, userid, status):
        self.packageaclid = packageaclid
        self.userid = userid
        self.status = status

class GroupPackageAcl(object):
    def __init__(self, packagelistingid, acl, packageaclid, groupid, status):
        self.packageaclid = packageaclid
        self.groupid = groupid
        self.status = status

CollectionStatusTable = Table('collectionstatuscode', metadata, autoload=True)
assign_mapper(session.context, CollectionStatus, CollectionStatusTable)

StatusTranslationTable = Table('statuscodetranslation', metadata, autoload=True)
assign_mapper(session.context, StatusTranslation, StatusTranslationTable)

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
        polymorphic_identity='c')

assign_mapper(session.context, Branch, BranchTable, inherits=collectionMapper,
        inherit_condition=CollectionTable.c.id==BranchTable.c.collectionid,
        polymorphic_identity='b')

PackageTable = Table('package', metadata, autoload=True)
PackageListingTable = Table('packagelisting', metadata, autoload=True)

assign_mapper(session.context, Package, PackageTable, properties =
        {'listings':relation(PackageListing, backref='package')})
assign_mapper(session.context, PackageListing, PackageListingTable)

PackageAclTable = Table('packageacl', metadata, autoload=True)
PersonPackageAclTable = Table('personpackageacl', metadata, autoload=True)
GroupPackageAclTable = Table('grouppackageacl', metadata, autoload=True)

assign_mapper(session.context, PackageAcl, PackageAclTable,
        properties={'people' : relation(PersonPackageAcl, backref='acl'),
            'groups' : relation(GroupPackageAcl, backref='acl')})
assign_mapper(session.context, PersonPackageAcl, PersonPackageAclTable)
assign_mapper(session.context, GroupPackageAcl, GroupPackageAclTable)

### FIXME: Create sqlalchemy schema.
# By and large we'll follow steps similar to the Collection/Branch example
# above.
# List of tables to map::
# StatusCode
# PackageStatusCode
# PackageLogStatusCode
# PackageBuildStatusCode
# PackageBuildLogStatusCode
# PackageListingStatusCode
# PackageListingLogStatusCode
# PackageACLStatusCode
# PackageACLLogStatusCode
# CollectionSet
# PackageBuild
# PackageBuildListing
# PackageACL
# PersonPackageACL
# GroupPackageACL
# Log
# PackageLog
# PackageListingLog
# PackageBuildLog
# PersonPackageACLLog
# GroupPackageACLLog

