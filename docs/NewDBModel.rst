===================
Changes to DB Model
===================

:Author: Toshio Kuratomi
:Date: 16 Oct, 2008

We want to make some changes to the DB Model.  In some cases these will be
fairly invasive and require rewriting various bits of both client code and
pkgdb server code.  Client code could hopefully be incorporated into
`fedora.client.pkgdb` so that there's a single place to update for changes in
the server in the future.

.. contents::

----------------------
Remove One::Many Lists
----------------------

:Status: Design Finalizing

The 0.3.x API was updated to take advantage of SA-0.4's dictionary collections.
We did this by adding the dictionary mappings in addition to the list of items.
So, for instance, the Package class has both `Package.listings` => `list()`
of :class:`PackageListing` objects and `Package.listings2` => `dict()` of
:class:`PackageListing` objects keyed on the :class:`Collection` short name.
For the 0.4.x release we want to move the dictionary mapping to
`Package.listing` and remove `Package.listing2`.

Porting
=======

You'll need to change your code in the following ways:

* If your code requires a list::

    - pkg_list = Package.listing
    + pkg_list = Package.listing.values()

* If your code is using the ``listing2`` interface::

    - pkg_dict = Package.listing2
    + pkg_dict = Package.listing

This affects the following pairs of methods:

==================== ========   ========    ==================
      Class          Old Dict   New Dict    Old List (removed)
-------------------- --------   --------    ------------------
PersonPackageListing acls2      acls        acls
GroupPackageListing  acls2      acls        acls
Collection           listing2   listing     listing
Package              listing2   listing     listing
PackageListing       people2    people      people
PackageListing       groups2    groups      groups
CollectionStatus     locale     locale      translations
PackageListingStatus locale     locale      translations
PackageStatus        locale     locale      translations
PackageAclStatus     locale     locale      translations
==================== ========   ========    ==================

---------------------
Change User and Group
---------------------

:Status: Design Finalizing

We're going to switch from using numeric userid/groupid's to usernames and
groupnames from the Fedora Account System. This makes changing usernames
harder but it is something that's already a problem with bodhi, koji, etc.
The plus side is we don't have to lookup information in FAS just to have a
reasonable way to identify the user to the person using hte pkgdb.

As part of this change we will also change the following fields:

===========================  =========================
    Old Column Name              New Column Name
---------------------------  -------------------------
PersonPackageListing.userid  PersonPackageListing.user
GroupPackageListing.groupid  GroupPackageListing.group
===========================  =========================

In many cases, the json API added convenience attributes with the username
embedded.  These will be removed as well as they're now redundant:

========================  ====================
Convenience Attribute     New Attribute
------------------------  --------------------
PackageListing.owneruser  PackageListing.owner
[Incomplete]              [Incomplete]
========================  ====================

Porting
=======

In order to port you'll need to change any code that expects numeric userids
to accept usernames instead.  You'll have to send back usernames instead.  For
the most part, this will simply mean removing code which did conversions as you
probably wanted to get usernames before.  Sometimes, when you wanted to retrieve
more information from FAS, it will mean you have to use a different FASmethod to
retrieve the data as you'll have a username for FAS instead of a userid.

Here's an example of the old way to do things::
    pkgdb = PackageDB()
    fas = AccountSystem(username=USER, password=PASS)
    pkgdata = pkgdb.send_request('/package/name/kernel')
    uid = pkgdata.packageListings[0]['owner']
    username = pkgdata.packageListings[0]['owneruser']
    person = fas.person_by_id(uid)

Converted to the new way::
    pkgdb = PackageDB()
    fas = AccountSystem(username=USER, password=PASS)
    pkgdata = pkgdb.send_request('/package/name/kernel')
    username = pkgdata.packageListings['devel']['owner']
    person = fas.person_by_username(username)
    uid = person.id

---------------------------------
Normalize Statuscode/StatuscodeId
---------------------------------

:Status: Design Finalizing

Statuses are identified by a numeric id.  :class:`StatusCodeTranslation` and
all the StatusCode tables call that column `statuscodeid`.  Other instances
call it `statuscode`.  We're going to standardize on `status_id` since this
often shows up when we return database objects to the user and so should
follow PEP8.

Affected tables:

* :class:`collectionlogstatuscode`
* :class:`collectionstatuscode`
* :class:`packageacllogstatuscode`
* :class:`packageaclstatuscode`
* :class:`packagebuildlogstatuscode`
* :class:`packagebuildstatuscode`
* :class:`packagelistinglogstatuscode`
* :class:`packagelistingstatuscode`
* :class:`packagelogstatuscode`
* :class:`packagestatuscode`
* :class:`statuscodetranslation`

Porting
=======

Change all occurences of `statuscodeid` and `statuscode` to `status_id`

--------------------
Reorganize the Model
--------------------

