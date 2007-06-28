<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
<p>View users: <a href="${tg.url('/users/info/' + fasname)}">Info</a> | <a href="${tg.url('/users/packages/' + fasname)}">Packages</a> | <a href="${tg.url('/users/acllist/' + fasname)}">ACL Listings</a></p>
<p></p>
<p>Nothing else of interest yet!</p>
</div>
</html>
