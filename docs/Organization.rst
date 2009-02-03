============================
Internal Code Reorganization
============================

The code internals currently place the bulk of their information in the
controllers.  This is not very object oriented and leads to some controllers
(dispatcher) that are very big and only loosely related to each other.

.. contents::

--------
Overview
--------

Old Structure
=============

1) User clicks on a link
2) Link goes through TurboGears/cherrypy to get a controller method
3) Controller method parses data given by the user
4) Controller method checks that the data is valid
5a) Controller method asks database model for information
5b) Controller method changes data in the database model
6) Controller logs data to logging tables
7) Controller checks for exceptions from saving data to database
8) Controller emails users with changes
9) Controller returns values to the user

New Structure
=============

1) User clicks on a link
2) Link goes through TurboGears/CherryPy to get a controller method
3) Validator for the controller checks that the data is valid
4) Validator transforms data into database objects where appropriate
5a) Controller method asks database model for information
5b) Controller method asks database model to update itself
6) Database model adds/removes/updates records
7) Controller logs the transaction to simple logging table
8) Controller checks for exceptions from the database and rollsback() the
   transaction if errors are found.
9) Controller returns values to the user

A) Asynchronous process checks log table
B) Combines and sends new entries to the log table to various entities.

---------
Specifics
---------

3 & 4 Validators
================

Generic checks will go in pkgdb/validators.py.

Those are checks for certain types of parameters.  Valid package, etc.  These
checks will also return certain types of data in some circumstances.  Turning
a set of Package and Collection Shortname into a PackagListing, for instance.

However, we want to be careful as those will each invoke database calls and
having too many database calls will bog down the machine.  The number of db
calls can be controlled from inside of the controller methods.

Alternately, we could write specific validators for each controller method.
So the validator will know whether to load the PackageListing or not.

5 & 6 Controller/Db Model Interaction
=====================================

Querying for information from the db should be simple to do using sqlalchemy
commands in the controller.  However, creating and updating information is
trickier.  This often requires that we check whether information already
exists and using that before going further.  We want to push that sort of
logic out to the model.

7 Logging
=========

Currently, log generation is complex.  A command like add_package
generates many logs on the server to add the package, add the packagelistings,
add the group and user acls.  We want to Simplify the logs for that:

Logs:
id serial
datetime changetime
description
key text


8 Controller Checks for Database Errors
=======================================

Catching every exception in the manner specified here may have too much
boilerplate.  Luckily TurboGears provides a way to catch exceptions via a
decorator.  We should look into using the `@exception_handler`_ decorator to
catch these.  The handler should work as long as we can separate out the type
of exceptions that we want to return -- example: every time we get an
InvalidRequestError we want to return CannotClone.

.. _`@exception_handler`: http://docs.turbogears.org/1.0/ErrorReporting

Calling the Model
~~~~~~~~~~~~~~~~~

Calls to the database model should catch database errors::
    try:
        pkg_for_f10 = pkg.create_listing('F-10')
    except InvalidRequestError, e:
        flash(_('Unable to save database %(msg)s') % {'msg': e.message})
        return dict(exc='DatabaseError')

Commit
~~~~~~

If a controller causes changes to occur to the page, something similar to the
following should happen::
    try:
        session.flush()
    except SQLError, e:
        flash(_('Unable to save database %(msg)s') % {'msg': e.message})
        return dict(exc='DatabaseError')


