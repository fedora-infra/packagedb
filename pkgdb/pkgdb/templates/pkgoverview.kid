<?python
layout_params['displayNotes']=False
?>
<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
  <p>Search interface<br/>
  Search by [Criteria[v]]  Search for [______]  Regex [x]
  <p>
  Where Criteria == owner, interest, package name, etc
  </p>
  </p>

  <p>List of packages which match the search criteria<br/>
  `Package Name`_ Collection Owner Interest<br/>

  <p><a href="pkgdb/pkgpage">`Package Name`_</a> links to a page with information
  about the package.
  </p>
  </p>

  <p>Add to side bar: Package Stats</p>
  <ul>
    <li>Number of packages</li>
    <li>Number of packages in collections</li>
  </ul>

</div>
</html>
