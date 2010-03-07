#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
#
# Copyright © 2010  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2, or (at your option) any later version.  This
# program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the GNU
# General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA. Any Red Hat trademarks that are incorporated in the source
# code or documentation are not subject to the GNU General Public License and
# may only be used or replicated with the express permission of Red Hat, Inc.
#
# Author(s): Martin Bacovsky <mbacovsk@redhat.com>
#
'''
PackageBuild related tools
'''

from turbogears.database import session, get_engine
import datetime
import logging
import pytz
import re
import os
import sys
import atexit
from StringIO import StringIO
import stat
import rpmUtils
import ConfigParser
from cpioarchive import CpioArchive
from sqlalchemy.sql import and_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import eagerload

import yum
from yum.misc import getCacheDir
from yum.parser import varReplace

# Currently, this is broken for xz so use our version
#from rpmUtils.miscutils import rpm2cpio
from pkgdb.lib.utils import rpm2cpio


try:
    from fedora.textutils import to_unicode
except ImportError:
    from pkgdb.lib.utils import to_unicode

from pkgdb.model import Package, PackageBuild, PackageListing, BinaryPackage
from pkgdb.model import RpmFiles, RpmProvides, RpmObsoletes, RpmConflicts
from pkgdb.model import RpmRequires, PackageBuildDepends, PackageBuildRepo
from pkgdb.model import Icon, IconName, Theme, Repo
from pkgdb.model import Application

from pkgdb.lib.desktop import Desktop, DesktopParseError
from pkgdb.lib.icon import Icon as IconImage

log = logging.getLogger(__name__)

RE_APP_ICON_FILE = re.compile(
        "^.*/(icons|pixmaps)/([^/]*)/(\d+x\d+)/apps/([^/]*)\.png$")

class PkgImportError(Exception):
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)


class PkgImportAlreadyExists(Exception):
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)


