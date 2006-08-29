class Collection(SQLObject):
    '''Collection of packages.
    
    Fields:
    :name: "Core5". "Extras4' or whatever names-for-groupings you want
    '''
    name = StringCol(length=128, notNone=True)

class Package(SQLObject):
    '''Data associated with an individual package.
   
    Fields:
    :name: Name of the package.
    :created: Date the package was entered into the db
    :status: Is the package ready to be built, in review, or other?
    '''
    name = StringCol(length=128, notNone=True)
    created = DateTimeCol(default=sqlbuilder.func.NOW(), notNone=True)
    status = EnumCol(enumValues=('awaitingreview', 'approved', 'denied'),
            default='awaitingreview', notNone=True)

class PackageHistory(SQLObject):
    '''Records changes to packages.

    Fields:
    :package: The `Package` that changed.
    :by_user_id: `Person` id from accountsdb for user who made the change.
    :action: What happened to the package.
    :status: ?
    :when: When the change was made.
    '''
    package = ForeignKey('Package', notNone=True)
    by_user_id = IntCol(notNone=True)
    action = EnumCol(enumValues=('added', 'removed', 'statuschanged'),
            notNone=True)
    status = StringCol(length=128, notNone=True)
    when = DateTimeCol(default=sqlbuilder.func.NOW(), notNone=True)

class PackageListing(SQLObject):
    '''Associates a `Package` with a `Collection`.

    Fields:
    :package: `Package` id that is in this `collection`.
    :collection: A `Collection` that holds this `package`.
    :created: Date the `package` was requested for this `collection`.
    :status: Whether the `package` was entered in the `collection`.
    '''
    package = ForeignKey('Package', notNone=True)
    collection = ForeignKey('Collection', notNone=True)
    created = DateTimeCol(default=sqlbuilder.func.NOW(), notNone=True)
    status = EnumCol(enumValues=('awaitingreview', 'awaitingbranch',
        'approved', 'denied'), default='awaitingreview', notNone=True)

class PackageListingHistory(SQLObject):
    '''Records `Package`s moving in and out of `Collection`s.

    Fields:
    :package_listing: `PackageListing` that has changed.
    :by_user_id: `Person` id from accountsdb that requested the package be
        moved in or out of the `Collection`.
    :action: What happened to the package's status within the collection.
    :status: ?
    :when: When the change was made.
    '''
    package_listing = ForeignKey('PackageListing', notNone=True)
    by_user_id = IntCol(notNone=True)
    action = EnumCol(enumValues=('added', 'removed', 'statuschanged'),
            notNone=True)
    status = StringCol(length=128, notNone=True)
    when = DateTimeCol(default=sqlbuilder.func.NOW(), notNone=True)

class PackageVersion(SQLObject):
    '''Specific package version on a specific branch.

    Fields:
    :package_listing: `PackageListing` of the package within a collection.
    :version: RPM EVR of the package, potentially including disttag.
    :status: What is happening with this particular version.
    :created: When the package version was created.
    '''
    package_listing = ForeignKey('PackageListing', notNone=True)
    version = StringCol(length=128, notNone=True)
    status = EnumCol(enumValues=('awaitingdevel', 'awaitingreview',
        'awaitingqa', 'awaitingpublish', 'approved', 'denied', 'obsolete'),
        default='awaitingdevel', notNone=True)
    created = DateTimeCol(default=sqlbuilder.func.NOW(), notNone=True)

class PackageVersionHistory(SQLObject):
    '''Changes to the package's version.

    Fields:
    :package_version: `PackageVersion` that's changed.
    :by_user_id: `Person` id from accountsdb that made the change.
    :action: What happened to this version of the package.
    :status: ?
    :when: When the change was made.
    '''
    package_version = ForeignKey('PackageVersion', notNone=True)
    by_user_id = IntCol(notNone=True)
    action = EnumCol(enumValues=('added', 'statuschanged'), notNone=True)
    status = StringCol(length=128, notNone=True)
    when = DateTimeCol(default=sqlbuilder.func.NOW(), notNone=True)

class PackageInterest(SQLObject):
    '''A person that is interested in the package.

    PackageInterestHistory assumes that records will never be removed from
    here.  Instead, set the status to 'obsolete'.

    Fields:
    :user_id: `Person` id from accounts db interested in this package.
    :package_listing: Package in a collection that the person is interested
        in watching.
    :status: Whether the person is allowed to watch the package at this level.
    :role: Whether the watcher is a maintainer, co-maintainer, or watcher.
        Used to authorize what the person can do to the package.
    '''
    user_id = IntCol(notNone=True)
    package_listing = ForeignKey('PackageListing', notNone=True)
    status = EnumCol(enumValues=('awaitingreview', 'approved', 'denied',
        'obsolete'), default='awaitingreview', notNone=True)
    role = EnumCol(enumValues=('watcher', 'owner'), default='watcher',
            notNone=True)

class PackageInterestHistory(SQLObject):
    '''History of who has watched the packages before.

    Fields:
    :package_interest: The package/person pair that has changed.
    :action: What has happened to it.
    :status: ?
    :when: When the change occurred.
    '''
    package_interest = ForeignKey('PackageInterest', notNone=True)
    action = EnumCol(enumValues=('added', 'statuschanged'), notNone=True)
    status = StringCol(length=128, notNone=True) # Not EnumCol, but  
could be changed to be one.
    when = DateTimeCol(default=sqlbuilder.func.NOW(), notNone=True)
