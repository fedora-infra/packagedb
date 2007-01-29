<?python
layout_params['displayNotes']=False
?>
<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
  <a py:if="tg.paginate.current_page &gt; 1"
    href="${tg.paginate.get_href(1)}">&lt;&lt;</a>
  <a py:if="tg.paginate.current_page &gt; 1"
    href="${tg.paginate.get_href(tg.paginate.current_page - 1)}">&lt;</a>
  <span py:for="page in tg.paginate.pages">
    <a py:if="page != tg.paginate.current_page" href="${tg.paginate.get_href(page)}">${page}</a>
    <b py:if="page==tg.paginate.current_page">${page}</b>
  </span>
  <a py:if="tg.paginate.current_page &lt; tg.paginate.page_count"
    href="${tg.paginate.get_href(tg.paginate.current_page + 1)}">&gt;</a>
  <a py:if="tg.paginate.current_page &lt; tg.paginate.page_count"
    href="${tg.paginate.get_href(tg.paginate.page_count)}">&gt;&gt;</a>
  <ul py:for="pkg in packages">
  <li><a href="${tg.url('/packages/id/' + str(pkg.id))}"
    py:content="pkg.name"></a> --
    <span py:replace="pkg.summary">Package Summary</span></li>
  </ul>
  <p>At some point we will need to add these interface components:</p>
  <p>Search interface<br/>
  Search by [Criteria[v]]  Search for [______]  Regex [x]
  <p>
  Where Criteria == owner, interest, package name, etc
  </p>
  </p>

  <p>List of packages which match the search criteria<br/>
  `Package Name`_ Collection Owner Interest<br/>

  <p><a href="id">`Package Name`_</a> links to a page with information
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
