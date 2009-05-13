# -*- coding: utf-8 -*-
#
# Copyright © 2008  Red Hat, Inc. All rights reserved.
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
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Utilities for all classes to use
'''
import os
import tempfile
import logging

from turbogears import config

from bugzilla import Bugzilla

# The Fedora Account System Module
from fedora.client.fas2 import AccountSystem

from pkgdb.model.statuses import StatusTranslation
from pkgdb import _

STATUS = {}
fas = None
LOG = None
bugzilla = None
# Get the admin group if one is specified.
admin_grp = config.get('pkgdb.admingroup', 'cvsadmin')

# Get the packager group if one is specified.
pkger_grp = config.get('pkgdb.pkgergroup', 'packager')

def to_unicode(obj, encoding='utf-8', errors='strict'):
    '''return a unicode representation of the object.

    :arg obj: object to attempt to convert to unicode.  Note: If this is not
        a str or unicode object then the conversion might not be what
        you want (as it converts the __str__ of the obj).
    :kwarg encoding: encoding of the byte string to convert from.
    :kwarg errors:
        :strict: raise an error if it won't convert
        :replace: replace non-converting chars with a certain char for the
            encoding.  (For instance, ascii substitutes a ?).
        :ignore: silently drop the bad characters

    '''
    if isinstance(obj, unicode):
        return obj
    if isinstance(obj, str):
        return unicode(obj, encoding, errors)
    return unicode(obj)

class UserCache(dict):
    '''Naive cache for user information.

    This cache can go out of date so use with caution.

    Use clear() to remove all entries from the cache.
    Use del cache[username] to remove a specific entry.
    '''
    def __init__(self, fas):
        super(UserCache, self).__init__()
        self.fas = fas

    def __getitem__(self, username):
        '''Retrieve a user for a username.

        First read from the cache.  If not in the cache, refresh from the
        server and try again.

        If the user does not exist then, KeyError will be raised.
        '''
        username = username.strip()
        if username not in self:
            if not username:
                # If the key is just whitespace, raise KeyError immediately,
                # don't try to pull from fas
                raise KeyError(username)
            LOG.debug(_('refresh forced for %(user)s') % {'user':  username})
            person = fas.person_by_username(username)
            if not person:
                # no value for this username
                raise KeyError(username)
        return super(UserCache, self).__getitem__(username)

def refresh_status():
    '''Cache the status types for use in all methods.
    '''
    global STATUS
    statuses = {}
    for status in StatusTranslation.query.all():
        statuses[status.statusname] = status
    STATUS = statuses

def init_globals():
    '''Initialize global variables.

    This is mostly connections to services like FAS, bugzilla, and loading
    constants from the database.
    '''
    # Things to do on startup
    refresh_status()
    global fas, LOG, bugzilla, admin_grp, pkger_grp
    LOG = logging.getLogger('pkgdb.controllers')

    # Get a connection to the Account System server
    fas_url = config.get('fas.url', 'https://admin.fedoraproject.org/accounts/')
    username = config.get('fas.username', 'admin')
    password = config.get('fas.password', 'admin')

    fas = AccountSystem(fas_url, username=username, password=password,
            cache_session=False)
    fas.cache = UserCache(fas)

    # Get a connection to bugzilla
    bz_server = config.get('bugzilla.queryurl', config.get('bugzilla.url',
        'https://bugzilla.redhat.com'))
    bz_url = bz_server + '/xmlrpc.cgi'
    bz_user = config.get('bugzilla.user')
    bz_pass = config.get('bugzilla.password')
    bugzilla = Bugzilla(url=bz_url, user=bz_user, password=bz_pass,
            cookiefile=None)

__all__ = [STATUS, admin_grp, pkger_grp, LOG, fas, bugzilla, refresh_status,
        init_globals, to_unicode]
