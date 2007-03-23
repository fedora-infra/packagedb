<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
<ul py:for="pkgName in pkgs.keys()">
<li><a href="${tg.url('/packages/name/' + pkgName)}" py:content="pkgName"></a>
-- ${pkgs[pkgName]}</li>
</ul>
</div>
</html>
