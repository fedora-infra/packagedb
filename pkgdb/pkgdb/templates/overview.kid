<?python
layout_params['displayNotes']=False
?>
<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">

<h1>Fedora Package Database -- Version 0.1.91</h1>
<h2>News</h2>
<ul>
<li>You can now log in to the database using your Fedora Account System Username
and Password</li>
<li>While logged in, you can take ownership of orphaned packages or orphan
packages that you own</li>
<li>Sign up to watch or comaintain packages</li>
</ul>

<h2>Soon</h2>
<ul>
<li>If you are a maintainer or co-maintainer, approve privileges for other people.</li>
</ul>
<h2>ASAP</h2>
<ul>
<li>Tie the information in the database into what actually exists on the system.
</li>
<li>Make sure we import everything important from owners.list and cvs:
<ul>
<li>Current sync of owners.list/owners.epel.list</li>
<li>Package ACLs</li>
</ul>
</li>
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
  <p>Version 0.1 is a read-only interface tothe information that was stored in
  owners.list and the Fedora cvs archive.
  </p>
  <p>Version 0.2 plans to add the ability ot make changes to the acl information
  stored in the database.
  </p>
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
