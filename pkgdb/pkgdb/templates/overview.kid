<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">

<h1>Fedora Package Database -- Version 0.3</h1>

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

  For more information on the packagedb, see it's
  <a href="http://hosted.fedoraproject.org/projects/packagedb">Project Page</a>.
</div>
</html>
