<?python
layout_params['displayNotes']=False
?>
<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">

  <p>This should be a general overview of the Fedora Package Database.  The
  first incarnation will be develper-centric with administrative functions
  such as ownership information, ability to watch a package, sign up to be
  a comaintainer, etc.</p>
  <p>As we have time, we will add more end-user content like:
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

  <p>This front page should contain a broad overview of packages,and collections
  and how they relate to Fedora.
  </p>
  <ul>
  <li><a href="${tg.url('/collections/')}">View Packages by Collection</a></li>
  <li><a href="${tg.url('/packages/')}">Browse all Packages in the Database</a></li>
  </ul>
</div>
</html>
