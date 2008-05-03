# -*- coding: utf-8 -*-
#
# Copyright © 2008  Ionuț Arțăriși
# Copyright © 2008  Red Hat, Inc.
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
# Author(s): Ionuț Arțăriși <mapleoin@lavabit.com>
#            Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Controller to search for packages and users.
'''

import sqlalchemy
from sqlalchemy.sql import and_, or_

from turbogears import controllers, expose, paginate, config, \
        redirect, identity
from turbogears.database import session
from cherrypy import request

from pkgdb import model
from fedora.tg.util import request_format

ORPHAN_ID = 9900

class Search(controllers.Controller):
    '''Controller for searching the pkgdb.
    '''
    def __init__(self, fas, appTitle):
        '''Create a Search Controller.

        :fas: Fedora Account System object.
        :appTitle: Title of the web app.
        '''
        self.fas = fas
        self.appTitle = appTitle

    @expose(template='pkgdb.templates.search')
    def index(self):
    # should redirect to pkgdb/packages
        return dict(title=self.appTitle + ' -- All packages')

    @expose(template='pkgdb.templates.search')
    def package(self, release, searchwords=''):
   
        matches = model.PackageListing.query.filter(and_(
            model.PackageListing.packageid==model.Package.id,or_(
                model.Package.name.like('%'+searchwords+'%'),
                    model.Package.description.like('%'+searchwords+'%'))))
        if int(release) in range(1,10):
           matches = matches.filter(model.PackageListing.collectionid==release)

        count = matches.count() 
         #if not matches.all() == []:
        #    matches = 'No matches found'
             # We don't want EOL releases, filter those out of each clause
   #     query = query.join(['listings', 'collection']).filter(
   #                 model.Collection.c.statuscode != self.EOLStatusId)

        return dict(title=self.appTitle + ' -- Search packages for: ' + searchwords,
                   matches=matches,
                   count=count)
