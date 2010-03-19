# -*- coding: utf-8 -*-
#
# Copyright © 2008  Ionuț Arțăriși
# Copyright © 2008, 2009  Red Hat, Inc.
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
# Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#            Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Controller to search for packages and eventually users.
'''

#
# Pylint Explanations
#

# :E1101: SQLAlchemy monkey patches the mapper classes with the database fields
#   so we have to diable this all over.

from sqlalchemy.sql import func, and_, select
from turbogears import controllers, expose, validate, paginate, redirect
from turbogears.validators import Int

from pkgdb.model import Collection, Package, PackageBuild, Repo
from pkgdb.lib.utils import STATUS
from pkgdb import _


COLLECTION = 21

class Search(controllers.Controller):
    '''Controller for searching the pkgdb.
    '''
    def __init__(self, app_title):
        '''Create a Search Controller.

        :arg app_title: Title of the web app.
        '''
        self.app_title = app_title

    @expose(template='pkgdb.templates.advancedsearch', allow_json=True)
    def index(self):
        '''Advanced package search.

        Provides a form with multiple fields for a comprehensive package
        search.

        :collections: list of pkgdb collections
        '''
        # a little helper so we don't have to write/update form selects manually
        #pylint:disable-msg=E1101
        collections = select([Collection.id,
                    Collection.name, Collection.version]).execute()
        #pylint:enable-msg=E1101
        return dict(title=_('%(app)s -- Advanced Search') % {
            'app': self.app_title}, collections=collections)

    @expose(template='pkgdb.templates.search', allow_json=True)
    @validate(validators={'collection':Int()})
    @paginate('builds', limit=20, max_pages=13)
    def package(self, searchwords='', collection=COLLECTION, searchon='both',
                operator='AND'):
        '''Searches for packagebuilds

        This method returns a list of PackageBuilds that match the given
        searchwords. Other information useful to the view is also returned:
        :query: words that were used for the search, unchanged
        :active_collection: the matching Collection object
        :collections: all the Collections in the pkgdb
        :builds: a list of all the found PackageBuilds
        :buildrepos: a dictionary of 'buildname': list of corresponding Repo
                     key-value pairs.
        :operator: 'AND'/'OR' unchanged
        :searchon: same as the argument, unchanged

        :kwarg collection: id of a collection
        :kwarg searchon: where to search; one of: 'description', 'name' or 'both'
        :kwarg operator: 'AND' or 'OR'
        :kwarg searchwords: one or more words which will be used to search for
        matches. 
        '''

        if searchwords == '' or searchwords.isspace():
            raise redirect('/search/')

        # case insensitive
        query = searchwords.lower()

        descriptions, names, exact = [], [], []
        if operator == 'OR':
            query = query.split()
            for searchword in query:
                if searchon == 'description':
                    #pylint:disable-msg=E1101
                    descriptions += PackageBuild.query.join(
                        PackageBuild.package).filter(and_(
                            PackageBuild.statuscode!= STATUS['Removed'],
                            Package.statuscode!=STATUS['Removed'],
                            func.lower(Package.description).like(
                                '%' + searchword + '%')))
                #pylint:enable-msg=E1101
                elif searchon in ['name', 'both']:
                    #pylint:disable-msg=E1101
                    exact += PackageBuild.query.filter_by(name=searchword
                            ).filter(PackageBuild.statuscode!= \
                                    STATUS['Removed'])
                    names += PackageBuild.query.filter(and_(
                        PackageBuild.statuscode!= \
                                STATUS['Removed'],
                    func.lower(PackageBuild.name).like('%'+searchwords+'%')))
                    #pylint:enable-msg=E1101
                    if searchon == 'both':
                        #pylint:disable-msg=E1101
                        descriptions += PackageBuild.query.join(
                            PackageBuild.package).filter(and_(
                                    PackageBuild.statuscode!= \
                                            STATUS['Removed'],
                                    Package.statuscode!= \
                                            STATUS['Removed'],
                                            func.lower(Package.description
                                                ).like('%'+searchwords+'%')))
                        #pylint:enable-msg=E1101
        else: # AND operator
            if searchon in ['name', 'both']:
                #pylint:disable-msg=E1101
                exact = PackageBuild.query.filter_by(name=query).filter(
                        PackageBuild.statuscode!=STATUS['Removed'])
                # query the db for every searchword and build a Query object
                # to filter succesively
                query = query.split()
                names = PackageBuild.query.filter(and_(
                    PackageBuild.statuscode!=STATUS['Removed'],
                    func.lower(PackageBuild.name).like(
                        '%' + query[0] + '%')))
                #pylint:enable-msg=E1101
                for searchword in query:
                    #pylint:disable-msg=E1101
                    names = names.filter(func.lower(PackageBuild.name).like(
                        '%' + searchword + '%'))
                    #pylint:enable-msg=E1101
                if searchon == 'both':
                    #pylint:disable-msg=E1101
                    descriptions = PackageBuild.query\
                            .join(PackageBuild.package)\
                            .filter(and_(PackageBuild.statuscode!= \
                                STATUS['Removed'],
                                Package.statuscode!= STATUS['Removed'],
                                func.lower(Package.description)\
                                        .like('%' + query[0] + '%')))
                    #pylint:enable-msg=E1101
                    for searchword in query:
                        #pylint:disable-msg=E1101
                        descriptions = descriptions.filter(func.lower(
                            Package.description).like('%'+searchword+'%'))
                        #pylint:enable-msg=E1101
                    descriptions = descriptions
            elif searchon == 'description':
                #pylint:disable-msg=E1101
                query = query.split()
                descriptions = PackageBuild.query.join(
                    PackageBuild.package).filter(and_(
                            PackageBuild.statuscode!= STATUS['Removed'],
                            Package.statuscode!= STATUS['Removed'],
                            func.lower(Package.description).like(
                                '%' + searchwords + '%')))
                #pylint:enable-msg=E1101

#                for searchword in query:
#                    #pylint:disable-msg=E1103
#                    descriptions = descriptions.filter(
#                            func.lower(Package.description).like(
#                                '%' + searchword + '%'))
#                   #pylint:enable-msg=E1101
#                descriptions = descriptions.all()

        # Return a list of all packages but keeping the order
        buildset = set()
        for group in [exact, names, descriptions]:
            if group:
                #pylint:disable-msg=E1101
                for b in group.join(PackageBuild.repos).filter(
                    Repos.collectionid==collection).all():
                    buildset.add(b)
                #pylint:enable-msg=E1101

        #pylint:disable-msg=E1101
        active_collection = Collection.query.filter_by(id=collection).one()
        #pylint:enable-msg=E1101
        # transform the set into a list again
        builds = []
        while buildset:
            builds.append(buildset.pop())

        # dictionary of buildname : [repolist]
        buildrepos = {}
        for build in builds:
            #pylint:disable-msg=E1101
            buildrepos[build.name] = Repo.query.join(Repo.collection).join(
                Repo.builds).filter(and_(PackageBuild.name==build.name,
                                         Collection.id==collection)).all()
            #pylint:enable-msg=E1101

        collections = Collection.query.all() #pylint:disable-msg=E1101

        return dict(title=_('%(app)s -- Search packages for: %(words)s')
                    % {'app': self.app_title, 'words': searchwords},
                    query=searchwords,
                    builds=builds,
                    buildrepos=buildrepos,
                    collections=collections,
                    active_collection=active_collection,
                    searchon=searchon,
                    operator=operator)
