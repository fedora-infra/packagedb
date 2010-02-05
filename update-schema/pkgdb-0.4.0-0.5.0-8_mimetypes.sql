CREATE TABLE mimetypes (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL UNIQUE
);                      

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE mimetypes TO pkgdbadmin;
GRANT SELECT, UPDATE ON mimetypes_id_seq TO pkgdbadmin;
GRANT SELECT ON mimetypes TO pkgdbreadonly;
GRANT SELECT, UPDATE ON mimetypes_id_seq TO pkgdbreadonly;


CREATE TABLE appsmimetypes (
    applicationid integer NOT NULL REFERENCES applications
                     ON DELETE CASCADE,
    mimetypeid integer NOT NULL REFERENCES mimetypes ON DELETE CASCADE
    );

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE appsmimetypes TO pkgdbadmin;
GRANT SELECT ON appsmimetypes TO pkgdbreadonly;


