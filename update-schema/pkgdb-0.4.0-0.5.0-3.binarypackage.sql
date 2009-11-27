CREATE TABLE binarypackages(
    name text NOT NULL PRIMARY KEY
); 
GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE binarypackages TO pkgdbadmin;
GRANT SELECT ON binarypackages TO pkgdbreadonly;

CREATE TABLE binarypackagetags (
    binarypackagename text NOT NULL REFERENCES binarypackages
                     ON DELETE CASCADE,
    tagid int NOT NULL REFERENCES tags ON DELETE CASCADE,
    score int NOT NULL DEFAULT 1
    );
GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE binarypackagetags TO pkgdbadmin;
GRANT SELECT ON binarypackagetags TO pkgdbreadonly;

INSERT INTO binarypackages (name) SELECT DISTINCT name FROM packagebuild;

ALTER TABLE packagebuild ADD FOREIGN KEY (name) REFERENCES binarypackages;

-- updates score every time someone uses a tag/binarypackage combination
CREATE OR REPLACE FUNCTION binarypackagetags_score()
RETURNS trigger AS $binarypackagetags_score$
    DECLARE
        old_score integer;
    BEGIN
        SELECT score INTO old_score FROM binarypackagetags WHERE
            tagid = NEW.tagid AND binarypackagename = NEW.binarypackagename;
            
        IF NOT FOUND THEN
            RETURN NEW;
        ELSE
            UPDATE binarypackagetags SET tagid = NEW.tagid,
                                        binarypackagename = NEW.binarypackagename,
                                        score = old_score + 1
                                    WHERE tagid = NEW.tagid AND
                                          binarypackagename =NEW.binarypackagename;
            RETURN NULL;
        END IF;
    END;
$binarypackagetags_score$ LANGUAGE plpgsql;

CREATE TRIGGER binarypackagetags_score BEFORE INSERT ON binarypackagetags
    FOR EACH ROW EXECUTE PROCEDURE binarypackagetags_score();

