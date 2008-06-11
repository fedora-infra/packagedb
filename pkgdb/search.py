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

    @expose(template='pkgdb.templates.overview', allow_json=True)
    def index(self):
        '''Redirects to a page that displays all packages.
        '''  
        redirect("/search/package/0/")

    @expose(template='pkgdb.templates.search', allow_json=True)
    @validate(validators={'release':Int()})
    @paginate('packages', default_order=['package.name','collectionid'], 
            limit=50, max_pages=13)
    def package(self, searchon='both', release=0, operator='AND', 
                        searchwords=''):
        
        '''Searches for packages

           This method returns a list of packages (PackageListing objects)
           matching the given search words. Other information useful in the
           view is also returned: 
           :query: words that were used for the search
           :count: number of packages
           :release: long name of the release
           :searchon: same as the argument, unchanged
           :names: list of all the different package names that were found
           :packages: a nested list of pkglistings grouped by package name
 
           Arguments:
           :searchwords: this can be one or more words which will be used to
           search in the packages' name and description for matches. If absent,
           all packages from all collections will be returned.
           :release: if the number is a valid PackageListing.collectionid, the
           search will be limited to that release. Otherwise (eg "0"),
           the search will return packages from all releases.
           :searchon: area of the search, should be one of: description, name, 
           both
        '''
        
        # get an array of different words to search (case insensitive)
        query = searchwords.lower().split() 
       
        if operator == 'OR':
            # make the string array SQL-ready 
            # we only get exact matches without this - which could be useful?
            for i in range(0,len(query)):
                query[i] ='%' + query[i] + '%'
            matches = []
            if searchon == 'description':
                for i in query:
                    matches +=model.PackageListing.query.filter(and_(
                               model.PackageListing.packageid==model.Package.id,
                                func.lower(model.Package.description).like(i)))
            elif searchon == 'name':
                for i in query:
                    matches +=model.PackageListing.query.filter(and_(
                               model.PackageListing.packageid==model.Package.id,
                                func.lower(model.Package.name).like(i)))
            else:
                for i in query:
                    matches +=model.PackageListing.query.filter(and_(
                               model.PackageListing.packageid==model.Package.id,
                                or_(func.lower(model.Package.name).like(i),
                                func.lower(model.Package.description).like(i))))
                
        else:      # AND operator
            # create the SQL-ready query as a string
            query = '%' + string.join(query, '%') + '%'
        
            if searchon == 'description':
                matches = model.PackageListing.query.filter(and_(
                    model.PackageListing.packageid==model.Package.id,
                        func.lower(model.Package.description).like(query)))
            elif searchon == 'name':
                matches=model.PackageListing.query.filter(and_(
                    model.PackageListing.packageid==model.Package.id,
                        func.lower(model.Package.name).like(query)))
            else:
                matches=model.PackageListing.query.filter(and_(
                    model.PackageListing.packageid==model.Package.id,or_(
                        func.lower(model.Package.name).like(query),
                            func.lower(model.Package.description).like(query))))
        
        # return only the packages in known collections or all of them
        num_of_colls = sqlalchemy.select([model.PackageListing.collectionid], 
                                    distinct=True).execute().rowcount
        if release in range(1,num_of_colls):
           matches = matches.filter(model.PackageListing.collectionid==release)
           # this is a way to get the name and version of the release 
           # even when the search has no matches:
           collection_helper = model.PackageListing.query.filter(
               model.PackageListing.collectionid==release).first().collection
           release = collection_helper.name + ' ' + collection_helper.version
        else:
           release = 'all'
        # return a list of all the package names
        names = []
        for i in matches:
            names.append(i.package.name)
        names = set(names)
        
        packages = []         
        def f(x): return x.package.name == pkg_name
        for pkg_name in names:
            arr = []
            for pkgl in filter(f, matches):
                arr.append(pkgl)
            packages.append(arr)
         
        count = len(packages)
        
        return dict(title=self.appTitle + ' -- Search packages for: ' 
                                                        + searchwords,
                   query=searchwords,
                   packages=packages,
                   count=count,
                   release=release,
                   searchon=searchon,
                   names=names)
