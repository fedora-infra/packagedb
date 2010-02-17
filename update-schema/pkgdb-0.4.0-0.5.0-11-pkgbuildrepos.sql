CREATE TABLE packagebuildrepos (
    repoid integer NOT NULL REFERENCES repos
                     ON DELETE CASCADE,
    packagebuildid integer NOT NULL REFERENCES packagebuild ON DELETE CASCADE
    );

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE packagebuildrepos TO pkgdbadmin;
GRANT SELECT ON packagebuildrepos TO pkgdbreadonly;

insert into packagebuildrepos (packagebuildid, repoid) select id, repoid from packagebuild;

alter table packagebuild drop column repoid;
