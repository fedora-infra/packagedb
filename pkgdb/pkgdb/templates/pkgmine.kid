<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
<span py:for="page in tg.paginate.pages">
    <a py:if="page != tg.paginate.current_page"
        href="${tg.paginate.get_href(page)}">${page}</a>
    <b py:if="page == tg.paginate.current_page">${page}</b>
</span>
<p>N.B. Multiple listings for the same package is a known bug that we hope to fix soon.</p>
<ul py:for="package in pkgs">
 <li><a href="${tg.url('/packages/name/' + package.package.name)}"
    py:content="package.package.name"></a> --
    <span py:replace="package.package.summary">Package Summary</span></li>
</ul>
</div>
</html>
