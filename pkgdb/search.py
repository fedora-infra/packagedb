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
Controller to search for packages and eventually users.
'''
import string

import sqlalchemy
from sqlalchemy.sql import func, and_, or_

from turbogears import controllers, expose, validate, paginate, config, \
        redirect
from turbogears.validators import Int
from turbogears.database import session
from cherrypy import request

from pkgdb import model
from fedora.tg.util import request_format

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

    @expose(template='pkgdb.templates.overview')
    def index(self):
    # should display all packages or redirect to pkgdb/packages 
    #    return dict(title=self.appTitle + ' -- All packages')
        redirect("/search/package/0/")

    @expose(template='pkgdb.templates.search')
    @validate(validators={'release':Int()})
    @paginate('packages', default_order=['package.name','collectionid'], 
            limit=50, max_pages=13)
    def package(self, searchon='both', release=0, searchwords='', and_or='and'):
        # get an array of different words to search 
        # and create the SQL-ready query
        query = searchwords.split() 
        query = '%' + string.join(query, '%') + '%'
        # perform case insensitive searches 
        query = query.lower()
        # searches using AND operator
        if searchon == 'description':
            matches = model.PackageListing.query.filter(and_(
                model.PackageListing.packageid==model.Package.id,
                        func.lower(model.Package.description).like(query)))
        elif searchon == 'names':
            matches=model.PackageListing.query.filter(and_(
                model.PackageListing.packageid==model.Package.id,
                    func.lower(model.Package.name).like(query)))
        else:
            matches=model.PackageListing.query.filter(and_(
                model.PackageListing.packageid==model.Package.id,or_(
                    func.lower(model.Package.name).like(query),
                        func.lower(model.Package.description).like(query))))
        # FIXME searches using OR operator
        
        # return only the packages in known collections or all of them
        if release in range(1,16):
           matches = matches.filter(model.PackageListing.collectionid==release)
           # this is a way to get the name and version of the release 
           # even when the search has no matches:
           collection_helper = model.PackageListing.query.filter(
               model.PackageListing.collectionid==release).first().collection
           release = collection_helper.name + ' ' + collection_helper.version
        else:
           release = 'all'
        count = matches.count() 
        return dict(title=self.appTitle + ' -- Search packages for: ' + query,
                   query=searchwords,
                   packages=matches,
                   count=count,
                   release=release,
                   searchon=searchon)
