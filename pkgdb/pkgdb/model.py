from datetime import datetime
from turbogears.database import metadata, session, bind_meta_data
from sqlalchemy import *
from turbogears import identity, config
from sqlalchemy.ext.assignmapper import assign_mapper

bind_meta_data()

#
# Python classes
#

class SABase(object):
    def __json__(self):
        props = {}
        for key in self.mapper.props.keys():
            if isinstance(self.mapper.props[key],
                    orm.properties.PropertyLoader) and not (
                            self.mapper.props[key].is_backref):
                continue
            props[key] = getattr(self, key)
        return props

class StatusTranslation(SABase):
    '''Map status codes to status names in various languages.
    
    Table -- StatusCodeTranslation
    '''
    def __init__(self, statuscodeid, statusname, language=None,
            description=None):
        self.statuscodeid = statuscodeid
        self.statusname = statusname
        self.language = language or None
        self.description = description or None

    def __json__(self):
        '''Translations want to traverse the opposite way as other classes.
        
        We link to the translations from the status.  Don't create the reverse.
        '''
        return {'statuscodeid': self.statuscodeid,
                'statusname': self.statusname,
                'language': self.language,
                'description': self.description}

    def __repr__(self):
        return 'StatusTranslation(%s, "%s", language="%s", description="%s")' \
                % (self.statuscodeid, self.statusname, self.language,
                        self.description)

class BaseStatus(SABase):
    def __init__(self, statuscodeid):
        self.statuscodeid = statuscodeid

    def __json__(self):
        return {'statuscodeid': self.statuscodeid,
                'translations': self.translations
                }

class CollectionStatus(BaseStatus):
    '''Subset of status codes that are applicable to collections.

    Table -- CollectionStatusCode
    '''
    def __repr__(self):
        return 'CollectionStatus(%s)' % self.statuscodeid

class PackageStatus(BaseStatus):
    '''Subset of status codes that apply to packages.

    Table -- PackageStatusCode
    '''
    def __repr__(self):
        return 'PackageStatus(%s)' % self.statuscodeid

class PackageListingStatus(BaseStatus):
    '''Subset of status codes that are applicable to package listings.

    Table -- PackageListingStatusCode
    '''
    def __repr__(self):
        return 'PackageListingStatus(%s)' % self.statuscodeid

class PackageAclStatus(BaseStatus):
    ''' Subset of status codes that apply to Person and Group Package Acls.

    Table -- PackageAclStatusCode
    '''
    def __repr__(self):
        return 'PackageAclStatus(%s)' % self.statuscodeid

class Collection(SABase):
    '''A Collection of packages.

    Table -- Collection
    '''
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
        return 'Collection("%s", "%s", "%s", "%s", publishurltemplate="%s",' \
                ' pendingurltemplate="%s", summary="%s", description="%s")' % (
                self.name, self.version, self.statuscode, self.owner,
                self.publishurltemplate, self.pendingurltemplate,
                self.summary, self.description)

class Branch(Collection):
    '''Collection that has a physical existence.

    Some Collections are only present as a name and collection of packages.  The
    Collections that have a branch record are also present in our VCS and
    download repositories.

    Table -- Branch
    '''
    def __init__(self, collectionid, branchname, disttag, parentid, *args):
        self.collectionid = collectionid
        self.branchname = branchname
        self.disttag = disttag
        self.parentid = parentid
        Collection.__init__(self, args)
    
    def __repr__(self):
        return 'Branch(%s, "%s", "%s", %s, "%s", "%s", "%s", "%s",' \
                ' publishurltemplate="%s", pendingurltemplate="%s",' \
                ' summary="%s", description="%s")' % (self.collectionid,
                self.branchname, self.disttag, self.parentid,
                self.name, self.version, self.statuscode, self.owner,
                self.publishurltemplate, self.pendingurltemplate,
                self.summary, self.description)

class Package(SABase):
    '''Software we are packaging.

    This is equal to the software in one of our revision control directories.
    It is unversioned and not associated with a particular collection.

    Table -- Package
    '''
    def __init__(self, name, summary, statuscode, description=None,
            reviewurl=None):
        self.name = name
        self.summary = summary
        self.statuscode = statuscode
        self.description = description
        self.reviewurl = reviewurl

    def __repr__(self):
        return 'Package("%s", "%s", %s, description="%s", reviewurl="%s")' % (
                self.name, self.summary, self.statuscode, self.description,
                self.reviewurl)

class PackageListing(SABase):
    '''This associates a package with a particular collection.

    Table -- PackageListing
    '''
    def __init__(self, owner, statuscode, packageid=None, collectionid=None,
            qacontact=None):
        self.packageid = packageid
        self.collectionid = collectionid
        self.owner = owner
        self.qacontact = qacontact
        self.statuscode = statuscode

    def __repr__(self):
        return 'PackageListing(%s, %s, %s, %s, qacontact="%s")' % (
                self.packageid, self.collectionid, self.owner,
                self.statuscode, self.qacontact)

class PersonPackageListing(SABase):
    '''Associate a person with a PackageListing.

    People who are watching or can modify a packagelisting.

    Table -- PersonPackageListing
    '''
    def __init__(self, userid, packagelistingid):
        self.userid = userid
        self.packagelistingid = packagelistingid

    def __repr__(self):
        return 'PersonPackageListing(%s, %s)' % (self.userid,
                self.packagelistingid)

