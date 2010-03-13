-- Deactivate syncing for any repo that is currently inactive
update repos set active = false where collectionid in (select id from collection where statuscode = 9);
update repos set active = false where name like '%Debug';
