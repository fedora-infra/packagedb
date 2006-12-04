-- Fedora Package Database
-- Version 0.3

drop database pkgdb;
create database pkgdb with owner pkgdbadmin encoding 'UTF8';
\c pkgdb

-- Collection of packages.
-- 
-- Collections are a set of packages.  They can represent the packages in a
-- distro, in a SIG, or on a CD.
--
-- Fields:
-- :name: "Fedora Core", "Fedora Extras", "Python", "GNOME" or whatever
--   names-for-groupings you want.  If this is for a grouping that a SIG is
--   interested in, the name should make this apparent.  If it is for one
--   of the distributions it should be the name for the Product that will
--   be used in Bugzilla as well.
-- :version: The release of the `Collection`.  If the `Collection` doesn't
--   have releases (for instance, SIGs), version should be 0.
-- :status: Is the collection being worked on or is it inactive.
-- :owner: Creator, QA Contact, or other account that is in charge of the
--   collection.  This is a foreign key to an account id number.  (Since the
--   accounts live in a separate db we can't have the db enforce validity.)
-- :publishURLTemplate: URL to packages built for this collection with
--   [ARCH] and [PACKAGE] as special symbols that can be substituted from the
--   specific package built.
-- :pendingURLTemplate: URL to packages built but not yet in the repository
--   with [ARCH] and [PACKAGE] as special symbols that can be substituted from
--   the specific package built.
-- :summary: Brief description of the collection.
-- :description: Longer description of the collection.
create table Collection (
  id serial primary key,
  name text not null,
  version text not null,
  status text not null default 'development',
  owner integer not null,
  publishURLTemplate text null,
  pendingURLTemplate text null,
  summary text null,
  description text null,
  unique (name, version),
  check (status = 'development' or status = 'active' or status = 'maintanence'
    or status = 'EOL' or status = 'rejected')
);

-- `Collection`s with their own branch in the VCS have extra information.
--
-- Fields:
-- :collectionId: `Collection` this branch provides information for.
-- :branchName: Name of the branch in the VCS ("FC-3", "devel")
-- :distTag: DistTag used in the buildsystem (".fc3", ".fc6")
-- :parent: Many collections are branches of other collections.  This field
--    records the parent collection to branch from.

create table Branch (
  collectionId integer not null primary key,
  branchName varchar(32) not null,
  distTag varchar(32) not null,
  parentId integer null,
  foreign key (parentId) references Collection(id),
  foreign key (collectionId) references Collection(id)
);

-- Associate the packages in one collection with another collection.
--
-- This table is used to allow one `Collection` to be based on another with
-- certain packages that are overridden or not available in the `base`
-- `Collection`.  For instance, a `Collection` may be used to experiment with
-- a major version upgrade of python and all the dependent packages that need
-- to be rebuilt against it.  In this scenario, the base might be
-- "Fedora Core - devel".  The overlay "FC devel python3".  The overlay will
-- contain python packages that override what is present in the base.  Any
-- package that is not present in the overlay will also be searched for in
-- the base collection.
-- Once we're ready to commit to using the upgraded set of packages, we want
-- to merge them into devel.  To do this, we will actually move the packages
-- from the overlay into the base collection.  Probably, at this time, we
-- will also mark the overlay as obsolete.
--
-- Keeping things consistent is a bit problematic because we have to search for
-- for packages in the collection plus all the bases (an overlay can have
-- multiple bases) and any bases that they're overlays for.  SQL doesn't do
-- recursion -- in and of itself so we have to work around it in one of these
-- ways:
-- 1) Do the searching for packages in code; either a trigger on the server or
--    in any application code which looks at the database.
-- 2) Use a check constraint to only have one level of super/subset.  So if
--    devel contains python-2.5, devel cannot be a subset and python-2.5 cannot
--    be a superset to any other collection.  Have an insert trigger that
--    checks for this.
-- 3) Copy the packages.  When we make one collection a subset of another, add
--    all its packages including subset's packages to the superset.  Have an
--    insert trigger on packageList and packageListVer that check whether this
--    collection is a subset and copies the package to other collections.
-- Option 1, in application code may be the simplest to implement.  However,
-- option 3 has the benefit of running during insert rather than select.  As
-- always, doing something within the database rather than application logic
-- allows us to keep better control over the information.
--
-- * Note: Do not have an ondelete trigger as there may be overlap between the
-- packages in the parent and child collection.
--
-- Fields:
-- :overlay: The `Collection` which overrides packages in the base.
-- :base: The `Collection` which provides packages not explicitly listed in
--    `overlay`.
create table CollectionSet (
  overlay integer,
  base integer,
  primary key (overlay, base),
  foreign key (overlay) references Collection(id),
  foreign key (base) references Collection(id)
);