class GroupPackageListing(SABase):
    '''Associate a group with a PackageListing.

    Table -- GroupPackageListing
    '''
    def __init__(self, groupid, packagelistingid):
        self.groupid = groupid
        self.packagelistingid = packagelistingid

    def __repr__(self):
        return 'GroupPackageListing(%s, %s)' % (self.groupid,
                self.packagelistingid)

class PersonPackageListingAcl(SABase):
    '''Acl on a package that a person owns.

    Table -- PersonPackageListingAcl
    '''
    def __init__(self, acl, statuscode, personpackagelistingid=None):
        self.personpackagelistingid = personpackagelistingid
        self.acl = acl
        self.statuscode = statuscode

    def __repr__(self):
        return 'PersonPackageListingAcl("%s", %s, personpackagelistingid=%s)' \
                % (self.acl, self.statuscode, self.personpackagelistingid)

class GroupPackageListingAcl(SABase):
    '''Acl on a package that a group owns.

    Table -- GroupPackageListingAcl
    '''
    def __init__(self, acl, statuscode, grouppackagelistingid=None):
        self.grouppackagelistingid = grouppackagelistingid
        self.acl = acl
        self.statuscode = statuscode

    def __repr__(self):
        return 'GroupPackageListingAcl("%s", %s, grouppackagelistingid=%s)' % (
                self.acl, self.statuscode, self.grouppackagelistingid)

class Log(SABase):
    '''Base Log record.

    This is a Log record.  All logs will be entered via a subclass of this.

    Table -- Log
    '''
    def __init__(self, userid, description=None, changetime=None):
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
    def __init__(self, userid, action, description=None, changetime=None,
            packageid=None):
        Log.__init__(self, userid, description, changetime)
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
    def __init__(self, userid, action, description=None, changetime=None,
            packagelistingid=None):
        Log.__init__(self, userid, description, changetime)
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
    def __init__(self, userid, action, description=None, changetime=None,
            personpackagelistingaclid=None):
        Log.__init__(self, userid, description, changetime)
        self.action = action
        self.personpackagelistingaclid = personpackagelistingaclid

    def __repr__(self):
        return 'PersonPackageListingAclLog(%s, %s, description="%s",' \
                ' changetime="%s", personpackagelistingaclid= %s)' % (
                        self.userid, self.action, self.description,
                        self.changetime, self.personpackagelistingaclid)

class GroupPackageListingAclLog(Log):
    '''Log changes to an Acl that a group owns.

    Table -- GroupPackageListingAcl
    '''
    def __init__(self, userid, action, description=None, changetime=None,
            grouppackagelistingaclid=None):
        Log.__init__(self, userid, description, changetime)
        self.action = action
        self.grouppackagelistingaclid = grouppackagelistingaclid

    def __repr__(self):
        return 'GroupPackageListingAclLog(%s, %s, description="%s",' \
                ' changetime="%s", grouppackagelistingaclid= %s)' % (
                        self.userid, self.action, self.description,
                        self.changetime, self.grouppackagelistingaclid)

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
            literal_column("'b'").label('kind'))),
         'c' : select((CollectionTable, literal_column("'c'").label('kind')),
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

# Package Status Table.
PackageStatusTable = Table('packagestatuscode', metadata, autoload=True)
assign_mapper(session.context, PackageStatus, PackageStatusTable,
        properties={'packages' : relation(Package, backref='status'),
            'translations' : relation(StatusTranslation,
                order_by=StatusTranslationTable.c.language,
                primaryjoin=StatusTranslationTable.c.statuscodeid==PackageStatusTable.c.statuscodeid,
                foreignkey=StatusTranslationTable.c.statuscodeid,
                backref=backref('pstatuscode',
                    foreignkey=PackageStatusTable.c.statuscodeid,
                    primaryjoin=StatusTranslationTable.c.statuscodeid==PackageStatusTable.c.statuscodeid)
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

logMapper = assign_mapper(session.context, Log, LogTable,
        select_table=logJoin, polymorphic_on=logJoin.c.kind,
        polymorphic_identity='log')
        
assign_mapper(session.context, PersonPackageListingAclLog,
        PersonPackageListingAclLogTable,
        inherits=logMapper,
        inherit_condition=LogTable.c.id==PersonPackageListingAclLogTable.c.logid,
        polymorphic_identity='personpkglistacllog',
        properties={'acl': relation(PersonPackageListingAcl, backref='logs')})

assign_mapper(session.context, GroupPackageListingAclLog,
        GroupPackageListingAclLogTable,
        inherits=logMapper,
        inherit_condition=LogTable.c.id==GroupPackageListingAclLogTable.c.logid,
        polymorphic_identity='grouppkglistacllog',
        properties={'acl': relation(GroupPackageListingAcl, backref='logs')})

assign_mapper(session.context, PackageLog, PackageLogTable,
        inherits=logMapper,
        inherit_condition=LogTable.c.id==PackageLogTable.c.logid,
        polymorphic_identity='pkglog',
        properties={'package': relation(Package, backref='logs')})

assign_mapper(session.context, PackageListingLog, PackageListingLogTable,
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
