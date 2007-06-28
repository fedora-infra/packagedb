<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
<p>View users: <a href="${tg.url('/users/info/' + fasname)}">Info</a> | <a href="${tg.url('/users/packages/' + fasname)}">Packages</a> | <a href="${tg.url('/users/acllist/' + fasname)}">ACL Listings</a></p>
<p></p>
<span py:for="page in tg.paginate.pages">
    <a py:if="page != tg.paginate.current_page"
        href="${tg.paginate.get_href(page)}">${page}</a>
    <b py:if="page == tg.paginate.current_page">${page}</b>
</span>
<p></p>
<ul py:for="package in pkgs">
 <li><a href="${tg.url('/packages/name/' + package.name)}"
    py:content="package.name"></a> --
    <span py:replace="package.summary">Package Summary</span></li>
</ul>
</div>
</html>
