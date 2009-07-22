ALTER TABLE package ADD COLUMN upstreamurl text;

ALTER TABLE packagebuild ADD COLUMN name text NOT NULL;
ALTER TABLE packagebuild ADD COLUMN license text NOT NULL;
ALTER TABLE packagebuild ADD COLUMN architecture text NOT NULL;
ALTER TABLE packagebuild ADD COLUMN desktop boolean NOT NULL;
ALTER TABLE packagebuild ADD COLUMN size int NOT NULL;
ALTER TABLE packagebuild ADD COLUMN repoid int NOT NULL
    REFERENCES repos ON DELETE CASCADE;
ALTER TABLE packagebuild ADD COLUMN changelog text NOT NULL;
ALTER TABLE packagebuild DROP COLUMN statuscode;
ALTER TABLE packagebuild ADD COLUMN committime timestamp with time zone NOT NULL;
ALTER TABLE packagebuild ADD COLUMN committer text NOT NULL;

ALTER TABLE packagebuild DROP CONSTRAINT packagebuild_packageid_key;
ALTER TABLE packagebuild ADD CONSTRAINT packagebuild_uniques
    UNIQUE(name, packageid, epoch, architecture, version, release);

ALTER TABLE packagelisting ADD COLUMN specfile text;

CREATE TABLE packagebuilddepends (
    packagebuildid int NOT NULL REFERENCES packagebuild ON DELETE CASCADE,
    packagebuildname text NOT NULL,
    PRIMARY KEY (packagebuildid, packagebuildname)
    );
GRANT ALL ON packagebuilddepends TO pkgdbadmin;

CREATE TABLE repos (
    id serial NOT NULL PRIMARY KEY,
    shortname text NOT NULL,
    name text NOT NULL,
    failovermethod text NOT NULL,
    collectionid integer REFERENCES collection ON DELETE CASCADE
);
GRANT ALL ON repos TO pkgdbadmin;
    
CREATE TABLE rpmprovides (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL,
    flags text,
    epoch text,
    version text,
    release text,
    packagebuildid integer REFERENCES packagebuild ON DELETE CASCADE
    );
GRANT ALL ON rpmprovides TO pkgdbadmin;
GRANT ALL ON rpmprovides_id_seq TO pkgdbadmin;


CREATE TABLE rpmrequires (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL,
    flags text,
    epoch text,
    version text,
    release text,
    packagebuildid integer NOT NULL REFERENCES packagebuild ON DELETE CASCADE,
    prereq boolean NOT NULL DEFAULT FALSE
    );
GRANT ALL ON TABLE rpmrequires TO pkgdbadmin;
GRANT ALL ON rpmrequires_id_seq TO pkgdbadmin;

CREATE TABLE rpmobsoletes (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL,
    flags text,
    epoch text,
    version text,
    release text,
    packagebuildid integer NOT NULL REFERENCES packagebuild ON DELETE CASCADE
    );
GRANT ALL ON rpmobsoletes TO pkgdbadmin;
GRANT ALL ON rpmobsoletes_id_seq TO pkgdbadmin;

CREATE TABLE rpmconflicts (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL,
    flags text,
    epoch text,
    version text,
    release text,
    packagebuildid integer NOT NULL REFERENCES packagebuild ON DELETE CASCADE
    );
GRANT ALL ON rpmconflicts TO pkgdbadmin;
GRANT ALL ON rpmconflicts_id_seq TO pkgdbadmin;

CREATE TABLE rpmfiles (
    name text NOT NULL,
    packagebuildid integer NOT NULL REFERENCES packagebuild ON DELETE CASCADE,
    PRIMARY KEY(name, packagebuildid)
    );
GRANT ALL ON rpmfiles TO pkgdbadmin;
GRANT ALL ON rpmfiles_id_seq TO pkgdbadmin;

ALTER TABLE packagebuild ADD FOREIGN KEY (repoid) REFERENCES repos;


