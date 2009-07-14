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

CREATE TABLE languages (
    name text NOT NULL,
    shortname text NOT NULL PRIMARY KEY
    );
GRANT ALL ON TABLE languages TO pkgdbadmin;    

CREATE TABLE tags (
    id serial NOT NULL PRIMARY KEY,
    name text NOT NULL,
    language text NOT NULL REFERENCES languages ON DELETE CASCADE,
    UNIQUE (name, language)
    );
GRANT ALL ON TABLE tags TO pkgdbadmin;
GRANT ALL ON tags_id_seq TO pkgdbadmin;

CREATE TABLE packagebuildtags (
    packagebuildid int NOT NULL REFERENCES packagebuild ON DELETE CASCADE,
    tagid int NOT NULL REFERENCES tags ON DELETE CASCADE,
    score int NOT NULL DEFAULT 1,
    PRIMARY KEY (packagebuildid, tagid)
    );
GRANT ALL ON TABLE packagebuildtags TO pkgdbadmin;

CREATE OR REPLACE FUNCTION packagebuildtags_score()
RETURNS trigger AS $packagebuildtags_score$
    DECLARE
        old_score integer;
    BEGIN
        SELECT score INTO old_score FROM packagebuildtags WHERE
            tagid = NEW.tagid AND packagebuildid = NEW.packagebuildid;
            
        IF NOT FOUND THEN
            RETURN NEW;
        ELSE
            UPDATE packagebuildtags SET tagid = NEW.tagid,
                                        packagebuildid = NEW.packagebuildid,
                                        score = old_score + 1
                                    WHERE tagid = NEW.tagid AND
                                          packagebuildid = NEW.packagebuildid;
            RETURN NULL;
        END IF;
    END;
$packagebuildtags_score$ LANGUAGE plpgsql;

CREATE TRIGGER packagebuildtags_score BEFORE INSERT ON packagebuildtags
    FOR EACH ROW EXECUTE PROCEDURE packagebuildtags_score();

-- Got these from Transifex: https://translate.fedoraproject.org/languages/
INSERT INTO languages VALUES('Afrikaans', 'af');
INSERT INTO languages VALUES('Albanian', 'sq');
INSERT INTO languages VALUES('Amharic', 'am');
INSERT INTO languages VALUES('Arabic', 'ar');
INSERT INTO languages VALUES('Armenian', 'hy');
INSERT INTO languages VALUES('Assamese', 'as');
INSERT INTO languages VALUES('Azerbaijani', 'az');
INSERT INTO languages VALUES('Balochi', 'bal');
INSERT INTO languages VALUES('Basque', 'eu');
INSERT INTO languages VALUES('Basque eu_ES', 'eu_ES');
INSERT INTO languages VALUES('Belarusian', 'be');
INSERT INTO languages VALUES('Belarusian Latin', 'be@latin');
INSERT INTO languages VALUES('Bengali', 'bn');
INSERT INTO languages VALUES('Bengali (India)', 'bn_IN');
INSERT INTO languages VALUES('Bosnian', 'bs');
INSERT INTO languages VALUES('Brazilian Portuguese', 'pt_BR');
INSERT INTO languages VALUES('British English', 'en_GB');
INSERT INTO languages VALUES('Bulgarian', 'bg');
INSERT INTO languages VALUES('Burmese', 'my');
INSERT INTO languages VALUES('Catalan', 'ca');
INSERT INTO languages VALUES('Chinese (Simplified)', 'zh_CN');
INSERT INTO languages VALUES('Chinese (Traditional)', 'zh_TW');
INSERT INTO languages VALUES('Croatian', 'hr');
INSERT INTO languages VALUES('Czech', 'cs');
INSERT INTO languages VALUES('Danish', 'da');
INSERT INTO languages VALUES('Dutch', 'nl');
INSERT INTO languages VALUES('Dzongkha', 'dz');
INSERT INTO languages VALUES('Estonian', 'et');
INSERT INTO languages VALUES('Finnish', 'fi');
INSERT INTO languages VALUES('French', 'fr');
INSERT INTO languages VALUES('Galician', 'gl');
INSERT INTO languages VALUES('Georgian', 'ka');
INSERT INTO languages VALUES('German', 'de');
INSERT INTO languages VALUES('Greek', 'el');
INSERT INTO languages VALUES('Gujarati', 'gu');
INSERT INTO languages VALUES('Hebrew', 'he');
INSERT INTO languages VALUES('Hindi', 'hi');
INSERT INTO languages VALUES('Hungarian', 'hu');
INSERT INTO languages VALUES('Icelandic', 'is');
INSERT INTO languages VALUES('Iloko', 'ilo');
INSERT INTO languages VALUES('Indonesian', 'id');
INSERT INTO languages VALUES('Italian', 'it');
INSERT INTO languages VALUES('Japanese', 'ja');
INSERT INTO languages VALUES('Kannada', 'kn');
INSERT INTO languages VALUES('Korean', 'ko');
INSERT INTO languages VALUES('Kurdish', 'ku');
INSERT INTO languages VALUES('Lao', 'lo');
INSERT INTO languages VALUES('Latvian', 'lv');
INSERT INTO languages VALUES('Lithuanian', 'lt');
INSERT INTO languages VALUES('Macedonian', 'mk');
INSERT INTO languages VALUES('Maithili', 'mai');
INSERT INTO languages VALUES('Malay', 'ms');
INSERT INTO languages VALUES('Malayalam', 'ml');
INSERT INTO languages VALUES('Marathi', 'mr');
INSERT INTO languages VALUES('Mongolian', 'mn');
INSERT INTO languages VALUES('Nepali', 'ne');
INSERT INTO languages VALUES('Northern Sotho', 'nso');
INSERT INTO languages VALUES('Norwegian', 'no');
INSERT INTO languages VALUES('Norwegian Bokmål', 'nb');
INSERT INTO languages VALUES('Norwegian Nynorsk', 'nn');
INSERT INTO languages VALUES('Oriya', 'or');
INSERT INTO languages VALUES('Persian', 'fa');
INSERT INTO languages VALUES('Polish', 'pl');
INSERT INTO languages VALUES('Portuguese', 'pt');
INSERT INTO languages VALUES('Punjabi', 'pa');
INSERT INTO languages VALUES('Romanian', 'ro');
INSERT INTO languages VALUES('Russian', 'ru');
INSERT INTO languages VALUES('Serbian', 'sr');
INSERT INTO languages VALUES('Serbian (Latin)', 'sr@latin');
INSERT INTO languages VALUES('Sinhala', 'si');
INSERT INTO languages VALUES('Slovak', 'sk');
INSERT INTO languages VALUES('Slovenian', 'sl');
INSERT INTO languages VALUES('Spanish', 'es');
INSERT INTO languages VALUES('Swedish', 'sv');
INSERT INTO languages VALUES('Swiss German', 'de_CH');
INSERT INTO languages VALUES('Tagalog', 'tl');
INSERT INTO languages VALUES('Tajik', 'tg');
INSERT INTO languages VALUES('Tamil', 'ta');
INSERT INTO languages VALUES('Telugu', 'te');
INSERT INTO languages VALUES('Thai', 'th');
INSERT INTO languages VALUES('Turkish', 'tr');
INSERT INTO languages VALUES('Ukrainian', 'uk');
INSERT INTO languages VALUES('Urdu', 'ur');
INSERT INTO languages VALUES('Vietnamese', 'vi');
INSERT INTO languages VALUES('Welsh', 'cy');
INSERT INTO languages VALUES('Zulu', 'zu');
-- Also add American English:
INSERT INTO languages VALUES('American English', 'en_US');