class RPM(object):
    '''

    Note: RPM objects store their strings as byte strings.  This is because we
    can't tell here what we're going to do with the data.  At some point you
    may need to transform the data from bytes into unicode.
    '''
    
    def __init__(self, build, yumrepo):
    
        self.build = build
        self._cpio = None
        self._fdno = None
        self.yumrepo = yumrepo
        self._issued_arch_closes = []


    def close(self):
        """Clean after yourself
        """
        # cpioarchive registers iself in atexit and thuc can't be 
        # garbage collected
        if len(self._issued_arch_closes) == 0:
            return 
        
        pos_to_del = []

        for (pos, eh) in enumerate(atexit._exithandlers):
             if eh[0] in self._issued_arch_closes:
                eh[0](*(eh[1]), **(eh[2]))
                pos_to_del.append(pos)

        # a bit awkward way to drop unnecesary stuff
        for (idx,pos) in enumerate(pos_to_del):
            del atexit._exithandlers[pos-idx]


    @property
    def archive(self):
        """ Open an load rpm file and return the enclosed CpioArchive object.
            The requestor is responsible for closing the archive.
        """

        if not self._cpio:
            filename = self.build.localPkg()
            if not os.path.exists(filename):
                try:
                    log.info("          Downloading...")
                    filename = self.yumrepo.getPackage(self.build)
                except:
                    exc_class, exc, tb = sys.exc_info()
                    e = PkgImportError(exc)
                    raise e.__class__, e, tb

            self._fdno = os.open(filename, os.O_RDONLY)

            # rpm2cpio won't just output a blob of data, it needs a file.
            # Using StringIO here takes more memory than a tempfile, but
            # should be faster.
            # rpm2cpio closes fdno
            cpio = StringIO()
            try:
                rpm2cpio(self._fdno, out=cpio)
            except Exception, e:
                exc_class, exc, tb = sys.exc_info()
                e = PkgImportError("Invalid RPM file (%s). Yum cache broken?" % exc)
                raise e.__class__, e, tb
            self._cpio = cpio

        # Back to the beginning of the file
        self._cpio.seek(0)

        archive = CpioArchive(fileobj=self._cpio)
        self._issued_arch_closes.append(archive.close)

        return archive


    def re_custom_icons(self, icon_names=()):
            return re.compile(r"^.*/(icons|pixmaps).*/(%s)\.png$" % '|'.join((re.escape(e) for e in icon_names)))


    def has_icon(self, icon_names=()):
        """Finds out if rpm contains at least one icon file

        :arg icon_names: list of icon names we are especially looking for
        :returns: result of the test
        :rtype: boolean
        """
        if icon_names:
            re_cust_icons = self.re_custom_icons(icon_names)


        for f in self.filelist:
            if RE_APP_ICON_FILE.match(f) or (
                    icon_names and re_cust_icons.match(f)):
                return True
            
        return False


    def _prune_icons(self, icons):
        """Leave one icon (optimal for resize to 48x48)
        for every name and theme pair

        :arg icons: list of Icon objects
        :returns: pruned list of Icon objects
        """

        _icons = {}

        # organize
        for i in icons:
            sel = _icons.get(i.group_key, {})
            sel[i.size] = i
            _icons[i.group_key] = sel

        # prune
        pruned = []
        for i_set in _icons.values():
            if i_set.has_key(48):
                pruned.append(i_set[48])
            else:
                pruned.append(i_set[max(i_set.keys())])
        
        return pruned


    def icons(self, icon_names=()):
        """List of icons included in rpm

        The list is pruned and only one icon (optimal for resizing
        to 48x48) is left for each name, theme pair.

        :arg icon_names: list of icon names that will help us
            with search in unusual locations
        :returns: list of Icon objects
        """

        # check for icons first, getting full rpm is expensive
        if not self.has_icon(icon_names):
            return []

        icons = []

        if icon_names:
            re_cust_icons = self.re_custom_icons(icon_names)

        arch = self.archive

        for f in arch:
            if RE_APP_ICON_FILE.match(f.name) or (
                    icon_names and re_cust_icons.match(f.name)):
                icon_file = StringIO(f.read())
                try:
                    icon = IconImage.from_filename(f.name, icon_file)
                    icon.check()
                    icons.append(icon)
                except:
                    log.warning("%s: Unable to parse icon: %s" % (self.build, f.name))

        arch.close()

        return self._prune_icons(icons)


    def has_desktop(self):
        """Finds out if rpm contains at least one .desktop file

        :returns: result of the test
        :rtype: boolean
        """
        for f in self.filelist:
            if f.endswith('.desktop'):
                return True
        return False
        

    def desktops(self):
        """All .desktop file entries from rpm
        :returns: Iterator over Desktop objects (parsed .desktop files)
        """
        # check for desktops first, getting full rpm is expensive
        if not self.has_desktop():
            raise StopIteration
       
        arch = self.archive

        for f in arch:
            if f.name.endswith('.desktop'):
                desktop_file = StringIO(f.read())
                try:
                    desktop = Desktop.from_file(desktop_file)
                except DesktopParseError, e:
                    log.warning("%s: Invalid .desktop file: %s" % (self.build, e))
                    desktop_file.close()
                    continue

                desktop_file.close()
                yield desktop

        arch.close()


    sourcerpm = property(lambda self: self.build.sourcerpm)
    name = property(lambda self: self.build.name)
    epoch = property(lambda self: self.build.epoch)
    version = property(lambda self: self.build.version)
    arch = property(lambda self: self.build.arch)
    release = property(lambda self: self.build.release)
    changelog = property(lambda self: self.build.changelog)
    filelist = property(lambda self: self.build.filelist)
    provides = property(lambda self: self.build.provides)
    obsoletes = property(lambda self: self.build.obsoletes)
    conflicts = property(lambda self: self.build.conflicts)
    url = property(lambda self: self.build.url)
    size = property(lambda self: self.build.size)
    license = property(lambda self: self.build.license)

    requires_with_pre = property(lambda self: self.build._requires_with_pre)


