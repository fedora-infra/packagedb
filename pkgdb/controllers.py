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
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Root Controller for the PackageDB.  All controllers are mounted directly or
indirectly from here.
'''

from turbogears import controllers, expose, config, flash
from turbogears import identity, redirect
from turbogears.database import session
from sqlalchemy.orm import eagerload
from cherrypy import request, response

from fedora.tg.util import request_format

from pkgdb import release, _

from pkgdb.acls import Acls
from pkgdb.collections import Collections
from pkgdb.comments import Comments
from pkgdb.feeds import ApplicationFeed, CommentsFeed
from pkgdb.listqueries import ListQueries
from pkgdb.packages import Package
from pkgdb.applications import ApplicationController
from pkgdb.stats import Stats
from pkgdb.search import Search
from pkgdb.tag import Tags
from pkgdb.users import Users

from pkgdb.model import PackageBuild, Comment, ApplicationsTable

from fedora.tg import controllers as f_ctrlers

import logging
log = logging.getLogger(__name__)

class Root(controllers.RootController):
    '''Toplevel controller for the PackageDB

    All URLs to be served must be mounted somewhere under this controller.
    '''
    # Controller methods don't need an __init__()
    # pylint: disable-msg=W0232
    app_title = _('Fedora Package Database')

    appfeed = ApplicationFeed()
    commentsfeed = CommentsFeed()
    acls = Acls(app_title)
    collections = Collections(app_title)
    comments = Comments(app_title)
    lists = ListQueries(app_title)
    packages = Package(app_title)
    applications = ApplicationController(app_title)
    stats = Stats(app_title)
    search = Search(app_title)
    tag = Tags(app_title)
    users = Users(app_title)

    @expose(template="pkgdb.templates.login", allow_json=True)
    def login(self, forward_url=None, *args, **kwargs):
        login_dict = f_ctrlers.login(forward_url=forward_url, *args, **kwargs)
        login_dict['title'] = _('Login to the PackageDB')
        return login_dict

    @expose(allow_json=True)
    def logout(self):
        return f_ctrlers.logout()

    @expose(template='pkgdb.templates.overview')
    def index(self):
        '''Overview of the PackageDB.

        This page serves as an overview of the entire PackageDB.  
        '''
        packages = session.query(PackageBuild)\
                .options(eagerload('applications'))\
                .join('applications')\
                .filter(ApplicationsTable.c.apptype == 'desktop')\
                .order_by(PackageBuild.committime.desc()).limit(7).all()

        comments = Comment.query.filter_by(published=True).order_by(
            Comment.time.desc()).limit(7).all()
        
        return dict(packages=packages, comments=comments,
            title=self.app_title, version=release.VERSION)
