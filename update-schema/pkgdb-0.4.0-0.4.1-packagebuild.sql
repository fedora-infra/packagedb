-- Fix a small typo

CREATE OR REPLACE FUNCTION package_build_agreement()
  RETURNS trigger AS
$BODY$
DECLARE
  pkgList_pid integer;
  pkgBuild_pid integer;
BEGIN
  -- if (TG_TABLE_NAME = 'PackageBuildListing') then
  if (TG_RELNAME = 'packagebuildlisting') then
    -- Upon entering a new relationship between a Build and Listing, make sure
    -- they reference the same package.
    pkgList_pid := packageId from packageListing where id = NEW.packageListingId;
    pkgBuild_pid := packageId from packageBuild where id = NEW.packageBuildId;
    if (pkgList_pid != pkgBuild_pid) then
      raise exception 'PackageBuild % and PackageListing % have to reference the same package', NEW.packageBuildId, NEW.packageListingId;
    end if;
  -- elsif (TG_TABLE_NAME = 'PackageBuild') then
  elsif (TG_RELNAME = 'packagebuild') then
    -- Disallow updating the packageId field of PackageBuild if it is
    -- associated with a PackageListing
    if (NEW.packageId != OLD.packageId) then
      select * from PackageBuildListing where PackageBuildId = NEW.id;
      if (FOUND) then
        raise exception 'Cannot update packageId when PackageBuild is referenced by a PackageListing';
      end if;
    end if;
  -- elsif (TG_TABLE_NAME = 'PackageListing') then
  elsif (TG_RELNAME = 'packagelisting') then
    -- Disallow updating the packageId field of PackageListing if it is
    -- associated with a PackageBuild
    if (NEW.packageId != OLD.packageId) then
      select * from PackageBuildListing where PackageListingId = NEW.id;
      if (FOUND) then
        raise exception 'Cannot update packageId when PackageListing is referenced by a PackageBuild';
      end if;
    end if;
  else
    -- raise exception 'Triggering table % is not one of PackageBuild, PackageListing, or PackageBuildListing', TG_TABLE_NAME;
    raise exception 'Triggering table % is not one of PackageBuild, PackageListing, or PackageBuildListing', TG_RELNAME;
  end if;
  return NEW;
END;
$BODY$
  LANGUAGE 'plpgsql' VOLATILE
  COST 100;
ALTER FUNCTION package_build_agreement() OWNER TO postgres;

drop trigger if exists package_build_agreement_trigger on PackageBuildListing;
create trigger package_build_agreement_trigger before update or insert
  on PackageBuildListing
  for each row execute procedure package_build_agreement();

drop trigger if exists package_build_agreement_trigger on PackageListing;
create trigger package_build_agreement_trigger before update
  on PackageListing
  for each row execute procedure package_build_agreement();

drop trigger if exists package_build_agreement_trigger on PackageBuild;
create trigger package_build_agreement_trigger before update
  on PackageBuild
  for each row execute procedure package_build_agreement();

