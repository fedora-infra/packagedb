<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
  <table border="1" py:for="collection in sorted(bugzillaAcls.keys())">
    <thead><td>Package</td><td>Description</td><td>Owner</td><td>Initial QA</td><td>Initial CCList</td></thead>
    <tr><th py:content="collection" colspan="5"></th></tr>
    <tr py:for="package in sorted(bugzillaAcls[collection].keys())">
      <td><b>${package}</b></td>
      <td>${bugzillaAcls[collection][package].summary}</td>
      <td>${bugzillaAcls[collection][package].owner}</td>
      <td>${bugzillaAcls[collection][package].qacontact}</td>
      <td>
      <span py:for="person in bugzillaAcls[collection][package].cclist.people" py:replace="person + ' '"></span><br/>
      </td>
    </tr>
  </table>
</div>
</html>
