<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
  <table border="1">
    <tr py:for="pkg in sorted(packageAcls.keys())">
      <td py:content="pkg"></td>
      <span py:for="branch in sorted(packageAcls[pkg].keys())">
        <td><b>${branch}</b><br/>
        <span py:for="person in packageAcls[pkg][branch]['commit'].people" py:replace="person + ' '"></span><br/>
        <span py:for="group in packageAcls[pkg][branch]['commit'].groups" py:replace="group + ' '"></span>
        </td>
      </span>
    </tr>
  </table>
</div>
</html>
