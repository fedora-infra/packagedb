# -*- coding: utf-8 -*-
#
# Copyright © 2007-2013  Red Hat, Inc.
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
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Root Controller for the PackageDB.  All controllers are mounted directly or
indirectly from here.
'''
#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.
# :W0232: Controller methods don't need an __init__()

from turbogears import controllers, expose, redirect
from turbogears.database import session
from sqlalchemy.orm import eagerload
from sqlalchemy.sql.expression import and_

from pkgdb import release, _

import logging
log = logging.getLogger(__name__)

from pkgdb.collections import Collections
from pkgdb.acls import Acls
from pkgdb.listqueries import ListQueries
from pkgdb.packages import Package
from pkgdb.stats import Stats
from pkgdb.search import Search
from pkgdb.users import Users
from pkgdb.semantic import DoapController

from pkgdb.model import PackageBuild

from fedora.tg import controllers as f_ctrlers


class Root(controllers.RootController):
    '''Toplevel controller for the PackageDB

    All URLs to be served must be mounted somewhere under this controller.
    '''
    # Controller methods don't need an __init__()
    #pylint:disable-msg=W0232
    app_title = _('Fedora Package Database')

    acls = Acls(app_title)
    collections = Collections(app_title)
    lists = ListQueries(app_title)
    packages = Package(app_title)
    stats = Stats(app_title)
    search = Search(app_title)
    users = Users(app_title)
    doap = DoapController()

    @expose(template="pkgdb.templates.login", allow_json=True)
    def login(self, forward_url=None, *args, **kwargs):
        login_dict = f_ctrlers.login(forward_url=forward_url, *args, **kwargs)
        login_dict['title'] = _('Login to the PackageDB')
        return login_dict

    @expose(allow_json=True)
    def logout(self):
        return f_ctrlers.logout()

    @expose(template='pkgdb.templates.home')
    def index(self):
        '''Overview of the PackageDB.

        This page serves as an overview of the entire PackageDB.
        '''
        fresh = PackageBuild.most_fresh(5)

        return dict(title=self.app_title, version=release.VERSION,
            pattern='', fresh=fresh)

    @expose(template='pkgdb.templates.home')
    def search_dispatcher(self, pattern='', submit=''):

        if submit == 'Builds':
            redirect('/builds/search/%s' % pattern)
        elif submit == 'Applications':
            redirect('/apps/search/%s' % pattern)
        elif submit == 'Packages':
            redirect('/acls/list/*%s*' % pattern)

        redirect('/')

    @expose(content_type='application/xml',
        template='pkgdb.templates.opensearch')
    def opensearch(self, xmlfile):

        if xmlfile == 'pkgdb_packages.xml':
            return dict(shortname='Packages', url='/acls/list/',
                param='searchwords', example='kernel',
                stars=True)
        elif xmlfile == 'pkgdb_apps.xml':
            return dict(shortname='Apps', url='/apps/search',
                param='pattern', example='nethack',
                stars=False)
        elif xmlfile == 'pkgdb_builds.xml':
            return dict(shortname='Builds', url='/builds/search',
                param='pattern', example='kernel',
                stars=False)

        redirect('/')
