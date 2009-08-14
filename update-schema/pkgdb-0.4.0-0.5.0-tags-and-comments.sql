CREATE TABLE languages (
    name text NOT NULL,
    shortname text NOT NULL PRIMARY KEY,
    UNIQUE (name)
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

CREATE TABLE packagebuildnamestags (
    packagebuildname text NOT NULL REFERENCES packagebuildnames
                     ON DELETE CASCADE,
    tagid int NOT NULL REFERENCES tags ON DELETE CASCADE,
    score int NOT NULL DEFAULT 1,
    PRIMARY KEY (packagebuildname, tagid)
    );
GRANT ALL ON packagebuildnamestags TO pkgdbadmin;

-- updates score every time someone uses a tag/build combination
CREATE OR REPLACE FUNCTION packagebuildnamestags_score()
RETURNS trigger AS $packagebuildnamestags_score$
    DECLARE
        old_score integer;
    BEGIN
        SELECT score INTO old_score FROM packagebuildnamestags WHERE
            tagid = NEW.tagid AND packagebuildname = NEW.packagebuildname;
            
        IF NOT FOUND THEN
            RETURN NEW;
        ELSE
            UPDATE packagebuildnamestags SET tagid = NEW.tagid,
                                        packagebuildname = NEW.packagebuildname,
                                        score = old_score + 1
                                    WHERE tagid = NEW.tagid AND
                                          packagebuildname =NEW.packagebuildname;
            RETURN NULL;
        END IF;
    END;
$packagebuildnamestags_score$ LANGUAGE plpgsql;

CREATE TRIGGER packagebuildnamestags_score BEFORE INSERT ON packagebuildnamestags
    FOR EACH ROW EXECUTE PROCEDURE packagebuildnamestags_score();

CREATE TABLE comments (
       id serial NOT NULL PRIMARY KEY,
       author text NOT NULL,
       body text NOT NULL,
       published boolean NOT NULL DEFAULT TRUE,
       packagebuildname text NOT NULL REFERENCES packagebuildnames
                        ON DELETE CASCADE,
       language text NOT NULL REFERENCES languages ON DELETE CASCADE,
       time timestamp with time zone NOT NULL DEFAULT now()
       );
GRANT ALL ON comments TO pkgdbadmin;
GRANT ALL ON comments_id_seq TO pkgdbadmin;

-- Got these from Transifex: https://translate.fedoraproject.org/languages/
INSERT INTO languages (name, shortname) VALUES('Afrikaans', 'af');
INSERT INTO languages (name, shortname) VALUES('Albanian', 'sq');
INSERT INTO languages (name, shortname) VALUES('Amharic', 'am');
INSERT INTO languages (name, shortname) VALUES('Arabic', 'ar');
INSERT INTO languages (name, shortname) VALUES('Armenian', 'hy');
INSERT INTO languages (name, shortname) VALUES('Assamese', 'as');
INSERT INTO languages (name, shortname) VALUES('Azerbaijani', 'az');
INSERT INTO languages (name, shortname) VALUES('Balochi', 'bal');
INSERT INTO languages (name, shortname) VALUES('Basque', 'eu');
INSERT INTO languages (name, shortname) VALUES('Basque eu_ES', 'eu_ES');
INSERT INTO languages (name, shortname) VALUES('Belarusian', 'be');
INSERT INTO languages (name, shortname) VALUES('Belarusian Latin', 'be@latin');
INSERT INTO languages (name, shortname) VALUES('Bengali', 'bn');
INSERT INTO languages (name, shortname) VALUES('Bengali (India)', 'bn_IN');
INSERT INTO languages (name, shortname) VALUES('Bosnian', 'bs');
INSERT INTO languages (name, shortname) VALUES('Brazilian Portuguese', 'pt_BR');
INSERT INTO languages (name, shortname) VALUES('British English', 'en_GB');
INSERT INTO languages (name, shortname) VALUES('Bulgarian', 'bg');
INSERT INTO languages (name, shortname) VALUES('Burmese', 'my');
INSERT INTO languages (name, shortname) VALUES('Catalan', 'ca');
INSERT INTO languages (name, shortname) VALUES('Chinese (Simplified)', 'zh_CN');
INSERT INTO languages (name, shortname) VALUES('Chinese (Traditional)', 'zh_TW');
INSERT INTO languages (name, shortname) VALUES('Croatian', 'hr');
INSERT INTO languages (name, shortname) VALUES('Czech', 'cs');
INSERT INTO languages (name, shortname) VALUES('Danish', 'da');
INSERT INTO languages (name, shortname) VALUES('Dutch', 'nl');
INSERT INTO languages (name, shortname) VALUES('Dzongkha', 'dz');
INSERT INTO languages (name, shortname) VALUES('Estonian', 'et');
INSERT INTO languages (name, shortname) VALUES('Finnish', 'fi');
INSERT INTO languages (name, shortname) VALUES('French', 'fr');
INSERT INTO languages (name, shortname) VALUES('Galician', 'gl');
INSERT INTO languages (name, shortname) VALUES('Georgian', 'ka');
INSERT INTO languages (name, shortname) VALUES('German', 'de');
INSERT INTO languages (name, shortname) VALUES('Greek', 'el');
INSERT INTO languages (name, shortname) VALUES('Gujarati', 'gu');
INSERT INTO languages (name, shortname) VALUES('Hebrew', 'he');
INSERT INTO languages (name, shortname) VALUES('Hindi', 'hi');
INSERT INTO languages (name, shortname) VALUES('Hungarian', 'hu');
INSERT INTO languages (name, shortname) VALUES('Icelandic', 'is');
INSERT INTO languages (name, shortname) VALUES('Iloko', 'ilo');
INSERT INTO languages (name, shortname) VALUES('Indonesian', 'id');
INSERT INTO languages (name, shortname) VALUES('Italian', 'it');
INSERT INTO languages (name, shortname) VALUES('Japanese', 'ja');
INSERT INTO languages (name, shortname) VALUES('Kannada', 'kn');
INSERT INTO languages (name, shortname) VALUES('Korean', 'ko');
INSERT INTO languages (name, shortname) VALUES('Kurdish', 'ku');
INSERT INTO languages (name, shortname) VALUES('Lao', 'lo');
INSERT INTO languages (name, shortname) VALUES('Latvian', 'lv');
INSERT INTO languages (name, shortname) VALUES('Lithuanian', 'lt');
INSERT INTO languages (name, shortname) VALUES('Macedonian', 'mk');
INSERT INTO languages (name, shortname) VALUES('Maithili', 'mai');
INSERT INTO languages (name, shortname) VALUES('Malay', 'ms');
INSERT INTO languages (name, shortname) VALUES('Malayalam', 'ml');
INSERT INTO languages (name, shortname) VALUES('Marathi', 'mr');
INSERT INTO languages (name, shortname) VALUES('Mongolian', 'mn');
INSERT INTO languages (name, shortname) VALUES('Nepali', 'ne');
INSERT INTO languages (name, shortname) VALUES('Northern Sotho', 'nso');
INSERT INTO languages (name, shortname) VALUES('Norwegian', 'no');
INSERT INTO languages (name, shortname) VALUES('Norwegian Bokmål', 'nb');
INSERT INTO languages (name, shortname) VALUES('Norwegian Nynorsk', 'nn');
INSERT INTO languages (name, shortname) VALUES('Oriya', 'or');
INSERT INTO languages (name, shortname) VALUES('Persian', 'fa');
INSERT INTO languages (name, shortname) VALUES('Polish', 'pl');
INSERT INTO languages (name, shortname) VALUES('Portuguese', 'pt');
INSERT INTO languages (name, shortname) VALUES('Punjabi', 'pa');
INSERT INTO languages (name, shortname) VALUES('Romanian', 'ro');
INSERT INTO languages (name, shortname) VALUES('Russian', 'ru');
INSERT INTO languages (name, shortname) VALUES('Serbian', 'sr');
INSERT INTO languages (name, shortname) VALUES('Serbian (Latin)', 'sr@latin');
INSERT INTO languages (name, shortname) VALUES('Sinhala', 'si');
INSERT INTO languages (name, shortname) VALUES('Slovak', 'sk');
INSERT INTO languages (name, shortname) VALUES('Slovenian', 'sl');
INSERT INTO languages (name, shortname) VALUES('Spanish', 'es');
INSERT INTO languages (name, shortname) VALUES('Swedish', 'sv');
INSERT INTO languages (name, shortname) VALUES('Swiss German', 'de_CH');
INSERT INTO languages (name, shortname) VALUES('Tagalog', 'tl');
INSERT INTO languages (name, shortname) VALUES('Tajik', 'tg');
INSERT INTO languages (name, shortname) VALUES('Tamil', 'ta');
INSERT INTO languages (name, shortname) VALUES('Telugu', 'te');
INSERT INTO languages (name, shortname) VALUES('Thai', 'th');
INSERT INTO languages (name, shortname) VALUES('Turkish', 'tr');
INSERT INTO languages (name, shortname) VALUES('Ukrainian', 'uk');
INSERT INTO languages (name, shortname) VALUES('Urdu', 'ur');
INSERT INTO languages (name, shortname) VALUES('Vietnamese', 'vi');
INSERT INTO languages (name, shortname) VALUES('Welsh', 'cy');
INSERT INTO languages (name, shortname) VALUES('Zulu', 'zu');
-- Also add American English:
INSERT INTO languages (name, shortname) VALUES('American English', 'en_US');