-- Data associated with an individual package.
-- 
-- Fields:
-- :id: Unique primary key
-- :name: Name of the package
-- :summary: Brief summary of what the package is
-- :description: Longer description of the package
-- :reviewURL: URL for the review ticket for this package
-- :status: Is the package ready to be built, in review, or other?
create table Package (
  id serial primary key,
  name text not null unique,
  summary text not null,
  description text null,
  reviewURL text null,
  status text not null default 'awaitingreview',
  check (status = 'awaitingreview' or status = 'underreview' or status = 'approved' or status = 'denied')
);

-- Specific version of a package to be built. 
--
-- Fields:
-- :id: Easily referenced primary key
-- :packageId: The package this is a specific build of.
-- :epoch: RPM Epoch for this release of the `Package`.
-- :version: RPM Version string.
-- :release: RPM Release string including any disttag value.
-- :status: What is happening with this particular version.
create table PackageVersion (
  id serial not null primary key,
  packageId integer not null,
  epoch text null,
  version text not null,
  release text not null,
  status text null,
  unique (packageId, epoch, version, release),
  foreign key (packageId) references Package(id),
  check (status = 'awaitingdevel' or status = 'awaitingreview' or
    status = 'awaitingqa' or status = 'aaitingpublish' or status = 'approved' or
    status = 'denied' or status = 'obsolete')
);

-- Associate a particular build with a collection.
-- A built package may be part of multiple collections.
--
-- Fields:
-- :packageVersionId: The `PackageVersion` that is being added to a collection.
-- :collectionId: The `Collection` that the PackageVersion is being added to.
create table PackageVersionListing (
  packageVersionId integer not null,
  collectionId integer not null,
  primary key (packageVersionId, collectionId),
  foreign key (packageVersionId) references PackageVersion(id),
  foreign key (collectionId) references Collection(id)
);

-- Associates a `Package` with a `Collection`.
-- A package residing in a specific branch.
-- 
-- Fields:
-- :packageId: `Package` id that is in this `Collection`.
-- :collection: A `Collection` that holds this `Package`.
-- :owner: id from the accountsDB for the owner of the `Package` in this
--    `Collection`.  There is a special orphaned account to use if you want
--    to orphan the package.
-- :qacontact: Initial bugzilla QA Contact for this package.
-- :status: Whether the `Package` was entered in the `Collection`.
create table PackageListing (
  id serial primary key,
  packageId integer not null,
  collectionId integer not null,
  owner integer not null,
  qacontact integer null,
  status text not null default 'awaitingreview',
  foreign key (packageId) references Package(id),
  foreign key (collectionId) references Collection(id),
  unique(packageId, collectionId),
  check (status = 'awaitingreview' or status = 'awaitingbranch' or
    status = 'approved' or status = 'denied' or status = 'obsolete')
);

-- Permissions for who can make various changes to the code.
-- We want to limit the access that a given person may have to edit the package
--
-- Fields:
-- :id: Primary key
-- :pkgListId: What package in what collection has this value.
-- :acl: The permission being set.
-- :status: Whether this permission is active.
create table PackageACL (
  id serial primary key,
  packageListingId integer not null,
  acl text not null,
  status text not null,
  foreign key (packageListingId) references PackageListing(id),
  check (status = 'awaitingreview' or status = 'approved' or status = 'denied'
    or status = 'obsolete'),
  check (acl = 'commit' or acl = 'build' or acl = 'watchbugzilla'
    or acl = 'watchcommits' or acl = 'approveacls' or acl = 'checkout')
);

