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

from turbogears import controllers, expose, config, flash
from turbogears import identity, redirect
from cherrypy import request, response

from fedora.tg.util import request_format

from pkgdb import release, _

from pkgdb.listqueries import ListQueries
from pkgdb.collections import Collections
from pkgdb.packages import Packages
from pkgdb.users import Users
from pkgdb.stats import Stats
from pkgdb.search import Search

from fedora.tg import controllers as f_ctrlers

class Root(controllers.RootController):
    '''Toplevel controller for the PackageDB

    All URLs to be served must be mounted somewhere under this controller.
    '''
    # Controller methods don't need an __init__()
    # pylint: disable-msg=W0232
    app_title = 'Fedora Package Database'

    collections = Collections(app_title)
    packages = Packages(app_title)
    users = Users(app_title)
    stats = Stats(app_title)
    search = Search(app_title)
    lists = ListQueries(app_title)
    # For backwards compatibility:
    acls = lists

    @expose(template="pkgdb.templates.login")
    def login(self, forward_url=None, *args, **kwargs):
        login_dict = f_ctrlers.login(forward_url=forward_url, *args, **kwargs)
        login_dict['title'] = 'Login to the PackageDB'
        return login_dict

    @expose(allow_json=True)
    def logout(self):
        return f_ctrlers.logout()

    @expose(template='pkgdb.templates.overview')
    def index(self):
        '''Overview of the PackageDB.

        This page serves as an overview of the entire PackageDB.  It needs to
        tell developers where to get more information on their packages.
        '''
        return dict(title=self.app_title, version=release.VERSION)
