<?python
layout_params['displayNotes']=True
?>
<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
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
