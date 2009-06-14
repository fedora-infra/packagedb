=================
New PackageDB API
=================

:Author: Toshio Kuratomi
:Date: 14 Oct, 2008
:For Version: 0.5.x

The first version of the PackageDB API grew somewhat organically.  This document
exlains what API changes are going into 0.4.x to create a more cohesive, easier
to use API.

.. contents::

-----------
Current API
-----------

There are three major parts to the current API that were driven by different
needs in the early development.

* ``pkgdb/acls/(bugzilla|vcs)``: Being able to get information comparable to
  the existing ``owners.list`` for the purpose of setting initialcclist and
  owner in bugzilla and generating acls on the cvs server.
* ``pkgdb/packages/name/$PKGNAME``: Being able to extract information from the
  packages for use by Bodhi_ and command line clients.  This mirrors the
  information available about a package in each page.
* ``pkgdb/packages/dispatcher/$METHOD``: JSON methods for the web UI to talk
  to when setting values.  This is the oldest of the interface and therefore
  has the most stuff that in hindsight was done wrong.

Two other parts of the interface are small and evolving.  They are somewhat
test beds for the new ideas in this document rather than legacy interfaces
that will need invasive changes to fix.

* ``pkgdb/users/``: needed to create a web interface for users to see which
  packages they owned.  Similar to ``pkgdb/packages/name`` this should let
  people extract the same information via json.
* ``pkgdb/stats/``: a web interface for people to see statistics about who
  owns how many packages.  This should also be constructed to let people
  extract the same information via json.

.. _Bodhi: https://fedorahosted.org/bodhi

Issues
======

Private Details
~~~~~~~~~~~~~~~

Currently, many of the controller methods in ``/packages/dispatcher`` use the
numeric id for the item they're talking about.  This is a detail that should
be hidden in the API.

New API Fixes
-------------

1. Use the username rather than the userid in all JSON API and on all web pages.

  A. This goes along with converting the database to `store usernames`_ rather
     than userids.

2. Use package name, not the numeric ids.
3. Send Collection Name and Collection Version, rather than Collection ID.
4. When talking about a PackageListing, send Package Name, Collection Name,
   and Collection Version instead of the PackageListing id. 
5. When talking about a particular acl, send the Package Name, Collection
   Name, Collection Version, acl name, and username instead of the acl id.
   (This example shows why we decided to send the id for things instead of the
   symbolic names.  However, there could be some ways to make this case better
   in the `Granularity`_ section)

.. _`store usernames`: NewDBModel.html#Change User and Group

Too Much Data
~~~~~~~~~~~~~

Currently, many methods return whole data structures from the database like
:class:`PackageListing`.  Because the remote end some other pieces of that,
for instance the list of :class:`PersonPackageListingAcls` on the
:class:`PackageListing`, we end up sending a huge nested data structure.  We
should make an effort to pare that down to a more reasonable sizeso that the
JSON data is smaller.

New API Fixes
-------------

Need to analyze the data that's actually being used vs what's being sent.
Then create different database queries that get more targetted data.  Also
need to preprocess some of the data so that we don't include so much
extraneous information when we finally send it.

Some Parameters are Composites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some parameters, especially ids that are passed to the dispatcher methods are
combinations of several values.  In other words, we sometimes see things like
this (Note: in the real code, the composite might also consist of numeric ids)

  /pkgdb/packages/dispatcher/set_owner/libfoo:FedoraDevel:toshio

being sent to a method like this::

  class Dispatcher(controller):
      def set_owner(self, divName):
          package, collection, newOwner = divName.split(':')
          pass

New API Fixes
-------------

Composites are a bit tricky.  Since we're going to stop sending numeric ids,
we'll have to send several pieces of data that's conceptually a composite to
the server.  We can either send them as three args and let the server deal
with it like this::

  /pkgdb/packages/dispatcher/set_owner/libfoo/Fedora/devel/toshio

  class Dispatcher(controller):
      def set_owner(self, package, collectionName, collectionVer, newOwner):
          pkgListing = PackageListing.query.filter(
                  and_(Package.name==package, 
                       Collection.name==collectionName,
                       Collection.version==collectionVer)).one()

or we can package it up on the client and send it to the server::

  class Dispatcher(controller):
      def set_owner(pkgListingId, newOwner):
          pkgListing = PackageListing.query.filter(
                  and_(Package.name==pkgListingId[0], 
                       Collection.name==pkgListingId[1],
                       Collection.version==pkgListingId[2])).one()

Since packaging the data into a single object (for instance a tuple/list) and
encoding that (probably with json) are extra steps, I'm inclined towards going
with option 1.  However, this does mean that sending things like acls will
have a very long argument string with no organization.  Hopefully, working on
`Granularity`_ will let us sidestep this issue in the majority of cases.  If
not, we should do the second one everywhere.  Consistency is very important
here.

