# Version 0.2
from sqlobject import *
from sqlobject.inheritance import InheritableSQLObject
from turbogears.database import PackageHub

hub = PackageHub('pkgdb')
__connection__ = hub

class Collection(SQLObject):
    '''Collection of packages.
    
    Collections are a set of packages.  They can represent the packages in a
    distro, in a SIG, or on a CD.

    Fields:
    :name: "Fedora Core", "Fedora Extras", "Python", "GNOME" or whatever
        names-for-groupings you want.  If this is for a grouping that a SIG is
        interested in, the name should make this apparent.  If it is for one
        of the distributions it should be the name for the Product that will
        be used in Bugzilla as well.
    :version: The release of the `Collection`.  If the `Collection` doesn't
        have releases (for instance, SIGs), version should be 0.
    :status: Is the collection being worked on or is it inactive.
    :owner: Creator, QA Contact, or other account that is in charge of the
        collection.
    :summary: Brief description of the collection.
    :description: Longer description of the collection.
    '''
    name = StringCol(length=128, notNone=True)
    version = StringCol(length=128, notNone=True, default='0')
    status = EnumCol(enumValues=('development', 'active', 'maintanence',
        'EOL', 'rejected'), default='development', notNone=True)
    owner = IntCol(notNone=True)
    summary = UnicodeCol(length=128, notNone=False, default=None)
    description = UnicodeCol(notNone=False, default=None)

    ### TODO:  There's an sqlmeta atribute that may be a better way to enable
    # this.  Set a two column unique constraint and have a lookup function
    # that looks up by name-version.
    def byNameVersion(name, version='0'):
        '''Return the `Collection` from its altenateID, name-version.

        SQLObject doesn't handle multiple column alternateID's (unique values).
        We'll add a uniqueness constraint on the name-version into the database
        manually and create the convenience function here to return the entry
        by Name and Version.

        Arguments:
        :name: The `Collection`'s name.
        :version: The `Collection`'s version.

        Returns:
        '''
        pass

class Branch(SQLObject):
    '''`Collection`s with their own branch in the VCS have extra information.

    Fields:
    :collection: `Collection` this branch provides information for.
    :branchName: Name of the branch in the VCS ("FC-3", "devel")
    :distTag: DistTag used in the buildsystem (".fc3", ".fc6")
    :parent: Many collections are branches of other collections.  This field
        records the parent collection to branch from.
    '''
    collection = ForeignKey('Collection')
    branchName = StringCol(length=32, notNone=True)
    distTag = StringCol(length=32, notNone = True)
    parent = ForeignKey('Collection', notNone=False)

class Package(SQLObject):
    '''Data associated with an individual package.
   
    Fields:
    :name: Name of the package
    :summary: Brief summary of what the package is
    :description: Longer description of the package
    :status: Is the package ready to be built, in review, or other?
    '''
    name = StringCol(length=128, alternateID=True, notNone=True)
    summary = UnicodeCol(length=128, notNone=True)
    description = UnicodeCol(notNone=False, default=None)
    status = EnumCol(enumValues=('awaitingreview', 'underreview', 'approved',
        'denied'), default='awaitingreview', notNone=True)

class PackageListing(SQLObject):
    '''Associates a `Package` with a `Collection`.

    Fields:
    :package: `Package` id that is in this `Collection`.
    :collection: A `Collection` that holds this `Package`.
    :owner: id from the accountsDB for the owner of the `Package` in this
        `Collection`.  There is a special orphaned account to use if you want
        to orphan the package.
    :qacontact: Initial bugzilla QA Contact for this package.
    :status: Whether the `Package` was entered in the `Collection`.
    '''
    package = ForeignKey('Package', notNone=True)
    collection = ForeignKey('Collection', notNone=True)
    owner = IntCol(notNone=True)
    qacontact = IntCol(notNone=False)
    status = EnumCol(enumValues=('awaitingreview', 'awaitingbranch',
        'approved', 'denied'), default='awaitingreview', notNone=True)

class PackageVersion(SQLObject):
    '''Specific package version on a specific branch.

    Fields:
    :packageListing: `PackageListing` of the package within a collection.
    :epoch: RPM Epoch for this release of the `Package`.
    :version: RPM Version string.
    :release: RPM Release string including any disttag value.
    :status: What is happening with this particular version.
    '''
    packageListing = ForeignKey('PackageListing', notNone=True)
    epoch = StringCol(length=32, notNone=False)
    version = StringCol(length=32, notNone=True)
    release = StringCol(length=128, notNone=True)
    status = EnumCol(enumValues=('awaitingdevel', 'awaitingreview',
        'awaitingqa', 'awaitingpublish', 'approved', 'denied', 'obsolete'),
        default='awaitingdevel', notNone=True)

