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

STATUS = {}
fas = None
LOG = None
bugzilla = None
admin_grp = None
pkger_grp = None

def to_unicode(obj, encoding='utf-8', errors='strict'):
    '''

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

class GroupCache(dict):
    '''Naive cache for group information.

    This cache can go out of date so use with caution.

    Since there's only a few groups that we retrieve information for, we
    cache individual groups on demand.
    '''
    def __init__(self, fas):
        super(GroupCache, self).__init__()
        self.fas = fas

    def __getitem__(self, group):
        '''Retrieve a group for a groupid or group name.

        First read from the cache.  If not in the cache, refresh from the
        server and try again.

        If the group does not exist then, KeyError will be raised.
        '''
        if isinstance(group, basestring):
            group = group.strip()
        if not group:
            # If the key is just whitespace, raise KeyError immediately,
            # don't try to refresh the cache
            raise KeyError(group)

        if group not in self:
            LOG.debug('GroupCache queries FAS')
            if isinstance(group, basestring):
                try:
                    group_data = self.fas.group_by_name(group)
                except AppError, e:
                    raise KeyError(e.message)
            else:
                group_data = self.fas.group_by_id(group)
                if not group_data:
                    # Unfortunately, this method doesn't yet raise an
                    # exception on bad id.  Instead it returns an empty record
                    raise KeyError(_('Unable to find group id %(id)s') %
                            {'id': group})
            self[group_data.name] = group_data
            self[group_data.id] = group_data

        return super(GroupCache, self).__getitem__(group)

class UserCache(dict):
    '''Naive cache for user information.

    This cache can go out of date so use with caution.
    '''
    def __init__(self, fas):
        super(UserCache, self).__init__()
        self.fas = fas
        # Force a refresh on startup so we don't have a delay the first time
        # someone retrieves a page.
        self.force_refresh()

    def force_refresh(self):
        '''Refetch the userid mapping from fas.
        '''
        LOG.debug('UserCache refresh forced')
        people = self.fas.people_by_id()
        self.clear()
        self.update(people)
        # Note: no collisions because userid is an int and username is a string.
        for user_id in people:
            self[people[user_id]['username']] = people[user_id]

    def __getitem__(self, user_id):
        '''Retrieve a user for a userid or username.

        First read from the cache.  If not in the cache, refresh from the
        server and try again.

        If the user does not exist then, KeyError will be raised.
        '''
        try:
            user_id = user_id.strip()
        except AttributeError: # pylint: disable-msg=W0704
            # If this is a string, strip leading and trailing whitespace.
            # If it's a number there's no difficulty.
            pass
        if user_id not in self:
            if not user_id:
                # If the key is just whitespace, raise KeyError immediately,
                # don't try to refresh the cache
                raise KeyError(user_id)
            LOG.debug('refresh forced for %s' % user_id)
            self.force_refresh()
        return super(UserCache, self).__getitem__(user_id)

def refresh_status():
    '''Cache the status types for use in all methods.
    '''
    global STATUS
    statuses = {}
    for status in StatusTranslation.query.all():
        statuses[status.statusname] = status
    STATUS = statuses

def shutdown():
    pass

def startup():
    # Things to do on startup
    refresh_status()
    global fas, LOG, bugzilla, admin_grp, pkger_grp
    LOG = logging.getLogger('pkgdb.controllers')

    # Get the admin group if one is specified.
    admin_grp = config.get('pkgdb.admingroup', 'cvsadmin')

    # Get the packager group if one is specified.
    pkger_grp = config.get('pkgdb.pkgergroup', 'packager')

# Get a connection to the Account System server
    fas_url = config.get('fas.url', 'https://admin.fedoraproject.org/accounts/')
    username = config.get('fas.username', 'admin')
    password = config.get('fas.password', 'admin')

    fas = AccountSystem(fas_url, username=username, password=password,
            cache_session=False)
    fas.cache = UserCache(fas)
    fas.group_cache = GroupCache(fas)

    # Get a connection to bugzilla
    bz_server = config.get('bugzilla.queryurl', config.get('bugzilla.url',
        'https://bugzilla.redhat.com'))
    bz_url = bz_server + '/xmlrpc.cgi'
    bz_user = config.get('bugzilla.user')
    bz_pass = config.get('bugzilla.password')
    bugzilla = Bugzilla(url=bz_url, user=bz_user, password=bz_pass,
            cookiefile=None)

__all__ = [STATUS, LOG, fas, bugzilla, refresh_status, startup, to_unicode]
