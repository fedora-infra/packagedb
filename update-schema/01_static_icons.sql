CREATE TABLE media_status(
    id integer PRIMARY KEY,
    name text NOT NULL
); 

INSERT INTO media_status VALUES (0, 'NEW');
INSERT INTO media_status VALUES (1, 'EXPORTED');
INSERT INTO media_status VALUES (2, 'SYNCED');

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE media_status TO pkgdbadmin;
GRANT SELECT ON media_status TO pkgdbreadonly;

ALTER TABLE icons ADD m_status_id integer NOT NULL default 0;
ALTER TABLE icons
    ADD CONSTRAINT icons_m_status_id_fkey FOREIGN KEY (m_status_id) REFERENCES media_status(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE applications ADD icon_status_id integer NOT NULL default 0;
ALTER TABLE applications
    ADD CONSTRAINT applications_icon_status_id_fkey FOREIGN KEY (icon_status_id) REFERENCES media_status(id) ON UPDATE CASCADE ON DELETE CASCADE;



