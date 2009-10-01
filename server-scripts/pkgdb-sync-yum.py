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

from pkgdb.lib.rpm import RPMParser

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
                        ApplicationsTable
from pkgdb.model import Branch, Package, PackageListing, PackageBuild, Repo, Application, \
                        ApplicationTag, Tag, RpmFiles, PackageBuildDepends, RpmRequires, \
                        RpmProvides, RpmConflicts, RpmObsoletes

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

repos = session.query(Repo).filter_by(active=True).all()

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
    yb.add_enable_repo(repo.shortname, [
            '%s%s' % ('http://ucho.ignum.cz/fedora/linux/', repo.url),
            '%s%s' % (repo.mirror, repo.url), 
            '%s%s' % ('http://ftp.linux.cz/pub/linux/fedora/linux/', repo.url)
            ])

    yumrepo = yb.repos.getRepo(repo.shortname)
    
    log.info('Refreshing repo: %s' % yumrepo.name)

    yb._getSacks(thisrepo=yumrepo.id)
    
    
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
               
                # Do a bit of house-keeping
                (committime, committer, changelog) = rpm.changelog[0]
                committime = datetime.datetime.utcfromtimestamp(committime)
                committer = committer.replace('- ', '')
                committer = committer.rpartition(' ')[0]

                # insert the new packagebuild and get its id
                pkgbuild = PackageBuild(
                    packageid=package.id, name=rpm.name,
                    epoch=rpm.epoch, version=rpm.version,
                    release=rpm.release, size=rpm.size,
                    architecture=rpm.arch,
                    license=rpm.license, changelog=changelog,
                    committime=committime, committer=committer,
                    repoid=repo.id)
                session.add(pkgbuild)
                
                
                # FIXME: We should behave differently for various entry types 
                applications = []
                has_desktop = False

                # Look for apps
                for f in rpm.filelist:
                    if f.endswith('.desktop'):
                        has_desktop = True

                # download and process .desktop to create app
                if has_desktop:

                    desktop_entries = ()
                    try:
                        rpm_file = yumrepo.getPackage(rpm)
                        log.info("%s was downloaded" % rpm.name)
                        parser = RPMParser(rpm_file)
                        desktop_entries = parser.desktop_entries()
                    except Exception, e:
                        log.error("Error occured while downloading rpm from repo %s. %s" % (yumrepo.name, e))

                    for entry in desktop_entries:
                        if entry.has_option('Desktop Entry', 'name'):
                            try:
                                app = Application.query.filter_by(name=entry.get('Desktop Entry', 'name')).one()
                            except:
                                if entry.has_option('Desktop Entry', 'type'):
                                    desktoptype = entry.get('Desktop Entry', 'type')
                                else:
                                    desktoptype = None
                                app = Application(
                                    name=entry.get('Desktop Entry', 'name'),
                                    description=rpm.description,
                                    url=rpm.url,
                                    apptype='desktop',
                                    desktoptype=desktoptype,
                                )
                                session.add(app)
                                log.debug(repr(app))
                            applications.append(app)

                            # add .desktop categories as well as groups from comps as prefiled tags
                            if entry.has_option('Desktop Entry', 'Categories'):
                                cats = entry.get('Desktop Entry', 'Categories')
                                for cat in cats.split(';'):
                                    if cat:  # Sometimes the category ends up empty: Categories = Foo;Bar;Baz;
                                        # FIXME hendle localized keys properly
                                        # TODO: filter futile tags
                                        # FIXME: use Application.tag()
                                        log.debug("Tag: %s" % cat)
                                        try:
                                            tag = session.query(Tag).filter_by(name=cat, language='en_US').one()
                                        except:
                                            tag = Tag(name=cat, language='en_US')
                                            session.add(tag)
                                            log.debug(repr(tag))

                                        try:
                                            apptag = session.query(ApplicationTag).filter_by(applicationid=app.id, tag=tag.id).one()
                                        except:
                                            apptag = ApplicationTag()
                                            apptag.tag = tag
                                            apptag.application = app

                # create application record for packagebuild if there is no .desktop file
                if not has_desktop \
                        and not rpm.name.endswith('-devel') \
                        and not rpm.name.endswith('-debuginfo'):
                    app = Application.query.filter_by(name=rpm.name).first()
                    if not app:
                        app = Application(
                            name=rpm.name,
                            description=rpm.description,
                            url=rpm.url,
                            apptype='unknown',
                        )
                        session.add(app)
                        #session.flush()
                        log.debug(repr(app))
                    applications.append(app)
                        
                # associate the build with apps 
                for app in applications:
                    pkgbuild.applications.append(app)

                # associate the listing with the packagebuild
                listing.builds.append(pkgbuild)

                # update PRCOs (treat requires as special case)
                prcos = [['provides', RpmProvides],
                         ['conflicts', RpmConflicts],
                         ['obsoletes', RpmObsoletes]]
                for prco, prcoclass in prcos:
                    for (n, f, (e, v, r)) in getattr(rpm, prco):
                        prcoobj = prcoclass(name=n, flags=f, epoch=e,
                                        version=v, release=r)
                        prcoobj.build = pkgbuild

                # requires have the extra PreReq field
                # also setup package dependencies here
                dependencies = set()
                for (n, f, (e, v, r), p) in rpm._requires_with_pre():
                    rpm_requires = RpmRequires(name=n, flags=f, epoch=e,
                                        version=v, release=r, prereq=p)
                    rpm_requires.build = pkgbuild

                    for provider in yb.pkgSack.searchProvides(n):
                        dependencies.add(provider.name)

                for dep in dependencies:
                    build_depends = PackageBuildDepends(packagebuildname=dep)
                    build_depends.build = pkgbuild
                        
                # files
                for filename in rpm.filelist:
                    rpm_file = RpmFiles(name=filename)
                    rpm_file.build = pkgbuild


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
        # flush per rpm
        session.flush()
        log.info("Collected data about %s were flushed" % rpm.name)

    # finish up for this repo
    yb.cleanMetadata()
    yb.cleanExpireCache()
    yb.cleanSqlite()
    yb.close()
    yumrepo.close()
