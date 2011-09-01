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
import os
import atexit
import logging
import sys
import yum
from yum.misc import getCacheDir
from yum.parser import varReplace
from stat import S_IEXEC, S_IFDIR
from StringIO import StringIO
from cpioarchive import CpioArchive
import re

from pkgdb.lib.desktop import Desktop, DesktopParseError
from pkgdb.lib.icon import Icon as IconImage

# Currently, this is broken for xz so use our version
#from rpmUtils.miscutils import rpm2cpio
from pkgdb.lib.utils import rpm2cpio

log = logging.getLogger(__name__)

RE_APP_ICON_FILE = re.compile(
        "^.*/(icons|pixmaps)/([^/]*)/(\d+x\d+)/apps/([^/]*)\.png$")
RE_LIBFILE = re.compile("^/usr/lib(64)?/.*\.(la|so(\.\d+)*)$")
RE_IMGFILE = re.compile("^/usr/share/.*\.png$")
ARCHLIST = ['x86_64', 'ia32e', 'athlon', 'i686', 'i586', 'i486', 'i386', 'noarch']

class RPMDownloadError(Exception):
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)


class YumProxyError(Exception):
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)


class YumProxy(object):
 
    def __init__(cls, cachedir='/var/tmp/'):
        cls._yumbase = None
        cls.cachedir = getCacheDir(cachedir)
        if not cls.cachedir:
            raise YumProxyError('Unable to setup yum cache directory.')


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

    def add_repo(self, repo_id, mirror, url, archlist=ARCHLIST):
        self.yumbase.repos.disableRepo('*')
        repopath = '%s%s' % (mirror, url)
        log.debug('Enabling repo: %s (%s)' % (repo_id, repopath))
        # the repo id needs to be str (not unicode), 
        # rpm header paths will be refused by rpm otherwise
        self.yumbase.add_enable_repo(str('%s' % repo_id), [str(repopath)])
        _yumrepo = self.yumbase.repos.getRepo('%s' % repo_id)

        # populate sack
        try:
            self.yumbase._getSacks(thisrepo=_yumrepo.id, archlist=archlist)
        except:
            exc_class, exc, tb = sys.exc_info()
            e = YumProxyError('Repo %s failed to read! (%s)' % (_yumrepo, exc))
            raise e.__class__, e, tb

        return _yumrepo

    def builds_by_name(self, repo_id, names):
        repo = self.yumbase.repos.getRepo(repo_id)
        sack = repo.getPackageSack()
        sack.printPackages()
        return sack.searchNames(names)
        

class RPM(object):
    '''

    Note: RPM objects store their strings as byte strings.  This is because we
    can't tell here what we're going to do with the data.  At some point you
    may need to transform the data from bytes into unicode.
    '''
    
    def __init__(self, build, yumbase):
        """RPM object with some special features.
        :args build: YumAvailablePackage instance
        :args yum_proxy: YumProxy instance
        """
    
        self.build = build
        self._cpio = None
        self._fdno = None
        self._hdr = None
        self.yumbase = yumbase
        #self.yumrepo = self.yumbase.repos.getRepo(self.build.repoid)
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


    def _download_rpm(self):
        try:
            log.info("          Downloading...")
            self.yumbase.downloadPkgs([self.build])
            filename = self.build.localPkg()
        except:
            exc_class, exc, tb = sys.exc_info()
            e = RPMDownloadError(exc)
            raise e.__class__, e, tb

        return filename


    def _download_header(self):
        try:
            log.info("          Downloading header...")
            self.yumbase.downloadHeader(self.build)
        except:
            exc_class, exc, tb = sys.exc_info()
            e = RPMDownloadError(exc)
            raise e.__class__, e, tb

        return 
        


    @property
    def archive(self):
        """ Open an load rpm file and return the enclosed CpioArchive object.
            The requestor is responsible for closing the archive.
        """

        if not self._cpio:
            filename = self.build.localPkg()
            if not os.path.exists(filename):
                filename = self._download_rpm()

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
                e = RPMDownloadError("Invalid RPM file (%s). Yum cache broken?" % exc)
                raise e.__class__, e, tb
            self._cpio = cpio

        # Back to the beginning of the file
        self._cpio.seek(0)

        archive = CpioArchive(fileobj=self._cpio)
        self._issued_arch_closes.append(archive.close)

        return archive

    @property
    def hdr(self):
        if not self._hdr:
            self._download_header()
            self._hdr = self.build.returnLocalHeader()
        return self._hdr
        

    @property
    def executables(self):
        files = self.hdr['filenames']
        filemodes = self.hdr['filemodes']
        filetuple = zip(files, filemodes)

        for f in filetuple:
            if RE_LIBFILE.match(f[0]) or RE_IMGFILE.match(f[0]):
                continue
            if f[1] & S_IEXEC and not f[1] & S_IFDIR:
                try:
                    f[0].decode('utf-8')
                    yield f[0]
                except UnicodeDecodeError, e:
                    log.warn('Wrong filename encoding %s: %s' % (f[0], e))


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
        
    @property
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
    summary = property(lambda self: self.build.summary)
    description = property(lambda self: self.build.description)

    requires_with_pre = property(lambda self: self.build._requires_with_pre())


