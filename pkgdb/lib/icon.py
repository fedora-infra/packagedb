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
icon manipulation library
'''
import Image
import re
from StringIO import StringIO

RE_THEME_IN_PATH = re.compile(r'share/icons/([^/]*)/')
RE_NAME_IN_PATH = re.compile(r'/([^/]+)\.png$')


class Icon(object):
    """Class represents icon image with name and theme.

    It can parse name and theme from filepath.
    Export with resize is available.
    """

    def __init__(self, name, data, theme='default'):
        self.img = Image.open(data)
        self.name = name
        self.theme = theme


    @classmethod
    def from_filename(self, filename, data):
        """Create Icon object.

        Try to guess theme and icon name from filepath

        :arg filename: full filename (with path)
        :arg data: open file that holds PNG image
        :returns: Icon onject
        """
        # theme
        match = RE_THEME_IN_PATH.search(filename)
        if match:
            theme = match.groups()[0]
        else:
            theme = 'default'

        # name
        match = RE_NAME_IN_PATH.search(filename)
        name = match.groups()[0]

        return self(name, data, theme)


    def __str__(self):
        return 'Icon(%r, theme=%r, size=%r)' % (
            self.name, self.theme, self.size)
       

    def export(self, size=None):
        """Export Icon 

        :arg size: (optional) if specified, resize during export.
        :returns: open file with PNG image
        """
        if size is None:
            size = self.size

        data = StringIO()

        if self.size == size:
            ex_img = self.img
        else:
            ex_img = self.img.copy()
            ex_img.thumbnail((48, 48), Image.ANTIALIAS)

        ex_img.save(data, "PNG")
        data.seek(0)

        return data
    
    @property
    def size(self):
        return max(self.img.size)


    def check(self):
        """Check if we can process the image.
        """
        self.img.load()
    
    @property
    def group_key(self):
        return "%s:%s" % (self.name, self.theme)

