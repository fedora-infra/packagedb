==============
 New Tags API
==============

:Author: Ionuț Arțăriși
:Date: 19 Aug, 2009
:For Version: 0.5.x

The new tags (`/pkgdb/tag`) API will be used to tag Applications. These are a
wrapper on top of PackageBuild objects. Basically all the PackageBuilds with
the same name get tagged the same. (PackageBuild.name is a FK to
Application.name in the db).
PackageBuilds are specific rpms, they have a version, a release, an arch and
belong to a specific yum repository.

This API will be used by:
* the pkgdb in its views to allow FAS users to tag builds via the WebUI
* other Fedora Infrastructure services

.. contents::

---------
Languages
---------

Each tag belongs to a specific language. The same tag can exist in multiple
languages at the same time. Tags don't get translated through a l10n process,
instead they are entered through the pkgdb API. That way, different
cultures/languages will tag apps differently according to their local IT
culture.  

The language must be mentioned on
https://translate.fedoraproject.org/languages/ . Either the long language name
or the shortname is accepted by pkgdb. The default language for all methods is
'American English (en_US)'.

-------
Scoring
-------

By default, each application/tag combination has a score showing how many
times that specific combination was entered in the pkgdb. This score might
come in handy when rating tags or when drawing tagclouds.

---------------------
Application Retrieval
---------------------

The API can retrieve tags belonging to one or more applications provided as
arguments to the `tag/packages` method.

-------------------
Application Tagging
-------------------

Applications can be tagged by sending a set of `apps` and `tags`, followed by
a `language` to the `tag/add` method. PkgDB (postgresql) will automatically
score the tags on each app. If the app has already been tagged with that
specific tag, the score will be incremented, otherwise, the tag will first be
associated to the build and the score will be set to 1.

---------------------
Application Searching
---------------------

The `tag/search` method receives one or more `tags`, an `operator` (OR|AND)
and a `language`. If the operator is `OR` (default), the method will return
all apps that contain at least ONE of the tags; using the `AND` operator will
result in the method returning all apps that contain at least ALL of the tags.

------------------
Application Scores
------------------

The `tag/scores` method will return a dictionary of tag : score items
belonging to a given `application` given as argument. 
