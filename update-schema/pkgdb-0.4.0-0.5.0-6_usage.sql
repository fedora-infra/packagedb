CREATE TABLE usages (
        id SERIAL NOT NULL,
        name TEXT NOT NULL,
        PRIMARY KEY (id),
         UNIQUE (name)
);

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE usages TO pkgdbadmin;
GRANT SELECT, UPDATE ON usages_id_seq TO pkgdbadmin;

CREATE TABLE applicationsusages (
        applicationid INTEGER NOT NULL,
        usageid INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        author TEXT NOT NULL,
        PRIMARY KEY (applicationid, usageid, author),
         FOREIGN KEY(applicationid) REFERENCES applications (id) ON DELETE CASCADE ON UPDATE CASCADE,
         FOREIGN KEY(usageid) REFERENCES usages (id) ON DELETE CASCADE ON UPDATE CASCADE
);

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE applicationsusages TO pkgdbadmin;
