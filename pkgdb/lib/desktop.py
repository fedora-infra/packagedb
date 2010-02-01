#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
#
# Copyright © 2010  Red Hat, Inc.
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
#
'''
.desktop files related stuff
'''

from ConfigParser import ConfigParser

class DesktopParseError(Exception):
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)

class Desktop(object):
    
    def __init__(self, name, generic_name=None, comment=None,
            target_type='Application', icon_name=None, 
            categories=[], mimetypes=[]):
        self.name = name
        self.generic_name = generic_name
        self.comment = comment
        self.target_type = target_type
        self.icon_name = icon_name
        self.categories = categories
        self.mimetypes = mimetypes


    @classmethod
    def from_file(self, data):
        """initialize Desktop object with data from .desktop file
        :arg data: open .desktop file
        :raises DesktopParseError: on invalid file
        :returns: initialized Desktop object
        """
        try:
            conf = ConfigParser()
            conf.readfp(data)
        except Exception, e:
            raise DesktopParseError('Failed to read .desktop file (%s)' % e)
            
      
        # name
        if conf.has_option('Desktop Entry', 'Name'):
            name = conf.get('Desktop Entry', 'name').title()
        else: 
            raise DesktopParseError('"Name" entry not found')

        # generic_name
        generic_name = ''
        if conf.has_option('Desktop Entry', 'GenericName'):
            generic_name = conf.get('Desktop Entry', 'GenericName')

        # comment
        comment = ''
        if conf.has_option('Desktop Entry', 'Comment'):
            comment = conf.get('Desktop Entry', 'Comment')

        # target_type
        target_type = None
        if conf.has_option('Desktop Entry', 'Type'):
            target_type = conf.get('Desktop Entry', 'Type')

        # icon
        icon_name = None
        if conf.has_option('Desktop Entry', 'Icon'):
            icon_name = conf.get('Desktop Entry', 'Icon').replace('.png','')

        # categories
        categories = set()
        if conf.has_option('Desktop Entry', 'Categories'):
            for c in conf.get('Desktop Entry', 'Categories').split(';'):
                if c.strip():
                    categories.add(c)

        # mimetypes
        mimetypes = set()
        if conf.has_option('Desktop Entry', 'MimeType'):
            for mt in conf.get('Desktop Entry', 'MimeType').split(';'):
                if mt.strip():
                    mimetypes.add(mt)

        return self(name, generic_name=generic_name, 
                comment=comment, icon_name=icon_name,
                target_type=target_type, categories=categories,
                mimetypes=mimetypes)

