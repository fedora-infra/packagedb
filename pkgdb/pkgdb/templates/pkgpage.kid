<?python
layout_params['displayNotes']=True
?>
<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
  <h1 py:content="package.name">Package</h1>
  <table border="0">
  <tr><td>
  Status
  </td><td py:content="package.statusname">
  </td></tr>
  <tr><td>
  Creation Date
  </td><td py:content="TODO">Fill in the Creation Date
  </td></tr>
  </table>
  <p py:content="package.summary">Summary</p>
  <p py:content="package.description">Description</p>

  <p>Contents:
  <ul py:for="pkg in packageListings">
    <!-- Misleading: This is actually the collection name and version -->
    <li><a href="${'#' + pkg.name + pkg.version}"
      py:content="pkg.name + ' ' + pkg.version"></a></li>
  </ul>
  <table border="1">
  <tr><th>
  Collection
  </th><th>
  Owner
  </th><th>
  QA Contact
  </th><th>
  Status
  </th></tr>
  </table>
  <table border="1" py:for="pkg in packageListings">
  <a name="${'#' + pkg.name + pkg.version}">
  <tr><td><a href="${tg.url('/collections/id/' + str(pkg.collectionid)}"
    py:content="pkg.name pkg.version"></a>
  </td><td py:content="pkg.owner">
  </td><td py:content="pkg.qacontact">
  </td><td py:content="pkg.statusname">
  </td></tr>
  </a>
  </table>
  <p>Contents: Package is in Collection
  <ul>
    <li>Collection1</li>
    <li>Collection2</li>
  </ul>
  </p>
  <p>
  Package - Collection1 - Status: [STATUS]
  <table border="2">
  <tr><td>
  Put information about the package collections here
  </td></tr>
  </table>
  Package - Collection2 - Status: [STATUS]
  <table border="2">
  <tr><td>
  Put information about the package collections here
  </td></tr>
  </table>
  <ul>
  <li>If the user is logged in, they can add themselves to the package.</li>
  <li>If the user is an owner or co-owner, they can edit all of the mutable package information</li>
  <li>Package name and EVR are immutable.  Status should eventually be immutable (set automatically).</li>
  </ul>
  </p>
</div>
</html>
