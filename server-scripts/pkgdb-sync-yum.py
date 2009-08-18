#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
#
# Copyright © 2009  Red Hat, Inc. All rights reserved.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.  You should have
# received a copy of the GNU General Public License along with this program;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
# incorporated in the source code or documentation are not subject to the GNU
# General Public License and may only be used or replicated with the express
# permission of Red Hat, Inc.
#
# Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#
'''
sync information from yum into the packagedb

Import PackageBuild(rpm) related information from all the `active` repos
available in the pkgdb.
'''

import os
import sys
import yum
import sqlalchemy
import logging
import datetime

from sqlalchemy.sql import insert, delete, and_
from turbogears import config, update_config
from turbogears.database import session

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
                        PackageBuildDependsTable, PackageTable, \
                        PackageBuildNamesTable
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

repos = Repo.query.filter_by(active=True).all()

# make a clean start
yb = yum.YumBase()
yb.cleanSqlite()
yb.cleanMetadata()
yb.cleanExpireCache()
yb.close()

# get sacks first, so we can search for dependencies
for repo in repos:
    yb = yum.YumBase()

    yb.repos.disableRepo('*')
    yb.add_enable_repo('pkgdb-%s' % repo.shortname,
                       ['%s%s' % (repo.mirror, repo.url)])

    yumrepo = yb.repos.getRepo('pkgdb-%s' % repo.shortname)
    
    yb._getSacks(thisrepo=yumrepo.id)
    
    log.info('Refreshing repo: %s' % yumrepo.name)
    
    # populate pkgdb with packagebuilds (rpms)
    rpms = yumrepo.sack.returnNewestByName()[:10]
    if rpms == []:
        log.warn("There were no packages in this repo! %s%s" % (
            repo.mirror, repo.url))
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

                # Make sure the buildname is in the db
                conn = PackageBuildNamesTable.select(
                    PackageBuildNamesTable.c.name==rpm.name).execute()
                buildname = conn.fetchone()
                if buildname == None:
                    PackageBuildNamesTable.insert().values(name=rpm.name
                                                           ).execute()
                conn.close()
                
                desktop = False
                for f in rpm.filelist:
                    if f.endswith('.desktop'):
                        desktop = True
                        
                # Do a bit of house-keeping
                if rpm.changelog:
                    (committime, committer, changelog) = rpm.changelog[0]
                    committime = datetime.datetime.utcfromtimestamp(committime)
                    committer = committer.replace('- ', '')
                    committer = committer.rsplit(' ',1)[0]
                else:
                    (committime, committer, changelog) = (
                        datetime.datetime.now(),'','')

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

                log.info('inserted %s-%s-%s' % (rpm.name,
                                             rpm.version, rpm.release))
    # finish up for this repo
    yb.cleanMetadata()
    yb.cleanExpireCache()
    yb.cleanSqlite()
    yb.close()
    yumrepo.close()