Statelessness
~~~~~~~~~~~~~

The toggle methods in the current dispatcher class rely on the server not
changing the state of a toggle between the client rendering the page and
submitting the change request.  This doesn't work when multiple people update
the same information.

New API Fixes
-------------

1) Remove the toggle functions.

  A) Any replacements that are written should be done by setting something to a particular state.

*Bad*::

  def toggle_owner(self, package, collectionName, collectionVersion):
      pkgListing = find_package_listing(package, collectionName, collectionVersion)
          if pkgListing.owner == identity.current.user_name:
               pkgListing.owner = 'orphan'
          elif pkgListing.owner == 'orphan':
               pkgListing.owner = identity.current.user_name
          else:
               # Error, the new owner cannot become the owner of a currently owned package
               pass

*Good*::

  def set_owner(self, package, collectionName, collectionVersion, newOwner):
      pkgListing = find_package_listing(package, collectionName, collectionVersion)
      if allowed_set_owner(identity.current, pkgListing, newOwner):
          pkgListing.owner == 'newOwner'

Note that ``allowed_set_owner()`` in the second example hides the complexity
of deciding whether the user can set the owner to ``newOwner``.
``allowed_set_owner()`` would be more complex than what is in
``toggle_owner()``.

Unify CommandLine Client with WebUI API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Currently the Command line client has two methods that pretty much do
everything that the WebUI does with five to ten methods.  We want to merge
these so that the WebUI is just another client with a shared server API.

Separate Admin from User Functions
----------------------------------

Conversely, the command line client does a lot of things that a user should be
able to do.  But the APIs are locked so that only an admin can do them.  Admin
functions should be strictly separated from user functions so that only things
that really are admin-only have their own API.

New API Fixes
-------------

See the entry for `Granularity`_ for how we'll fix these issues.

Accessibility
~~~~~~~~~~~~~

We need to have some method of sending a request to the server via form
submission if the user's browser does not support AJAX.  To do this, the
client needs to provide a static html page to the browser.  A script on the
page will substitute dynamic entries for the static entries where appropriate.
For instance::

  <form>
  <input type="submit">
  </form>
  <script>
    jQuery.onload(// Create a handler to call an AJAX method instead of submitting this part of the page)
  </script>

If the browser supports scripts, then the submit button's action will be
overridden and we'll send AJAX requests as we currently do.  If the browser
does not support scripts, the submit button will POST the changes needed to a
server method which will return the refreshed page afterwards.

Granularity
~~~~~~~~~~~

Currently, each individual change on the Web App has its own method.  This
causes more round trips than necessary.  However, it does allow us to make
changes via AJAX since each method can operate simultaneously with the other
pieces.  We need to find a balance that does high level operations for speed
but allows us to make AJAX calls to perform those operations.

New API Fixes
-------------

There are several layers at which people may want to operate:

:_`Layer 1`:
  Make a single change.  This is what the API for the WebUI currently does.
  It's great for people who want to fine tune their acls on a single package
  but not so good for what we're really using the PackageDB for these days.
  This layer should probably be available but it doesn't (and can't) be
  optimized as well as the other layers since the grain is so fine.

:_`Layer 2`:
  Make a set of logical changes.  This includes things like: "Make person
  co-maintainer", "Approve All Pending Acls", "Take Ownership of Package in
  all Collections".  This is the level at which we usually want to operate.

:_`Layer 3`:
  Make a whole set of not necessarily logically related changes.  This is the
  ideal for the non-Javascript enabled version and may also be ideal for the
  command line client.  Make a bunch of changes to a package.  Hit Submit.
  All changes to the package are applied.  

