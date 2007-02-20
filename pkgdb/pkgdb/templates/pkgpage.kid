<?python
layout_params['displayNotes']=True
TODO='Not yet implemented'
?>
<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">
<div py:match="item.tag == 'content'">
  <script type='text/javascript'
    src="${tg.url('/static/javascript/framework.js')}"></script>
  <script type='text/javascript'
    src="${tg.url('/static/javascript/pkgpage.js')}"></script>
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
    <ul py:for="pkg in packageListings">
      <li><a py:attrs="{'href' : ''.join(
         ('#', pkg.collection.name, pkg.collection.version)).replace(' ','')}"
        py:content="' '.join((pkg.collection.name, pkg.collection.version))">
      </a></li>
    </ul>
  </p>
  <form action="${tg.url('/packages/dispatcher/')}" method="POST">
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
    <tr id="${''.join((pkg.collection.name, pkg.collection.version)).replace(' ','')}">
      <td><a href="${tg.url('/collections/id/' + str(pkg.collection.id))}"
        py:content="' '.join((pkg.collection.name, pkg.collection.version))"></a>
      </td><td>
        <div py:if="pkg.ownerid == 9900"
          py:attrs="{'name': str(pkg.id)}"
          class="requestContainer owner orphaned">
          <span class="ownerName">${pkg.ownername}</span>
        <span py:if="pkg.ownerid == 9900">
          <span py:if="'cvsextras' in tg.identity.groups and pkg.collection.statuscode.translations[0].statusname!='EOL'">
            <input type="button" name="unorphan"
              class="ownerButton unorphanButton"
              value="Take Ownership"></input>
          </span>
        </span>
        </div>
        <div py:if="pkg.ownerid != 9900"
          py:attrs="{'name': str(pkg.id)}"
          class="requestContainer owner owned">
          <span class="ownerName">${pkg.ownername}</span>
        <span py:if="not tg.identity.anonymous and tg.identity.user.user_id == pkg.ownerid">
          <input type="button" name="orphan"
            class="ownerButton orphanButton"
            value="Release Ownership"/>
        </span>
        </div>
      </td><td py:content="pkg.qacontactname">
      </td><td py:content="pkg.statuscode.translations[0].statusname">
      </td></tr>
<!-- Notes 
  If owner || approveacls, allow you to make changes to the ACLs
  -->
    <tr py:if="not tg.identity.anonymous or pkg.people" colspan="4"><td colspan="4">
      <table class="acl" width="100%">
        <tr>
          <th py:for="colName in ['User'] + list(aclNames)" py:content="colName">
          </th>
        </tr>
        <tr py:for="person in pkg.people.items()">
          <td py:content="person[1].name" class="aclcell">Name
          </td>
          <td py:for="acl in aclNames" class="aclcell">
            <!-- If the logged in user is this row, add a checkbox to set it -->
            <span py:if="not tg.identity.anonymous and person[0] == tg.identity.user.user_id">
            <input type="checkbox" py:attrs="{'value' : acl}" checked="checked"
              py:if="person[1].acls[acl]"/>
            <input type="checkbox" py:attrs="{'value' : acl}"
              py:if="not person[1].acls[acl]"/>
            </span>
            <!-- If the user can set acls, give drop downs for status -->
            <span py:if="not tg.identity.anonymous and (
              tg.identity.user.user_id==pkg.ownerid or
              (tg.identity.user.user_id in pkg.people and 
                pkg.people[tg.identity.user.user_id].acls['approveacls']=='Approved'))">
              <select py:attrs="{'name': acl}">
              <span py:for="status in aclStatus">
                <!-- FIXME: Have to mark where the acl is at.  If nothing is
                  set, then the acl must select blank.  Else, select the one
                  that's set. 
                  * Probably can do this by making the first acl in the list ""
                  -->
                <option selected="selected"
                  py:if="person[1].acls[acl]==status.translations[0].statusname"
                  py:content="status.translations[0].statusname"
                  py:attrs="{'value': 'aclStatus[status]',
                  'name': 'aclStatus[status]'}"></option>
                <option py:if="not person[1].acls[acl]==status.translations[0].statusname"
                  py:content="status.translations[0].statusname"
                  py:attrs="{'value': 'aclStatus[status]',
                  'name': 'aclStatus[status]'}"></option>
              </span>
              </select>
            </span>
            <span py:content="person[1].acls[acl]" class="aclcell"></span>
          </td>
        </tr>

        <tr py:if="not tg.identity.anonymous and
          tg.identity.user.user_id not in pkg.people">
          <td class="aclcell" py:attrs="{'colspan' : str(len(aclNames)+1)}">
            <input type="button" py:attrs="{'name':'add:' + str(pkg.package.id)
              + ':' + str(tg.identity.user.user_id)}"
              value="Add myself to package"/>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
  </form>
  <div id='Notes' py:if="layout_params['displayNotes']">
  <p>
    <ul>
      <li>If the user is an owner or has permission to change packagedb information they can edit all the mutable package information.</li>
      <li>Package name and EVR are immutable.  Status should eventually be immutable (set automatically).</li>
    </ul>
  </p>
  </div>
</div>
</html>