-- ACLs that allow a person to do something
--
-- Fields:
-- :packageACLId: Inherit from an ACL record.
-- :userId: User id from the account system.
create table PersonPackageACL (
  packageACLId integer primary key,
  userId integer not null,
  foreign key (packageACLId) references PackageACL (id)
);

-- ACLs that allow a group to do something
--
-- Fields:
-- :packageACLId: Inherit from an ACL record.
-- :groupId: Group id from the account system.
create table GroupPackagePermissions (
  packageACLId integer primary key,
  groupId integer not null,
  foreign key (PackageACLId) references PackageACL (id)
);
  
-- Log a change to the packageDB.
--
-- Fields:
-- :id: Primary key
-- :userId: Who made the change.
-- :changeTime: Time that the change occurred.
create table Log (
  id serial primary key,
  userId integer not null,
  changeTime timestamp default now() not null
);

-- Log a change made to the Package table.
--
-- Fields:
-- :logId: The id of the log entry.
-- :packageId: The package that changed.
-- :action: What happened to the package.
-- :description: Additional information about the change.
create table PackageLog (
  logId integer primary key,
  packageId integer not null,
  action text not null,
  description text null,
  check (action = 'added' or action = 'removed' or action = 'statuschanged' or
    action = 'awaitingreview' or action = 'underreview' or action = 'approved'
    or action = 'denied'),
  foreign key (logId) references Log(id),
  foreign key (packageId) references Package(id)
);

-- Log changes to packages in collections.
--
-- Fields:
-- :logId: The id of the log entry.
-- :packageListingId: The packageListing that changed.
-- :action: What happened to the package in the collection.
-- :description: Additional information about the change.
create table PackageListingLog (
  logId integer primary key,
  packageListingId integer not null,
  action text not null,
  description text null,
  check (action = 'added' or action = 'removed' or action = 'awaitingreview'
    or action = 'awaitingbranch' or action = 'underreview' or
    action = 'approved' or action = 'denied'),
  foreign key (logId) references Log (id),
  foreign key (packageListingId) references PackageListing(id)
);

-- Log changes to built packages.
--
-- Fields:
-- :logId: The id of the log entry.
-- :packageVersionId: The `PackageVersion` that changed.
-- :action: What happened to the `PackageVersion`.
-- :description: Additional information about the change.
create table PackageVersionLog (
  logId integer primary key,
  packageVersionId integer not null,
  action text not null,
  description text null,
  check (action = 'added' or action = 'awaitingdevel' or
    action = 'awaitingreview' or action = 'awaitingqa' or
    action = 'aaitingpublish' or action = 'approved' or action = 'denied' or
    action = 'obsolete'),
  foreign key (logId) references Log (id),
  foreign key (packageVersionId) references PackageVersion(id)
);

-- Log changes to built package ACLs.
--
-- Fields:
-- :logId: The id of the log entry.
-- :packageVersionId: The `PackageACL` that changed.
-- :action: What happened to the ACLs for the package.
-- :description: Additional information about the change.
create table PackageACLLog (
  logId integer primary key,
  packageACLId integer not null,
  action text not null,
  description text null,
  check (action = 'added' or action = 'awaitingreview'
    or action = 'awaitingbranch' or action = 'underreview' or
    action = 'approved' or action = 'denied' or action = 'obsolete'),
  foreign key (logId) references Log (id),
  foreign key (packageACLId) references PackageACL(id)
);

-- FIXME: In order to implement groups/categories/comps we need to have tables
-- that list the subpackages per collection.
--
-- create table BuiltPackage (
--   id serial primary key,
--   packageVersionId integer,
--   name text,
--   summary text,
--   description text,
--   unique packageVersionListingId, name
-- );
-- create table BuiltPackageListing (
--   id serial primary key,
--   builtPackageId integer,
--   collectionId integer,
-- );
-- create table Category (
--   category text primary key
-- );
-- create table BuiltPackageCategories (
--   category text references Category(category),
--   builtPackageListingId references BuiltPackageListing(id),
-- );
