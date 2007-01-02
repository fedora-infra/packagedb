<?python
layout_params['displayNotes']=False
?>
<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
<h1 py:content='title'>Error Title</h1>
<p py:content='msg'>Error message</p>
</div>
</html>
