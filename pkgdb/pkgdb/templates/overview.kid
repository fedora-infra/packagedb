<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">

<h1>Fedora Package Database -- Version 0.2.90.1</h1>

<h2>Overview</h2>
<p>The Package Database is a central repository of package information in
Fedora.  You will eventually be able to find and change all the metainformation
about a package by searching the database.  The current implementation is
focused on the data that package developers and release engineers need to
create packages and spin them into a distribution.
</p>

<h2>Browse Packages</h2>
  <ul>
  <li><a href="${tg.url('/collections/')}">View Packages by Collection</a></li>
  <li><a href="${tg.url('/packages/')}">Browse all Packages in the Database</a></li>
  </ul>

<h2>News</h2>
<h3>0.2.90.1</h3>
<ul>
<li>URL scheme that uses package name</li>
<li>Minor template tweaks</li>
</ul>

<h3>0.2.90.0</h3>
<ul>
<li>Log changes to package meta-information in the database [0.3]</li>
<li>Notification of acl/owner changes send to extras-commits-list</li>
</ul>
<h3>0.2</h3>
<ul>
<li>Sign up to watch or comaintain packages</li>
<li>If you are a maintainer or co-maintainer, approve privileges for other people and groups.</li>
<li>You can now log in to the database using your Fedora Account System Username
and Password</li>
<li>While logged in, you can take ownership of orphaned packages or orphan
packages that you own</li>
</ul>
<p>
At this point the user interface should be a full replacement for owners.list
and pkg.acl.  The backend that takes data from the database and applies it to
cvs is not yet complete.
</p>

<h2>Plans</h2>
<h3>Before Go Live</h3>
<ul>
<li>Within the web app
<ul>
<li>Notification of acl changes: owner, and approveacl group.  Notification of owner changes to everyone with acls on that package[0.3]</li>
<li>Notification that people have requested acls: package owner and people on approveacls</li>
</ul>
</li>
<li>External scripts
<ul>
<li>Current sync of owners.list/owners.epel.list: Have to update slightly to
account for the new owners.list format</li>
<li>How to add a new package, branch scripts, etc:  Must be done
pre-cvs-import so we should tie this
into dgilmore's scripts on cvs-int.  This can be enabled concurrently to the
current entering into owners.list.</li>
<li>Output entries to bugzilla</li>
<li>Sync to Package ACLs</li>
<li>Output ACLs to the system</li>
</ul>
</li>
</ul>
<h3>Urgent</h3>
<ul>
<li>Give cvsadmin group admin permissions on the packagedb</li>
</ul>
<h3>Future</h3>
<ul>
<li>Autoapproval of watchbugzilla and watchcommits ACLs</li>
<li>Have a interface for reviewing changes on the PackageDB. (When and by whom
were ACLs changed, when were the Collections added to the system, etc.)</li>
<li>View packages by owner</li>
<li>Full UI for managing groups in ACLs.</li>
<li>Expand what sponsors can do.</li>
<li>Modify tg_paginate to display entries alphabetically instead of as pages
of 100 entries</li>
<li>Tie into koji for build ACLs</li>
<li>Make branch requests through the pkgdb.  Some requests are automatically
approved and changes made to cvs, others are sent to cvsadmins for approval.</li>
<li>Restore the ability for contributors to import new packages into the tree after approval.</li>
<li>Add License information to the Database.  Initially this will be the same
as the spec file tag.  Later it will tie into a License DB.  Talk to Tom
Callaway (spot) for further details</li>
</ul>

<h2 id="notes">Notes</h2>
  <p>Version 0.3 will satisfy all the must haves for the "go live" date.</p>
  <p>Version 0.4 will hit low hanging fruit in the future page</p>
  <p>As we have time, we may add more end-user content like:
  <ul>
    <li>
    <a href="http://fedoraproject.org/extras/6/i386/repodata/">Fedora Extras
    Repoview</a>
    </li>
    <li>
    <a href="http://packages.gentoo.org">Gentoo's Package Database</a>
    </li>
    <li>
    <a href="http://www.debian.org/distrib/packages">Debian's Package
    Database</a>
    </li>
  </ul>
  </p>

  <p>The tentative plan is to have one interface for searching for packages.
  If the user is logged in, they have access to more information and have the
  ability to make changes to the database.
  </p>
  <p>More complete plans for moving forward are available in the
  <a href="http://www.fedoraproject.org/wiki/Infrastructure/PackageDatabase/RoadMap">README</a>.</p>
</div>
</html>
