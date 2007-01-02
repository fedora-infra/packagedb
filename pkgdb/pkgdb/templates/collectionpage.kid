<?python
layout_params['displayNotes']=True
?>
<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#"
  py:layout="'layout.kid'">

<div py:match="item.tag == 'content'">
  <h1 py:content="collection.name, ' ',  collection.version">Collection</h1>
  <p>Each collection page should have information about the Collection.
  <ul>
  <li>Date it was created</li>
  <li>Status (Is it active or EOL)</li>
  </ul>
  And it should have links to packages.  For the first cut we'll just have an
  alphabetical listing with [a-z] links at the top (and view all packages).
  In the future, we'll want
  to have most recent packages listed on this page.  And a full range of search
  functions.  Thinking about it this way, the Collections view is really a
  Package view limited by Collection.
  </p>
</div>
</html>
