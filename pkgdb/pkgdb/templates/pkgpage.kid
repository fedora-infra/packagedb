<?python
layout_params['displayNotes']=True
TODO='Not yet implemented'
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
    </td><td py:content="TODO">
      Fill in the Creation Date
    </td></tr>
  </table>
  <p py:content="package.summary">Summary</p>
  <p py:content="package.description">Description</p>

  <p>Contents:
    <!-- Slightly misleading: this is actually the collection name and
         version, not the package name and version
      -->
    <ul py:for="pkg in packageListings">
      <li><a py:attrs="{'href' : ''.join(
         ('#', pkg.name, pkg.version)).replace(' ','')}"
        py:content="' '.join((pkg.name, pkg.version))">
      </a></li>
    </ul>
  </p>
  <table class="pkglist" py:for="pkg in packageListings">
    <tr><th>
      Collection
    </th><th>
      Owner
    </th><th>
      QA Contact
    </th><th>
      Status
    </th></tr>
    <tr id="${''.join((pkg.name, pkg.version)).replace(' ','')}">
      <td><a href="${tg.url('/collections/id/' + str(pkg.collectionid))}"
        py:content="' '.join((pkg.name, pkg.version))"></a>
      </td><td py:content="pkg.ownername">
      </td><td py:content="pkg.qacontactname">
      </td><td py:content="pkg.statusname">
      </td></tr>
    <tr py:if="pkg.people" colspan="4"><td colspan="4">
      <table class="acl" width="100%">
        <tr>
          <th py:for="colName in ['User'] + list(aclNames)" py:content="colName">
          </th>
        </tr>
        <tr py:for="person in pkg.people.values()">
          <td py:content="person.name" class="aclcell">Name
          </td>
          <span py:for="acl in aclNames">
            <td py:content="person.acls[acl]" class="aclcell"></td>
          </span>
        </tr>
      </table>
    </td></tr>
  </table>
  <div id='Notes' py:if="layout_params['displayNotes']">
  <p>
    <ul>
      <li>If the user is logged in, they can add themselves to the package.</li>
      <li>If the user is an owner or has permission to change packagedb information they can edit all the mutable package information.</li>
      <li>Package name and EVR are immutable.  Status should eventually be immutable (set automatically).</li>
    </ul>
  </p>
  </div>
</div>
</html>
