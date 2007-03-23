<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
  <h1>Collections</h1>
    <table>
    <tr><th>
    Collection
    </th><th>
    Version
    </th><th>
    Number of Packages
    </th></tr>
    <tr py:for="collection in collections">
      <td>
      <a href="${tg.url('/collections/id/' + str(collection.id))}"
        py:content="collection.name">Collection Name</a>
      </td>
      <td>
      <a href="${tg.url('/collections/id/' + str(collection.id))}"
        py:content="collection.version">Collection Version</a>
      </td>
      <td>
      <a href="${tg.url('/collections/id/' + str(collection.id))}"
        py:content="collection.numpkgs">Number of Packages</a>
      </td>
    </tr>
    </table>
</div>
</html>