class PackageBuildImporter(object):

    def __init__(self, repo, cachedir='/var/tmp', force=False):
        self.repo = repo
        self.force = force
        self.collection = repo.collection
        self._yumrepo = None
        self._yumbase = None
        self._builds = None
        self.cachedir = getCacheDir(cachedir)
        if not self.cachedir:
            raise PkgImportError('Unable to setup yum cache directory.')


    def get_package(self, rpm):
        """Find corresponding package in pkgdb
       
        :arg rpm: RpmBase instance
        :raises PkgImportError: when coresponding package does not exist in PkgDB
        :returns: package
        """
        #get the name of the Package, ignore -devel/-doc tags, version etc.
        #version sometimes isn't the same as the sourcerpm's
        namelist = rpm.sourcerpm.split('-')
        package_name = '-'.join(namelist[:-2])

        #pylint:disable-msg=E1101
        pkg_query = session.query(Package).filter_by(name=package_name)
        #pylint:enable-msg=E1101
        try:
            package = pkg_query.one()
        except:
            exc_class, exc, tb = sys.exc_info()
            e = PkgImportError('The corresponding package (%s) does not '
                    'exist in the pkgdb!' % package_name)
            raise e.__class__, e, tb
        return package

    
    @property
    def yumbase(self):
        if not self._yumbase:
            yumbase = yum.YumBase()

            # suppress yum plugins output
            yum_log = logging.getLogger('yum.verbose.YumPlugins')
            yum_log.setLevel(logging.ERROR)

            yumbase.repos.setCacheDir(self.cachedir + varReplace('/$basearch/$releasever', yumbase.yumvar))

            yumbase.conf.cachedir = self.cachedir
            yumbase.doTsSetup()
            self._yumbase = yumbase

        return self._yumbase


    @property
    def yumrepo(self):
        if not self._yumrepo:
            self.yumbase.repos.disableRepo('*')
            self.yumbase.add_enable_repo('pkgdb-%s' % self.repo.shortname,
                       ['%s%s' % (self.repo.mirror, self.repo.url)])
            self._yumrepo = self.yumbase.repos.getRepo('pkgdb-%s' % self.repo.shortname)
           
            # populate sack
            try:
                self.yumbase._getSacks(thisrepo=self._yumrepo.id)
            except:
                exc_class, exc, tb = sys.exc_info()
                e = PkgImportError('Repo %s failed to read! (%s)' % (self._yumrepo, exc))
                raise e.__class__, e, tb

        return self._yumrepo


    @property
    def builds(self):
        if not self._builds:
            builds_data = session.query(
                    PackageBuild.name,
                    PackageBuild.epoch,
                    PackageBuild.version,
                    PackageBuild.release,
                    PackageBuild.architecture)\
                .join(PackageBuild.repos)\
                .filter(Repo.id==self.repo.id)\
                .all()
            self._builds = set(builds_data)

        return self._builds



    def check_package_listing(self, package):
        """Check if the package is in listing for the currently processed collection.

        :arg package: package object associated with build we are going to import
        :raises PkgImportError: when package is not included in the collection
        :returns: True if the check passed
        """
   
        try:
            #pylint:disable-msg=E1101
            listing = session.query(PackageListing)\
                .filter_by(
                    collectionid=self.collection.id,
                    packageid=package.id)\
                .one()
            #pylint:enable-msg=E1101
        except NoResultFound:
            raise PkgImportError('The package (%s) is not '
                    'included in requested collection (%s)!' % (package.name, self.collection.simple_name))

        return True
            

    def store_package_build(self, rpm):
        """Store packagebuild data in DB

        :args rpm: RPMBase instance
        :raises PkgImportAlreadyExists: when pkgbuild 
                    was already imported and not in force mode
        :returns: PackageBuild instance

        Checks whether packagebuild was already imported. 
        Import is interupted if it was and we are also not in 'force' mode.
        The record is created/updated otherwise.
        """

        build_key = (rpm.name, rpm.epoch, rpm.version, rpm.release, rpm.arch)
    
        if not self.force and build_key in self.builds:
            # The build already exists
            # interrupt import unless in force mode
            raise PkgImportAlreadyExists('This packagebuild was already imported.')

        try:
            # we assume that in any two repos there 
            # do not exist two packages with same nvr, 
            # that are built from different packages. 
            # We should also filter by packageid otherwise.
            #pylint:disable-msg=E1101
            pkgbuild = session.query(PackageBuild)\
                .filter_by(
                    name=to_unicode(rpm.name),
                    epoch=to_unicode(rpm.epoch),
                    version=to_unicode(to_unicode(rpm.version)),
                    architecture=to_unicode(to_unicode(rpm.arch)),
                    release=to_unicode(rpm.release))\
                .options(eagerload(PackageBuild.repos))\
                .one()
            #pylint:enable-msg=E1101
        except NoResultFound:
            package = self.get_package(rpm)
            self.check_package_listing(package)
            # insert the new packagebuild and get its id
            pkgbuild = PackageBuild(
                packageid=package.id, name=to_unicode(rpm.name),
                epoch=to_unicode(rpm.epoch), version=to_unicode(rpm.version),
                release=to_unicode(rpm.release),
                size=0, architecture=to_unicode(rpm.arch), license='',
                changelog='', committime=datetime.datetime.now(), committer='')
            session.add(pkgbuild) #pylint:disable-msg=E1101

            # create link to repo
            pkgbuild.repos.append(self.repo)

        else:
            # check link to repo
            if self.repo not in pkgbuild.repos:
                pkgbuild.repos.append(self.repo)

        # store commit data
        #FIXME: should be committime really tz aware?
        utc = pytz.timezone('UTC')
        (committime, committer, changelog) = (datetime.datetime.now(),'','')
        if rpm.changelog:
            (committime, committer, changelog) = rpm.changelog[0]
            committime = datetime.datetime.utcfromtimestamp(committime)
            committer = committer.replace('- ', '')
            committer = committer.rsplit(' ', 1)[0]

        pkgbuild.committime = to_unicode(committime.replace(tzinfo=utc))
        pkgbuild.committer = to_unicode(committer)
        pkgbuild.changelog = to_unicode(changelog)

        pkgbuild.size = to_unicode(rpm.size)
        pkgbuild.license = to_unicode(rpm.license)

        return pkgbuild


    def store_binary_package(self, name):
        """Store bianrypackage in DB

        :args name: packagebuild name
        :returns: BinaryPackage instance

        Finds binarypackage record in DB.
        Creates one if it was not found,
        """
        try:
            #pylint:disable-msg=E1101
            binary_package = session.query(BinaryPackage).filter_by(name=name).one()
            #pylint:enable-msg=E1101
        except:
            binary_package = BinaryPackage(name)
            session.add(binary_package) #pylint:disable-msg=E1101

        return binary_package


    def store_filelist(self, rpm, pkgbuild):
        """Store filelist

        :args rpm: RPMBase instance 
        :args pkgbuild: pkgbuild record in pkgdb  
        """
        #pylint:disable-msg=E1101
        session.query(RpmFiles).filter_by(build=pkgbuild)\
            .delete(synchronize_session=False)
        #pylint:enable-msg=E1101
        for filename in rpm.filelist:
            rpm_file = RpmFiles(name=filename)
            rpm_file.build = pkgbuild


    def store_provides(self, rpm, pkgbuild):
        """Store provides

        :args rpm: RPMBase instance 
        :args pkgbuild: pkgbuild record in pkgdb  
        """
        #pylint:disable-msg=E1101
        session.query(RpmProvides).filter_by(build=pkgbuild)\
            .delete(synchronize_session=False)
        #pylint:enable-msg=E1101
        for (n, f, (e, v, r)) in rpm.provides:
            obj = RpmProvides(name=n, flags=f, epoch=e,
                            version=v, release=r)
            obj.build = pkgbuild


    def store_obsoletes(self, rpm, pkgbuild):
        """Store obsoletes

        :args rpm: RPMBase instance 
        :args pkgbuild: pkgbuild record in pkgdb  
        """
        #pylint:disable-msg=E1101
        session.query(RpmObsoletes).filter_by(build=pkgbuild)\
            .delete(synchronize_session=False)
        #pylint:enable-msg=E1101
        for (n, f, (e, v, r)) in rpm.obsoletes:
            obj = RpmObsoletes(name=n, flags=f, epoch=e,
                            version=v, release=r)
            obj.build = pkgbuild


    def store_conflicts(self, rpm, pkgbuild):
        """Store conflicts

        :args rpm: RPMBase instance 
        :args pkgbuild: pkgbuild record in pkgdb  
        """
        #pylint:disable-msg=E1101
        session.query(RpmConflicts).filter_by(build=pkgbuild)\
            .delete(synchronize_session=False)
        #pylint:enable-msg=E1101
        for (n, f, (e, v, r)) in rpm.conflicts:
            obj = RpmConflicts(name=n, flags=f, epoch=e,
                            version=v, release=r)
            obj.build = pkgbuild


    def store_requires(self, rpm, pkgbuild):
        """Store requires

        :args rpm: RPMBase instance 
        :args pkgbuild: pkgbuild record in pkgdb  
        """
        #pylint:disable-msg=E1101
        session.query(RpmRequires).filter_by(build=pkgbuild)\
            .delete(synchronize_session=False)
        #pylint:enable-msg=E1101
        for (n, f, (e, v, r), p) in rpm.requires_with_pre():
            obj = RpmRequires(name=n, flags=f, epoch=e,
                            version=v, release=r, prereq=bool(p))
            obj.build = pkgbuild


    def store_dependencies(self, rpm, pkgbuild):
        """Store dependencies

        :args rpm: RPMBase instance 
        :args pkgbuild: pkgbuild record in pkgdb  
        """
        #pylint:disable-msg=E1101
        session.query(PackageBuildDepends).filter_by(build=pkgbuild)\
            .delete(synchronize_session=False)
        #pylint:enable-msg=E1101
        providers = set()
        for (n, f, (e, v, r), p) in rpm.requires_with_pre():
            for provider in self.yumrepo.sack.searchProvides(n):
                providers.add(provider.name)

        for provider in providers:
            dep = PackageBuildDepends(packagebuildname=provider)
            dep.build = pkgbuild


    def store_icon_name(self, name):
        """Create icon name record if it doesn't exist
        :arg name: icon name
        :returns: IconName object
        """
        try:
            #pylint:disable-msg=E1101
            icon_name = session.query(IconName).\
                    filter_by(name=name).one()
        except:
            icon_name = IconName(name=name)
            session.add(icon_name) 
            #session.flush()
            #pylint:enable-msg=E1101

        return icon_name


    def store_icon_theme(self, name):
        """Create icon theme record if it doesn't exist
        :arg name: theme name
        :returns: Theme object
        """
        try:
            #pylint:disable-msg=E1101
            theme = session.query(Theme).\
                    filter_by(name=name).one()
        except:
            theme = Theme(name=name)
            session.add(theme) 
            #session.flush() 
            #pylint:enable-msg=E1101

        return theme


    def store_icon(self, icon_image):
        """Create icon record if it doesn't exist

        Also make sure the associated data (icon name, theme)
        are stored as well. Update icon data if we have some 
        of better quality.

        :arg icon_image: pkgdb.lib.icon.Icon object
        """
        log.info("    - icon: %s" % icon_image)
        # icon_name
        icon_name = self.store_icon_name(icon_image.name)
        
        # icon_theme
        icon_theme = self.store_icon_theme(icon_image.theme)

        # icon
        try:
            #pylint:disable-msg=E1101
            icon = session.query(Icon).filter_by(
                    themeid=icon_theme.id,
                    nameid=icon_name.id,
                    collectionid=self.collection.id).one()
            #pylint:enable-msg=E1101
        except:
            icon = Icon(
                icon=icon_image.export(48).getvalue(),
                name=icon_name,
                theme=icon_theme,
                collection=self.collection,
                orig_size=icon_image.size)
            session.add(icon) #pylint:disable-msg=E1101

        # update icon data in DB if we have something better available
        if icon.orig_size < 48 and icon_image.size > icon.orig_size:
            icon.orig_size = icon_image.size
            icon.icon = icon_image.export(48).getvalue()

        session.flush() #pylint:disable-msg=E1101


    def store_desktop_app(self, rpm, pkgbuild, desktop):
        """Create Application instance and related stuff found in .desktop

        Application is created or update depending on its presence in DB.
        Tags and mimetypes are created/updated as well.
        Relation to icon and packagebuild are created too if needed.
        
        :arg rpm: RPM class instance
        :arg pkgbuild: PackageBuild object that represents
            the rpm above in pkgdb DB
        :arg desktop: Desktop object
        :returns: new or updated Application instance
        """

        # application
        try:
            #pylint:disable-msg=E1101
            app = session.query(Application)\
                .filter_by(
                    name=desktop.name,
                    apptype='desktop')\
                .one()
            #pylint:enable-msg=E1101
        except NoResultFound:
            app = Application(
                name=desktop.name,
                description=desktop.comment,
                summary=desktop.generic_name,
                url=rpm.url,
                apptype='desktop',
                desktoptype=desktop.target_type)
            session.add(app) #pylint:disable-msg=E1101
        else:
            app.description=desktop.comment
            app.summary=desktop.generic_name
            app.url=rpm.url
            app.desktoptype=desktop.target_type

        # icon name
        if desktop.icon_name:
            icon_name = self.store_icon_name(desktop.icon_name)
            app.iconname = icon_name
            
        # categories
        log.info("    - categories: %s items" % len(desktop.categories))
        for category in desktop.categories:
            app.tag(category)
            session.flush()

        # mimetypes
        log.info("    - mimetypes: %s items" % len(desktop.mimetypes))
        for mimetype in desktop.mimetypes:
            app.assign_mimetype(mimetype)
            session.flush()


        # assign to build
        if app not in pkgbuild.applications:
            pkgbuild.applications.append(app)

        session.flush() #pylint:disable-msg=E1101

        return app


    def prune_builds(self):
        """Remove builds that are no longer in repo
        """

        # get what is we think is in repo
        build_list = session.query(
                PackageBuild.id,
                PackageBuild.name,
                PackageBuild.epoch,
                PackageBuild.version,
                PackageBuild.release,
                PackageBuild.architecture)\
            .join(PackageBuild.repos)\
            .filter(Repo.id==self.repo.id)\
            .all()

        builds = dict(
                ((b.name, b.epoch, b.version, b.release, b.architecture), b.id)\
                for b in build_list)
        
        # delete what is realy in repo
        for b in self.yumrepo.sack.returnNewestByName():
            try:
                del builds[(b.name, b.epoch, b.version, b.release, b.arch)]
            except KeyError:
                pass
        
        # delete from db what left
        # delete build to repo associations
        session.query(PackageBuildRepo)\
            .filter(
                and_(
                    PackageBuildRepo.packagebuildid.in_(builds.values()),
                    PackageBuildRepo.repoid==self.repo.id))\
            .delete()

        # deletion of builds without association to repo
        # is guaranteed by db trigger

        log.info("Repo pruned...")


    def delete_all_builds(self):
        """Delete all builds that belongs to the repo
        """
        # delete build to repo associations
        # deletion of builds without association to any repo
        # is guaranteed by db trigger
        session.query(PackageBuildRepo)\
            .filter(PackageBuildRepo.repoid==self.repo.id)\
            .delete()

        log.info("Builds were deleted...")


    def close(self, prune=True):
        """Clean up after import
        """
        if prune:
            self.prune_builds()

        if self._yumbase:
            self._yumbase.cleanPackages()
            self._yumbase.cleanExpireCache()
            self._yumbase.close()



    def process(self, rpm):
        """Import build

        :args rpm: build 
        """
       
        pkgbuild = self.store_package_build(rpm)
        binary_package = self.store_binary_package(rpm.name)

        self.store_filelist(rpm, pkgbuild)
        self.store_provides(rpm, pkgbuild)
        self.store_obsoletes(rpm, pkgbuild)
        self.store_conflicts(rpm, pkgbuild)
        self.store_requires(rpm, pkgbuild)
        self.store_dependencies(rpm, pkgbuild)
        
        icon_names = set()

        for desktop in rpm.desktops():
            log.info("  Application found: %s" % desktop.name)
            self.store_desktop_app(rpm, pkgbuild, desktop)
            if desktop.icon_name:
                icon_names.add(desktop.icon_name)

        
        icons = rpm.icons(icon_names)
        for icon in icons:
            self.store_icon(icon)

