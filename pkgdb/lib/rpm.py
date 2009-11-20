# -*- coding: utf-8 -*-
#
# Copyright © 2007-2009  Red Hat, Inc.
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
# Author(s): Martin Bacovsky <mbacovsk@redhat.com>
#            Toshio Kuratomi <toshio@redhat.com>
#

import os, re
import stat
import rpmUtils
import ConfigParser
from rpmUtils.miscutils import rpm2cpio
from cpioarchive import CpioArchive
from StringIO import StringIO
import Image
import logging
log = logging.getLogger('pkgdb.lib.rpm')

RE_APP_ICON_FILE = re.compile("^.*/(icons|pixmaps).*/apps/([^/]*)\.png$")
RE_SIZED_APP_ICON_FILE = re.compile("^.*/(icons|pixmaps)/([^/]*)/(\d+x\d+)/apps/([^/]*)\.png$")


def _convert_size(size_string):
    size_string_re = re.compile("^(\d+)x\d+$")
    match = size_string_re.match(size_string)

    if not match:
        raise ValueError("%s did not match size regexp" % size_string)

    return match.group(1)

class RPMParser(object):
    """
    Parse RPM file and can return rpm header

        rpm  = RPMParser('my.rpm')

        heder = rpm.header()

    and/or list of parsed .desktop files

        entries = rpm.desktop_entries()
    """

    CHECK_DESKTOP = re.compile(".*\.desktop$")
    


    def __init__(self, filename):
        self.filename = filename
        self._cpio = None
    
    def header(self):
        ts = rpmUtils.transaction.initReadOnlyTransaction()

        fdno = os.open(self.filename, os.O_RDONLY)
        hdr = ts.hdrFromFdno(fdno)
        os.close(fdno)

        return hdr

    def get_archive(self):
        """ Open an rpm file and return the enclosed CpioArchive object.
            The requestor is responsible for closing the archive.
        """

        if not self._cpio:
            fdno = os.open(self.filename, os.O_RDONLY)

            # rpm2cpio won't just output a blob of data, it needs a file.
            # Using StringIO here takes more memory than a tempfile, but
            # should be faster.
            # rpm2cpio closes fdno
            cpio = StringIO()
            rpm2cpio(fdno, out=cpio)
            self._cpio = cpio

        # Back to the beginning of the file
        self._cpio.seek(0)

        archive = CpioArchive(fileobj=self._cpio)

        return archive


    def desktop_entries(self):
        """Parse an rpm file and return parsed desktop files as 
        a list of ConfigParser objects.
        """
        
        archive = self.get_archive()

        # return value
        desktop_entries = []

        for entry in archive:
            if self.CHECK_DESKTOP.match(entry.name):
                # DesktopFile needs a filehandler
                desktop_file = StringIO(entry.read())
                config = ConfigParser.ConfigParser()
                config.readfp(desktop_file)
                desktop_file.close()

                desktop_entries.append(config)

        archive.close()
        return desktop_entries


    def get_app_icons(self, exc=None):
        if exc == None:
            exc = []

        app_icon_data = {}

        archive = self.get_archive()

        for entry in archive:
            #TODO: accept unusual icons mentioned in .desktop
            match = RE_APP_ICON_FILE.match(entry.name)
            if match:

                if stat.S_ISLNK(entry.mode):
                    log.debug("%s is a symlink" % entry.name)
                    continue

                size = 0
                name = match.group(2)

                log.debug("%s has Icon: %s" % (entry.name, name))
                sized_match = RE_SIZED_APP_ICON_FILE.match(entry.name)
                width = 0
                theme = 'default'

                if sized_match:
                    width = _convert_size(sized_match.group(3))
                    theme = sized_match.group(2)

                if not app_icon_data.has_key(name) or width == 48 or app_icon_data[name]['size'][0] < width:
                    data = StringIO(entry.read())
                    img = Image.open(data)
                    data.seek(0)
                    size = img.size

                    log.debug("%s at size %sx%s from path %s" % (name, size[0], size[1], entry.name))

                app_icon_data[name] = dict(size=size, data=data, theme=theme)

        to_delete = []

        # normalize icon size to 48x48
        for name in app_icon_data.keys():
            size = app_icon_data[name]['size']
            if size[0] != 48 or size[1] != 48:
                data = app_icon_data[name]['data']
                log.debug("Resizing %s from %sx%s to 48x48" % (name, size[0], size[1]))
                try:
                    img = Image.open(data)
                    data = StringIO()
                    img.thumbnail((48,48), Image.ANTIALIAS)
                    img.save(data, "PNG")
                except IOError, e:
                    # Occasionally Image can't parse icon data
                    to_delete.append(name)
                    continue

                data.seek(0)
                size=(48,48)
                
                app_icon_data[name] = dict(size=size, theme=app_icon_data[name]['theme'], data=data)

        # delete invalid files
        for name in to_delete:
            # delete the icons Image couldn't parse
            try:
                app_icon_data[name]['data'].close()
            except:
                pass
            del app_icon_data[name]

        return app_icon_data



        
