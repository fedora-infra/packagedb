<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
  <table border="1">
    <tr py:for="collection in sorted(bugzillaAcls.keys())">
      <td py:content="collection"></td>
      <span py:for="package in sorted(bugzillaAcls[collection].keys())">
        <td><b>${package}</b></td>
        <td>${bugzillaAcls[collection][package].owner}</td>
        <td>${bugzillaAcls[collection][package].qacontact}</td>
        <td>${bugzillaAcls[collection][package].summary}</td>
        <td>
        <span py:for="person in bugzillaAcls[collection][package].cclist" py:replace="person + ' '"></span><br/>
        </td>
      </span>
    </tr>
  </table>
</div>
</html>
