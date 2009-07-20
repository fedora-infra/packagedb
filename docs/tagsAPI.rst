==============
 New Tags API
==============

:Author: Ionuț Arțăriși
:Date: 20 Jul, 2009
:For Version: 0.5.x

The new tags (`/pkgdb/tag`) API will be used to tag PackageBuild objects (specific rpms which have a version, a release, etc.).

This API will be used by:
* the pkgdb in its views to allow FAS users to tag builds via the WebUI
* other Fedora Infrastructure services

.. contents::

------------
Generalities
------------

Each tag belongs to a specific language. The same tag can exist in multiple languages at the same time. Tags don't get translated through a l10n process, instead they are entered through the pkgdb API. That way, different cultures/languages will tag builds differently according to their local IT culture.

Language
========

The language must be mentioned on https://translate.fedoraproject.org/languages/ . Either the long language name or the shortname is accepted by pkgdb. The default language for all methods is 'American English (en_US)'.

Scoring
=======

By default, each build/tag combination has a score showing how many times that specific combination was entered in the pkgdb. This score might come in handy when rating tags or when drawing tagclouds.

Branches
========

Since each build belongs to a specific Repo, one also belongs to a specific pkgdb Collection/Branch. An optional argument is provided to all of the following methods to specify the branch to look in, making it easier for users to pick a specific release, rather than a repo. The default is the latest stable Fedora release.

----------------------
PackageBuild Retrieval
----------------------

The API can retrieve tags belonging to one or more builds provided as arguments to the `tag/packages` method.

--------------------
PackageBuild Tagging
--------------------

PackageBuilds can be tagged by sending a set of `packages` and `tags`, followed by a `language` to the `tag/add` method. PkgDB will automatically score the tags on each packagebuild. If the build has already been tagged with that specific tag, the score will be incremented, otherwise, the tag will first be associated to the build and the score will be set to 1.

----------------------
PackageBuild Searching
----------------------

The `tag/search` method receives one or more `tags`, an `operator` (OR|AND) and a `language`. If the operator is `OR` (default), the method will return all builds that contain at least ONE of the tags; using the `AND` operator will result in the method returning all packagebuildss that contain at least ALL of the tags.

-------------------
PackageBuild Scores
-------------------

The `tag/scores` method will return a dictionary of tag : score items belonging to a given `packageName` given as argument. A `language` argument is also optional.