class PackageInterest(InheritableSQLObject):
    '''An entity that has an active or passive relation to the `PackageListing`.
   
    This is a base class meant to be inherited by people and group tables
    which have a relation to the `PackageListing`.

    `PackageInterestLog` assumes that records will never be removed from here.
    Instead, set the status to 'obsolete'.  This also means that we shouldn't
    change the role.  Instead, create a new PackageInterest record and mark
    this one obsolete.

    Fields:
    :packageListing: Package in a collection that the person is interested
        in watching.
    :status: Whether the person is allowed to watch the package at this level.
    :role: Whether the watcher is a maintainer, co-maintainer, or watcher.
        Used to authorize what the person can do to the package.
    '''
    packageListing = ForeignKey('PackageListing', notNone=True)
    status = EnumCol(enumValues=('awaitingreview', 'approved', 'denied',
        'obsolete'), default='awaitingreview', notNone=True)
    role = EnumCol(enumValues=('comaintainer', 'commitonly', 'buildonly',
        'watcher'), default='watcher', notNone=True)

class PackageInterestPerson(PackageInterest):
    '''A person that is interested in the `PackageListing`.

    Fields:
    :userID: `Person` id from accounts db interested in this package.
    '''
    userID = IntCol(notNone=True)
    
class PackageInterestGroup(PackageInterest):
    '''A group (usually a SIG) that is interested in the `PackageListing`.
    
    Fields:
    :groupID: Group id from the accounts db interested in this package.
    '''
    groupID = IntCol(notNone=True)
    
class Log (InheritableSQLObject):
    '''Keep track of changes made.
   
    This is a base class.  It is intended to be inherited by other classes
    to keep a record of changes to `Package`s.

    Fields:
    :userID: `Person` id from accountsdb for user who made the change.
    :changeTime: When the change was made.
    '''
    userID = IntCol(notNone=True)
    changeTime = DateTimeCol(default=sqlbuilder.func.NOW(), notNone=True)

class PackageLog(Log):
    '''Records changes to packages.

    Fields:
    :package: `Package` that changed.
    :action: What happened to the package.
    '''
    package = ForeignKey('Package', notNone=True)
    action = EnumCol(enumValues=('added', 'removed', 'statuschanged',
        'awaitingreview', 'underreview', 'approved', 'denied'), notNone=True)

class PackageListingLog(Log):
    '''Records `Package`s moving in and out of `Collection`s.

    Fields:
    :packageListing: `PackageListing` that has changed.
    :action: What happened to the package's status within the collection.
    '''
    packageListing = ForeignKey('PackageListing', notNone=True)
    action = EnumCol(enumValues=('added', 'removed', 'awaitingreview',
        'awaitingbranch', 'approved', 'denied'), notNone=True)

class PackageVersionLog(Log):
    '''Changes to the package's version.

    Fields:
    :packageVersion: `PackageVersion` that's changed.
    :action: What happened to this version of the package.
    '''
    packageVersion = ForeignKey('PackageVersion', notNone=True)
    action = EnumCol(enumValues=('added', 'awaitingdevel', 'awaitingreview',
        'awaitingqa', 'awaitingpublish', 'approved', 'denied', 'obsolete'),
        notNone=True)

class PackageInterestPersonLog(Log):
    '''History of who has watched the packages before.

    Fields:
    :packageInterest: The package/person pair that has changed.
    :action: What has happened to it.
    '''
    packageInterest = ForeignKey('PackageInterestPerson', notNone=True)
    action = EnumCol(enumValues=('added', 'awaitingreview', 'approved',
        'denied', 'obsolete'), notNone=True)

class PackageInterestGroupLog(Log):
    '''History of what groups have watched the packages before.

    Fields:
    :packageInterest: The package/Group pair that has changed.
    :action: What has happened to it.
    '''
    packageInterest = ForeignKey('PackageInterestGroup', notNone=True)
    action = EnumCol(enumValues=('added', 'awaitingreview', 'approved',
        'denied', 'obsolete'), notNone=True)
