ALTER TABLE package ADD COLUMN upstreamurl text NOT NULL;

ALTER TABLE packagebuild ADD COLUMN name text NOT NULL;
ALTER TABLE packagebuild ADD COLUMN license text NOT NULL;
ALTER TABLE packagebuild ADD COLUMN architecture text NOT NULL;
ALTER TABLE packagebuild ADD COLUMN desktop boolean NOT NULL;
ALTER TABLE packagebuild ADD COLUMN size int NOT NULL;
ALTER TABLE packagebuild ADD COLUMN repoid int NOT NULL;
ALTER TABLE packagebuild ADD COLUMN changelog text NOT NULL;
ALTER TABLE packagebuild DROP COLUMN statuscode;
ALTER TABLE packagebuild ADD COLUMN timestamp timestamp with timezone NOT NULL;
ALTER TABLE packagebuild ADD COLUMN committer text NOT NULL;

ALTER TABLE packagebuild DROP CONSTRAINT packagebuild_packageid_key;
ALTER TABLE packagebuild ADD CONSTRAINT packagebuild_uniques UNIQUE(name, packageid, epoch, architecture, version, release);

ALTER TABLE packagelisting ADD COLUMN specfile text;

CREATE TABLE repos (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL,
    failovermethod text NOT NULL,
    collectionid integer REFERENCES collections
)
    
CREATE TABLE rpmprovides (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL,
    flags text,
    epoch text,
    version text,
    release text,
    packagebuildid integer REFERENCES packagebuild ON DELETE CASCADE,
    );

CREATE TABLE rpmrequires (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL,
    flags text,
    epoch text,
    version text,
    release text,
    packagebuildid integer NOT NULL REFERENCES packagebuild ON DELETE CASCADE,
    prereq boolean NOT NULL DEFAULT FALSE,
    );

CREATE TABLE rpmobsoletes (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL,
    flags text,
    epoch text,
    version text,
    release text,
    packagebuildid integer NOT NULL REFERENCES packagebuild ON DELETE CASCADE,
    );

CREATE TABLE rpmconflicts (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL,
    flags text,
    epoch text,
    version text,
    release text,
    packagebuildid integer NOT NULL REFERENCES packagebuild ON DELETE CASCADE,
    );

CREATE TABLE rpmfiles (
    name text NOT NULL,
    packagebuildid integer NOT NULL REFERENCES packagebuild ON DELETE CASCADE,
    PRIMARY KEY(name, packagebuildid)
    );

ALTER TABLE packagebuild ADD FOREIGN KEY (repoid) REFERENCES repos;

INSERT INTO repos (name, failovermethod, collectionid) VALUES
('Fedora 11 - i386', 'priority', 21),
('Fedora 11 - i386 - Updates', 'priority', 21),
('Fedora 11 - i386 - Testing Updates', 'priority', 21),

;
