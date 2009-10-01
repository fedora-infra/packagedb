CREATE TABLE apptypes (
    apptype varchar(32) NOT NULL PRIMARY KEY
    );
INSERT INTO apptypes (apptype) VALUES ('desktop');
INSERT INTO apptypes (apptype) VALUES ('unknown');
INSERT INTO apptypes (apptype) VALUES ('commandline');

GRANT ALL ON TABLE apptypes TO pkgdbadmin;

CREATE TABLE applications (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL,
    description text NOT NULL,
    url text,
    apptype varchar(32) NOT NULL REFERENCES apptypes
            ON UPDATE CASCADE,
    desktoptype text
    );
    
GRANT ALL ON TABLE applications TO pkgdbadmin;
GRANT ALL ON applications_id_seq TO pkgdbadmin;


CREATE TABLE packagebuildapplications (
    applicationid integer NOT NULL REFERENCES applications
                     ON DELETE CASCADE,
    packagebuildid integer NOT NULL REFERENCES packagebuild ON DELETE CASCADE
    );

GRANT ALL ON packagebuildapplications TO pkgdbadmin;

-- packagebuild updates
GRANT ALL ON TABLE packagebuild TO pkgdbadmin;
DELETE FROM packagebuild;
ALTER TABLE packagebuild DROP COLUMN desktop;
ALTER TABLE packagebuild DROP CONSTRAINT packagebuild_name_fkey;

-- applicationstags
CREATE TABLE applicationstags (
    applicationid integer NOT NULL REFERENCES applications
                     ON DELETE CASCADE,
    tagid int NOT NULL REFERENCES tags ON DELETE CASCADE,
    score int NOT NULL DEFAULT 1
    );
GRANT ALL ON applicationstags TO pkgdbadmin;

DROP TABLE packagebuildnamestags;

-- comments
DELETE FROM comments;
ALTER TABLE comments DROP COLUMN packagebuildname;
ALTER TABLE comments ADD applicationid integer NOT NULL REFERENCES applications ON DELETE CASCADE ON UPDATE CASCADE;


DROP TABLE packagebuildnames ;

-- updates score every time someone uses a tag/application combination
CREATE OR REPLACE FUNCTION applicationstags_score()
RETURNS trigger AS $applicationstags_score$
    DECLARE
        old_score integer;
    BEGIN
        SELECT score INTO old_score FROM applicationstags WHERE
            tagid = NEW.tagid AND applicationid = NEW.applicationid;
            
        IF NOT FOUND THEN
            RETURN NEW;
        ELSE
            UPDATE applicationstags SET tagid = NEW.tagid,
                                        applicationid = NEW.applicationid,
                                        score = old_score + 1
                                    WHERE tagid = NEW.tagid AND
                                          applicationid =NEW.applicationid;
            RETURN NULL;
        END IF;
    END;
$applicationstags_score$ LANGUAGE plpgsql;

CREATE TRIGGER applicationstags_score BEFORE INSERT ON applicationstags
    FOR EACH ROW EXECUTE PROCEDURE applicationstags_score();

DROP FUNCTION packagebuildnamestags_score();

ALTER TABLE packagebuild DROP CONSTRAINT packagebuild_uniques;
ALTER TABLE packagebuild ADD CONSTRAINT packagebuild_uniques UNIQUE (name, packageid, epoch, architecture, version, release, repoid);
