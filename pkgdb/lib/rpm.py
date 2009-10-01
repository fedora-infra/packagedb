# -*- coding: utf-8 -*-
#
# Copyright © 2007-2009  Red Hat, Inc. All rights reserved.
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
# Red Hat Author(s): Martin Bacovsky <mbacovsk@redhat.com>
#

import sys, os, re
import rpmUtils
import ConfigParser
from rpmUtils.miscutils import rpm2cpio
from cpioarchive import CpioArchive
from StringIO import StringIO


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
    
    def header(self):
        ts = rpmUtils.transaction.initReadOnlyTransaction()

        fdno = os.open(self.filename, os.O_RDONLY)
        hdr = ts.hdrFromFdno(fdno)
        os.close(fdno)

        return hdr

    def _open_rpm(self):
        """Open an rpm file and return the enclosed CpioArchive object"""

        fdno = os.open(self.filename, os.O_RDONLY)

        # rpm2cpio won't just output a blob of data, it needs a file.
        # Using StringIO here takes more memory than a tempfile, but
        # should be faster.
        # rpm2cpio closes fdno
        cpio = StringIO()
        rpm2cpio(fdno, out=cpio)

        # Back to the beginning of the file
        cpio.seek(0)

        archive = CpioArchive(fileobj=cpio)

        return archive


    def desktop_entries(self):
        """Parse an rpm file and return parsed desktop files
        
        returns a list of ConfigParser objects, or an empty list
        """
        
        archive = self._open_rpm()

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

        return desktop_entries

