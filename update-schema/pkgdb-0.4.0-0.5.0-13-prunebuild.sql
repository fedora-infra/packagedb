CREATE OR REPLACE FUNCTION remove_orphaned_builds()
RETURNS trigger AS $remove_orphaned_builds$
    BEGIN
        DELETE FROM packagebuild USING (
            SELECT OLD.packagebuildid as id, count(*) as count 
            FROM packagebuildrepos p 
            WHERE p.packagebuildid = OLD.packagebuildid
        ) pbr 
        WHERE pbr.id = packagebuild.id AND pbr.count = 0;

        RETURN OLD;
    END;
$remove_orphaned_builds$ LANGUAGE plpgsql;

CREATE TRIGGER remove_orphaned_builds AFTER DELETE ON packagebuildrepos
    FOR EACH ROW EXECUTE PROCEDURE remove_orphaned_builds();

