-- Due to tags refactoring these triggers were moved on ORM level

ALTER TABLE applicationstags DISABLE TRIGGER applicationstags_score;
DROP TRIGGER applicationstags_score ON applicationstags;
DROP FUNCTION applicationstags_score();

ALTER TABLE binarypackagetags DISABLE TRIGGER binarypackagetags_score;
DROP TRIGGER binarypackagetags_score ON binarypackagetags;
DROP FUNCTION binarypackagetags_score();


