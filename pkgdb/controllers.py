# -*- coding: utf-8 -*-
#
# Copyright © 2007-2008  Red Hat, Inc. All rights reserved.
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
Root Controller for the PackageDB.  All controllers are mounted directly or
indirectly from here.
'''

from turbogears import controllers, expose, config
from turbogears.i18n.tg_gettext import gettext as _
from turbogears import identity, redirect
from cherrypy import request, response
import logging

from pkgdb import release

from pkgdb.acls import Acls
from pkgdb.collections import Collections
from pkgdb.packages import Packages
from pkgdb.users import Users
from pkgdb.stats import Stats

log = logging.getLogger("pkgdb.controllers")

# The Fedora Account System Module
from fedora.accounts.fas2 import AccountSystem

class UserCache(dict):
    '''Naive cache for user information.

    This cache can go out of date so use with caution.
    '''
    def __init__(self, fas):
        super(UserCache, self).__init__()
        self.fas = fas

    def force_refresh(self):
        log.debug('UserCache refresh forced')
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
        if user_id not in self:
            self.force_refresh()
        return super(UserCache, self).__getitem__(user_id)

class Root(controllers.RootController):
    '''Toplevel controller for the PackageDB

    All URLs to be served must be mounted somewhere under this controller.
    '''
    appTitle = 'Fedora Package Database'

    baseURL = config.get('fas.url', 'https://admin.fedoraproject.org/accounts/')
    username = config.get('fas.username', 'admin')
    password = config.get('fas.password', 'admin')

    fas = AccountSystem(baseURL, username, password)
    fas.cache = UserCache(fas)

    acls = Acls(fas, appTitle)
    collections = Collections(fas, appTitle)
    packages = Packages(fas, appTitle)
    users = Users(fas, appTitle)
    stats = Stats(fas, appTitle)

    @expose(template='pkgdb.templates.overview')
    def index(self):
        '''Overview of the PackageDB.

        This page serves as an overview of the entire PackageDB.  It needs to
        tell developers where to get more information on their packages.
        '''
        return dict(title=self.appTitle, version=release.VERSION)

    @expose(template="pkgdb.templates.login", allow_json=True)
    def login(self, forward_url=None, previous_url=None, *args, **kwargs):
        '''Page to become authenticated to the PackageDB.

        This shows a small login box to type in your username and password
        from the Fedora Account System.
        
        Arguments:
        :forward_url: The url to send to once authentication succeeds
        :previous_url: The url that sent us to the login page
        '''
        # pylint: disable-msg=R0201
        if not identity.current.anonymous \
                and identity.was_login_attempted() \
                and not identity.get_identity_errors():
            # User is logged in
            if 'tg_format' in request.params \
                    and request.params['tg_format'] == 'json':
                # When called as a json method, doesn't make any sense to
                # redirect to a page.  Returning the logged in identity
                # is better.
                return dict(user = identity.current.user)
            if not forward_url:
                forward_url = config.get('base_url_filter.base_url') + '/'
            raise redirect(forward_url)
        
        forward_url = None
        previous_url = request.path

        if identity.was_login_attempted():
            msg = _("The credentials you supplied were not correct or "
                   "did not grant access to this resource.")
        elif identity.get_identity_errors():
            msg = _("You must provide your credentials before accessing "
                   "this resource.")
        else:
            msg = _("Please log in.")
            forward_url = request.headers.get("Referer", "/")

        response.status=403
        return dict(message=msg, previous_url=previous_url, logging_in=True,
                    original_parameters=request.params,
                    forward_url=forward_url,
                    title='Fedora Account System Login')

    @expose()
    def logout(self):
        '''Logout from the database.
        '''
        # pylint: disable-msg=R0201
        identity.current.logout()
        raise redirect(request.headers.get("Referer","/"))

