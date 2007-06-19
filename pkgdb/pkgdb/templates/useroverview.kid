<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">

    <p>Nothing to see here yet, however take a look at <a href="${tg.url('/users/packages/')}">your packages</a> or <a href="${tg.url('/users/acllist/')}">your ACL entries</a></p>
</div>
</html>
