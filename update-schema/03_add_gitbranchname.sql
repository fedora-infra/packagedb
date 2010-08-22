ALTER TABLE branch ADD gitbranchname character varying(32) default NULL;

SELECT * FROM branch ORDER BY collectionid;

UPDATE branch
   SET gitbranchname = 'f13'
   WHERE branchname = 'F-13';

UPDATE branch
   SET gitbranchname = 'f12'
   WHERE branchname = 'F-12';

UPDATE branch
   SET gitbranchname = 'f11'
   WHERE branchname = 'F-11';

UPDATE branch
   SET gitbranchname = 'f10'
   WHERE branchname = 'F-10';

UPDATE branch
   SET gitbranchname = 'f9'
   WHERE branchname = 'F-9';

UPDATE branch
   SET gitbranchname = 'f8'
   WHERE branchname = 'F-8';

UPDATE branch
   SET gitbranchname = 'f7'
   WHERE branchname = 'F-7';

UPDATE branch
   SET gitbranchname = 'fc6'
   WHERE branchname = 'FC-6';

UPDATE branch
   SET gitbranchname = 'el6'
   WHERE branchname = 'EL-6';

UPDATE branch
   SET gitbranchname = 'el5'
   WHERE branchname = 'EL-5';

UPDATE branch
   SET gitbranchname = 'el4'
   WHERE branchname = 'EL-4';

UPDATE branch
   SET gitbranchname = 'olpc3'
   WHERE branchname = 'OLPC-3';

