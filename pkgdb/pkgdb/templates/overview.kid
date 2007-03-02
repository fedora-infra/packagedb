<?python
layout_params['displayNotes']=False
?>
<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">

<h1>Fedora Package Database -- Version 0.1.92</h1>
<h2>News</h2>
<h3>0.91.2</h3>
<ul>
<li>If you are a maintainer or co-maintainer, approve privileges for other people.</li>
</ul>
<h3>0.91.1</h3>
<ul>
<li>You can now log in to the database using your Fedora Account System Username
and Password</li>
<li>While logged in, you can take ownership of orphaned packages or orphan
packages that you own</li>
<li>Sign up to watch or comaintain packages</li>
</ul>

<h2>Before Go Live</h2>
<ul>
<li>Within the web app
<ul>
<li>Ability to add or subtract cvsextras access to your package: This will be
a general group feature later.  For now we just need cvsextras +/- to match
the present ACL system. <strong>(*) This is the last feature before 0.2</strong></li>
<li>Notification that people have requested acls: package owner and people on approveacls</li>
<li>Notification of owner changes:  cvsadmin group?</li>
<li>Hide checkout and build perms</li>
</ul>
</li>
<li>External scripts
<ul>
<li>How to add a new package:  Must be done pre-cvs-import so we should tie this
into dgilmore's scripts on cvs-int.</li>
<li>Current sync of owners.list/owners.epel.list: Have to update slightly to
account for the new owners.list format</li>
<li>Sync to Package ACLs</li>
<li>Output ACLs to the system</li>
<li>Output entries to bugzilla</li>
</ul>
</li>
</ul>

<h2>Future</h2>
<ul>
<li>View packages by owner</li>
<li>Full UI for managing groups in ACLs.</li>
<li>URL scheme that uses package name</li>
<li>Give cvsadmin group admin permissions on the packagedb</li>
<li>Later, expand that to sponsor roles, etc</li>
<li>Modify tg_paginate to display entries alphabetically instead of as pages
of 100 entries</li>
<li>Tie into koji for build ACLs</li>
</ul>

<h2>Overview</h2>
<p>The Package Database is a central repository of package information in
Fedora.  You will eventually be able to find ad change all the metainformation
about a package by searching the database.  The current implementation is
focused on the data that package developers and release engineers need to
create packages and spin them into a distribution.
</p>
<h2>Browse Packages</h2>
  <ul>
  <li><a href="${tg.url('/collections/')}">View Packages by Collection</a></li>
  <li><a href="${tg.url('/packages/')}">Browse all Packages in the Database</a></li>
  </ul>

<h2 id="notes">Notes</h2>
  <p>Version 0.1 is a read-only interface to the information that was stored in
  owners.list and the Fedora cvs archive.
  </p>
  <p>Version 0.2 will add the ability to make changes to the acl information
  stored in the database.
  </p>
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
  If the user is logged in, they have access ot more information and have the
  ability to make changes to the database.
  </p>
  <p>More complete plans for moving forward are available in the
  <a href="http://www.fedoraproject.org/wiki/Infrastructure/PackageDatabase/RoadMap">README</a>.</p>
</div>
</html>
