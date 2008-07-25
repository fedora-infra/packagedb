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
# Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#            Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Controller to search for packages and eventually users.
'''

import sqlalchemy
from sqlalchemy.sql import func, and_

from turbogears import controllers, expose, validate, paginate
from turbogears.validators import Int

from pkgdb import model

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

    @expose(template='pkgdb.templates.advancedsearch', allow_json=True)
    def index(self):
        '''Advanced package search.

           Provides a form with multiple fields for a comprehensive package
           search.
        '''  
        # a little helper so we don't have to write/update form selects manually
        releases = sqlalchemy.select([model.Collection.id,
                    model.Collection.name, model.Collection.version]).execute()
        return dict(title=self.appTitle + ' -- Advanced Search',
                    releases=releases)

    @expose(template='pkgdb.templates.search', allow_json=True)
    @validate(validators={'release':Int()})
    @paginate('packages', default_order=['package.name','collectionid'], 
            limit=20, max_pages=13)
    def package(self, searchon='both', release=0, operator='AND', 
                        searchwords=''):
        '''Searches for packages

           This method returns a list of packages (PackageListing objects)
           matching the given search words. Other information useful in the
           view is also returned: 
           :query: words that were used for the search, unchanged
           :count: number of packages
           :release: long name of the release
           :searchon: same as the argument, unchanged
           :packages: a nested list of pkglistings grouped by package name
           :collections: a dict of all the available collection branchnames as 
           keys and their corresponding ids 
           :operator: 'AND'/'OR' unchanged
 
           Arguments:
           :searchwords: this can be one or more words which will be used to
           search in the packages' name and description for matches. If absent,
           all packages from all collections will be returned.
           :release: if the number is a valid PackageListing.collectionid, the
           search will be limited to that release. Otherwise (eg "0"),
           the search will return packages from all releases.
           :searchon: area of the search, should be one of: description, name, 
           both
           :operator: can be either 'AND' or 'OR'
        '''

        if searchword == '' or searchword.isspace():
            raise redirect(config.get('base_url_filter.base_url') + '/search')

        # case insensitive
        query = searchwords.lower() 

        if operator == 'OR':
            query = query.split()  # -> list
            descriptions, names, exact = [], [], []
            for searchword in query:
                if searchon == 'description':
                    descriptions += model.PackageListing.query.filter(and_(
                        model.PackageListing.packageid==model.Package.id,
                            func.lower(model.Package.description).like(
                                '%'+searchword+'%')))
                elif searchon in ['name', 'both']:
                    exact += model.PackageListing.query.filter(and_(
                            model.PackageListing.packageid==model.Package.id,
                                func.lower(model.Package.name).like(
                                    searchword)))
                    names += model.PackageListing.query.filter(and_(
                        model.PackageListing.packageid==model.Package.id,
                            func.lower(model.Package.name).like(
                                '%'+searchword+'%')))
                    if searchon == 'both':
                        descriptions += model.PackageListing.query.filter(and_(
                            model.PackageListing.packageid==model.Package.id,
                                func.lower(model.Package.description).like(
                                    '%'+searchword+'%')))

        else:      # AND operator
            descriptions, names, exact = [], [], [] 
            if searchon in ['name', 'both']: 
                exact = model.PackageListing.query.filter(and_(
                    model.PackageListing.packageid==model.Package.id,
                             func.lower(model.Package.name).like(query))).all()
                # query the DB for every searchword and build a Query object
                # to filter succesively
                query = query.split()
                names = model.PackageListing.query.filter(and_(
                            model.PackageListing.packageid==model.Package.id,
                                func.lower(model.Package.name).like(
                                    '%' + query[0] + '%')))
                for searchword in query:
                    names = names.filter(func.lower(model.Package.name).like(
                                            '%' + searchword + '%'))
                names = names.all()
 
                if searchon == 'both':
                    descriptions = model.PackageListing.query.filter(and_(
                        model.PackageListing.packageid==model.Package.id,
                        func.lower(model.Package.description).like(
                            '%' + query[0] + '%')))
                    for searchword in query:
                        descriptions = descriptions.filter(
                                func.lower(model.Package.description).like(
                                    '%' + searchword + '%'))
                    descriptions = descriptions.all()
            elif searchon == 'description':
                query = query.split()
                descriptions = model.PackageListing.query.filter(and_(
                    model.PackageListing.packageid==model.Package.id,
                        func.lower(model.Package.description).like(
                           '%' + query[0] + '%')))
                for searchword in query:
                    descriptions = descriptions.filter(
                            func.lower(model.Package.description).like(
                                '%' + searchword + '%'))
                descriptions = descriptions.all()

        # Return a list of all packages but keeping the order
        s = set()   # order and remove duplicates
        packages = []
        for pkgl in exact + names + descriptions:
            if pkgl.package not in s:
                if (not release) or (pkgl.collectionid == release):
                    s.add(pkgl.package)
                    packages.append(pkgl.package)
        count = len(packages)

        collections = {} # build a dict of all the available releases
                         # branchnames as keys and string ids as values
        for coll in model.Collection.query.all():
            collections[coll.branchname] = str(coll.id)
            if coll.id == release:
                release = '%s %s' % (coll.name, coll.version)

        collections["ALL"] = '0'
        if not release:
            release = 'all'

        return dict(title='%s -- Search packages for: %s' %
                (self.appTitle, searchwords),
                   query=searchwords,
                   packages=packages,
                   count=count,
                   release=release,
                   collections=collections,
                   searchon=searchon,
                   operator=operator)
