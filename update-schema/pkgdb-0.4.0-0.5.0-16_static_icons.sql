CREATE TABLE mediastatuses(
    id integer PRIMARY KEY,
    name text NOT NULL
); 

INSERT INTO mediastatuses VALUES (0, 'NEW');
INSERT INTO mediastatuses VALUES (1, 'EXPORTED');
INSERT INTO mediastatuses VALUES (2, 'SYNCED');

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE mediastatuses TO pkgdbadmin;
GRANT SELECT ON mediastatuses TO pkgdbreadonly;

ALTER TABLE icons ADD mstatusid integer NOT NULL default 0;
ALTER TABLE icons
    ADD CONSTRAINT icons_mstatusid_fkey FOREIGN KEY (mstatusid) REFERENCES mediastatuses(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE iconnames ADD mstatusid integer NOT NULL default 0;
ALTER TABLE iconnames
    ADD CONSTRAINT iconnames_mstatusid_fkey FOREIGN KEY (mstatusid) REFERENCES mediastatuses(id) ON UPDATE CASCADE ON DELETE CASCADE;