We should be prioritizing `Layer 2`_ at the moment.  It is the layer at which
we can make the biggest difference in terms of usability for the end users and
responsiveness of applications.  `Layer 1`_ can be left in its semi-working
state for the moment and replaced with something that allows better
customization (maybe on the user's personal page).  `Layer 3`_ may need to be
worked on for accessibility reasons or we may be able to get away with doing a
non-optimal job with `Layer 2`.  (Multiple submit buttons on a page that hit
only commit a part of each page.)

`Layer 2`_ can have permissions set on logical units of change.  We should be
able to tell if a user is or is not allowed to ``watch_package()`` vs
``maintain_package()`` vs ``own_package()`` vs ``make_maintainer(other)``.
`Layer 3`_ would not be this granular which makes it harder to design
appropriate steps for.  `Layer 3`_ will have to check for proper permissions
for pieces of a requested change.

How to make this transition?
""""""""""""""""""""""""""""

1) Make a conscious effort to design and use API at `Layer 2`_.  When making a
   new element for a client (page or command line client), strive to use
   something that affects multiple logically related elements rather than
   individual objects.

2) Internally, move the code in the `Layer 1`_ Public API to their own class
   so we have very little code in the `Layer 1`_ controller.  Build `Layer 2`
   (at least, initially) by calling these `Layer 1` internal APIs.

3) Identify bottlenecks where we call one `Layer 2`_ API which makes an
   internal call 10 times which calls the database 10 times each.  Optimizing
   those to make less database calls will be a priority.

Logging
~~~~~~~

Logging each change to a set of acls independently is bad.  We want to log
changes to the set of acls as a single unit.  However, we want the user to
still experience each acl updating independently on the web.

New API Fixes
-------------

This can be done by making logging an asynchronous process.

1) Log to the db immediately along with the rest of the transaction just like
   now.
2) After a timeout, a process runs that looks through the db for all logs
   since the last run, picks out logs that should be bundled together, and
   sends a combined log to mailing lists, etc.

Error Handling
~~~~~~~~~~~~~~

Error handling is currently pretty ad hoc.  We return a variable, status with
every call to dispatcher.  This variable contains True if everything was fine,
False otherwise.  A message variable is sent if status==False.  We want to
standardize this in some manner so that our common client base class can take
error messages from bodhi or pkgdb with equal ease.

New API Fixes
-------------

We have two issues that need to be resolved:

1) How do we determine if a call produced an error?
2) How do we get a useful message from the error?

We're going to implement a standard for all Fedora Web Services via BaseClient
that resolves this.  It will use a variable named `exc` that returns an error
name (could be an actual exception but we currently don't want to raise these
on the client because we haven't evaluated what harm a server could do to a
client which raises arbitrary exception names) and a message in tg_flash.
BaseClient will take care of raising an exception from this information for
the client code to consume.

DB Changes
~~~~~~~~~~

Please see the New DB Model Documentation.  Some of these changes will be
internal and some of this will be externally visible.

.. toctree::
   :maxdepth: 2

   NewDBModel.rst

PEP8ify and Shorten Variable Names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Names of public variables and parameters are unwieldy in several ways:

1) They are too long.  This is especially seen in database column names.  This
   is bad because returning values as json has to repeat the column name
   multiple times.
2) They do not comply with PEP8_.  PEP8_ specifies underscores to divide words.
   We presently use camelCase.

.. _PEP8: http://python.org/dev/peps/pep-0008/

New API Fixes
-------------

Some of these changes will be fixed via `DB Changes`_.  Below
is a list of changes to parameters and return values unrelated to the
database.  In general the following rules are followed:

1) If it's a db object, it follows the db object spelling
2) If it's two words in standard usage, it becomes two words separated by
   underscore.
3) If it is abbreviated in one place, it is abbreviated everywhere.
4) Numeric id parameters are being removed.  We'll pass symbolic names or fully
   expanded names instead.  (pkg='foo', collectn='F-8' instead of
   pkg_listing_id='10998')

========================  ================
Current Name              New Name
------------------------  ----------------
package                   pkg
packageName               pkg_name
package_name              pkg_name
collection                collectn  (Use this for collection short name)
collectionName            collectn_name
collectionVersion         collectn_ver
cc_list                   cc_list
qacontact                 qa_contact
fasname                   username
pkg_listing_id            pkg_listing_id
collection_id             collectn_id
========================  ================

-----------------
Internal Cleanups
-----------------


Separate Display from Manipulation
==================================

:Status: Design

Because of the way decorators work, the controller methods are tightly bound
to being called from the web.  We cannot call a decorated controller method
and expect to get back reasonable information (often we will get an error).
We need to change controller methods to be a lightweight layer that feeds the
templates/json.  These talk to other functions/classes that do actual
manipulation of the database objects.  This allows us to reuse code much
easier since we are cleared about what should go into a controller and what
should be in its own function.

Organization
~~~~~~~~~~~~

A shadow class was considered but didn't seem very elegant::

  class Dispatcher(controller):
      pass
      # Variety of public methods that are @exposed to the web.

  class DispatchDoer(object):
      pass
      # Dispatcher methods are just a thin layer that calls methods in this class


Adding these methods to the mapped classes from the model is currently being
tried::

  class Dispatcher(controller):
      def change_owner(self, pkg, newOwner):
          pass
          PackageListing(pkg).set_owner(newOwner)

  class PackageListing(SABase):
      def set_owner(newOwner):
          if can_own(newOwner):
              self.owner = newOwner

Porting
-------

No matter what we come up with, there will be considerable internal
reorganization to make this work.  However, this should all be hidden from the
end-user behind the JSON API.  So there should be no external porting
required.