:Status: Implemented 0.3.9

Instead of having the entire model in one big file, breaking it up so separate
functionality is in separate files would be a plus for maintainability.

Porting
=======

This is done in the 0.3.x branch as it does not change the external API.

---------------
Simpler Logging
---------------

:Status: Design

Logging in the pkgdb is very precise right now.  This, unfortunately, also
makes it hard to work with.  You have to touch both the generic log table and
the table that logs the specific table you are working with when you want to
change something.  FAs2 has a single log table that is much more free form.
Perhaps this is the way to go.

If we do this, we'll need to add more timestamps to the other tables as we
currently depend on being able to ask the highly structured logs to tell us
when certain things happened.  (Note: This restriction is not in code
anywhere, it's just in the assumption that the user can search the logs for
when something happened because of the structured nature of the log table
hierarchy.)

Porting
=======
There is currently no server methods that expose the log tables so there is no
external interface to port.

Internally we'll have to restructure how we construct and save logs.

--------------------------
Change Ownership to an Acl
--------------------------

:Status: Design

It might simplify code if ownership is specified as an acl in the database
instead of a special field in the :class:`PackageListing`.  This is because
only bugzilla cares who is the owner versus a comaintainer (someone with
approveacls).

Porting
=======

Ownership will no longer be available directly from the
:class:`PackageListing`.  Most code can be simplified to check the person's
acls for either approveacls or ownership instead of looking in both the
:class:`PackageListing` table and the acl tables.  Code that interacts with
bugzilla will have to be changed to specifically find the owner acl.

External code that looked up the owner by simply looking in the
:class:`PackageListing` will now have to traverse the acls.  However, many of
those pieces of code should really be looking at comaintainers anyway, so this
makes their code better.

------------------
Lazy/Eager Loading
------------------

:Status: Analyzing Code

Instead of relying on SQLAlchemy's defaults for whether to load foreign key
relationships we should look at whether we always or never pull in the related
tables.  Redefining the frequently pulled in tables to eager load[#]_ and the
seldom used tables to lazy load will be a large win.  This is settable per
query as well as when creating the mapper so there is a great deal of
flexibility here.

Porting
=======

This touches internal API only and can be done in the 0.3.x branch.

.. [#]: http://www.sqlalchemy.org/docs/04/mappers.html#advdatamapping_relation_strategies

---------------------
Pluralize Table Names
---------------------
Database tables hold sets of records.  So instead of describing a Table as
Collection it should be collections.  However, the classes which map to the
tables are single instances rather than multiples.  So they will remain
singular.

Porting
=======

Database tables will change to plural form.

The Table definitions in model/\*.py will have to be adapted to find the right
table.  The classes that are mapped to the tables will retain the same name so
most code consuming the models will remain unchanged.  Sometimes there will be
old SQLAlchemy-0.3 code which references the Tables directly will need to be
changed.  These should be changed to reference the mapped class instead of
merely changed to reference the new table name.

Example::
    # Old:
    CollectionTable = Table('collection')
    mapper(Collection, CollectionTable)
    collection = Collection.query.filter(CollectionTable.c.version >= '8')

    # New:
    CollectionsTable = Table('collections')
    mapper(Collection, CollectionsTable)
    collection = Collection.query.filter(Collection.version >= '8')

------------------------------
Shorten Table and Column Names
------------------------------
Some table and column names are unwieldy because of their length.  We're going
to use some standard abbreviations and simply shorten some other names to make
these easier to use.

This also has a good effect on the json output.  Since we sometimes return
lists or database objects and the column names can show up there multiple
times this can drastically cut the amount of data sent over the wire.


Table Changes
=============

===========================  =================================
Current Name                 New Name
---------------------------  ---------------------------------
collectionlogstatuscode      collectionlogstatus
grouppackagelisting          group
grouppackagelistingacl       groupacl
packageacllogstatuscode      (merge with packageaclstatus)
packageaclstatuscode         packageaclstatus
packagelistinglogstatuscode  (merge with packagelistingstatus)
packagelistingstatuscode     packagelistingstatus
packagelog                   packagelog
packagelogstatuscode         (merge with packagestatus)
packagestatuscode            packagestatus
personpackagelisting         person
personpackagelistingacl      personacl
personackagelistingacllog    personacllog
statuscode                   status
statuscodetranslation        statustranslation
===========================  =================================

Column Renames
==============

Package
-------
reviewurl review_url
shouldopen should_open
statuscode status_id

Collection
----------
statuscode status_id
publishurltemplate drop
pendingurltemplate drop

Logs
----
\*id  \*_id
userid user
changetime change_time

CollectionPackage
-----------------
statuscode status_id
numpkgs num_pkgs

Groups
------
group_id group
packagelistingid pkglisting_id

GroupAcls
---------
grouppackagelistingid group_id
statuscode status_id

