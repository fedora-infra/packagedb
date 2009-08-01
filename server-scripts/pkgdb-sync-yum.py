import os
import sys
import yum
import sqlalchemy
import logging
import datetime

from sqlalchemy.sql import insert, delete, and_
from turbogears import config, update_config
from turbogears.database import session

MIRROR = 'http://download.fedoraproject.org/pub/fedora/linux'
CONFDIR='@CONFDIR@'
PKGDBDIR=os.path.join('@DATADIR@', 'fedora-packagedb')
sys.path.append(PKGDBDIR)

if len(sys.argv) > 1:
    update_config(configfile=sys.argv[1],
        modulename='pkgdb.config')
elif os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'setup.py')):
    update_config(configfile='pkgdb.cfg', modulename='pkgdb.config')
else:
    update_config(configfile=os.path.join(CONFDIR,'pkgdb.cfg'),
            modulename='pkgdb.config')
config.update({'pkgdb.basedir': PKGDBDIR})

from pkgdb.model import PackageBuildTable, RpmProvidesTable, RpmRequiresTable, \
                        RpmConflictsTable, RpmObsoletesTable, RpmFilesTable, \
                        ReposTable, PackageBuildListingTable, \
                        PackageBuildDependsTable, PackageTable
from pkgdb.model import Branch, Package, PackageListing, PackageBuild, Repo

fas_url = config.get('fas.url', 'https://admin.fedoraproject.org/accounts/')
username = config.get('fas.username', 'admin')
password = config.get('fas.password', 'admin')

log = logging.getLogger('pkgdb')

def get_pkg_name(rpm):
    # get the name of the Package, ignore -devel/-doc tags, version etc.
    # !version sometimes isn't the same as the sourcerpm's
    namelist = rpm.sourcerpm.split('-')
    namelist.pop()
    namelist.pop()
    packagename = '-'.join(namelist)
    return packagename

repos = Repo.query.all()

# get sacks first, so we can search for dependencies
for repo in repos:
    yb = yum.YumBase()

    yb.cleanSqlite()
    yb.cleanMetadata()
    yb.cleanExpireCache()
    
    yb.repos.disableRepo('*')
    yb.add_enable_repo(repo.shortname, ['%s%s' % (MIRROR, repo.url)])

    yumrepo = yb.repos.getRepo(repo.shortname)
    
    yb._getSacks(thisrepo=yumrepo.id)
    
    log.info('\nRefreshing repo: %s' % yumrepo.name)
    
    # populate pkgdb with packagebuilds (rpms)
    rpms = yumrepo.sack.returnNewestByName()[:10]
    if rpms == []:
        log.warn("There were no packages in this repo!")
    for rpm in rpms:

        packagename = get_pkg_name(rpm)
        pkg_query = Package.query.filter_by(name=packagename)
        try:
            package = pkg_query.one()
        except:
            log.warn("%s - the corresponding package does not exist in the" \
                     " pkgdb! pkgbuild was not added. Tried: %s" %
                     (rpm.name, packagename))
        else:
            # what's my packagelisting?
            collectionid = repo.collection.id
            listing_query = PackageListing.query.filter_by(
                                packageid=package.id,
                                collectionid=collectionid)
            try:
                listing = listing_query.one()
            except:
                log.warn("%s - the corresponding packagelist does not " \
                      "exist in the pkgdb! pkgbuild was not added." % rpm.name)
            else:
                if PackageBuild.query.filter_by(
                                name=rpm.name,
                                packageid=package.id,
                                version=rpm.version,
                                architecture=rpm.arch,
                                repoid=repo.id,
                                release=rpm.release).count() != 0:
                    log.warn("%s-%s - PackageBuild already in! " \
                             "Skipping to next repo." % (
                        pkg_query.one().name, rpm.version))
                    break

                desktop = False
                for f in rpm.filelist:
                    if f.endswith('.desktop'):
                        desktop = True
                        
                # do a bit of house-keeping
                (committime, committer, changelog) = rpm.changelog[0]
                committime = datetime.datetime.utcfromtimestamp(committime)
                committer = committer.replace('- ', '')
                committer = committer.rpartition(' ')[0]

                # insert the new packagebuild and get its id
                pkgbuildid = PackageBuildTable.insert().values(
                    packageid=package.id, name=rpm.name,
                    epoch=rpm.epoch, version=rpm.version,
                    release=rpm.release, size=rpm.size,
                    architecture=rpm.arch, desktop=desktop,
                    license=rpm.license, changelog=changelog,
                    committime=committime, committer=committer,
                    repoid=repo.id).execute().last_inserted_ids()[-1]
                
                # associate the listing with the packagebuild
                PackageBuildListingTable.insert().values(
                    packagebuildid=pkgbuildid, packagelistingid=listing.id
                    ).execute()

                # update PRCOs (treat requires as special case)
                prcos = [['provides', RpmProvidesTable],
                         ['conflicts', RpmConflictsTable],
                         ['obsoletes', RpmObsoletesTable]]
                for prco, prcotable in prcos:
                    for (n, f, (e, v, r)) in getattr(rpm, prco):
                        prcotable.insert().values(name=n, flags=f, epoch=e,
                                                  version=v, release=r,
                                                  packagebuildid=pkgbuildid
                                                  ).execute()
                # requires have the extra PreReq field
                # also setup package dependencies here
                dependencies = set()
                for (n, f, (e, v, r), p) in rpm._requires_with_pre():
                    RpmRequiresTable.insert().values(name=n, flags=f, epoch=e,
                                        version=v, release=r, prereq=p,
                                        packagebuildid=pkgbuildid
                                        ).execute()
                    for provider in yb.pkgSack.searchProvides(n):
                        dependencies.add(provider.name)

                for dep in dependencies:
                    PackageBuildDependsTable.insert().values(
                        packagebuildid=pkgbuildid,
                        packagebuildname=dep
                        ).execute()
                        
                # files
                for filename in rpm.filelist:
                    RpmFilesTable.insert().values(packagebuildid=pkgbuildid,
                                                  name=filename).execute()

                # update the package information

                if (package.description != rpm.description) or \
                   (package.summary != rpm.summary) or \
                   (package.upstreamurl != rpm.url):
                    PackageTable.update().where(
                        PackageTable.c.id==package.id
                        ).values(
                        description = rpm.description,
                        summary = rpm.summary,
                        upstreamurl = rpm.url).execute()
                
                # keep only the latest packagebuild from each repo
                PackageBuildTable.delete().where(and_(
                    PackageBuildTable.c.name==rpm.name,
                    PackageBuildTable.c.repoid==repo.id))

                log.info('inserted %s-%s-%s' % (pkg_query.one().name,
                                             rpm.version, rpm.release))
        # finish up for this repo
        # yb.cleanMetadata()
        # yb.cleanExpireCache()
        # yb.cleanSqlite()

    yb.close()
    yumrepo.close()
