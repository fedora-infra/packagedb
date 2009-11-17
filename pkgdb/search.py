# -*- coding: utf-8 -*-
#
# Copyright © 2008  Ionuț Arțăriși
# Copyright © 2008, 2009  Red Hat, Inc.
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

#
# Pylint Explanations
#

# :E1101: SQLAlchemy monkey patches the mapper classes with the database fields
#   so we have to diable this all over.
# :E1103: Since pylint doesn't know about the query method of the mapped
#   classes, it doesn't know what type is returned.  Because of that it doesn't
#   know that we have a filter() method on the returned type.

from sqlalchemy.sql import func, and_, select
from turbogears import controllers, expose, validate, paginate, redirect
from turbogears.validators import Int

from pkgdb.model import Collection, Package, PackageBuild, Repo
from pkgdb.utils import STATUS
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
        # pylint: disable-msg=E1101
        # a little helper so we don't have to write/update form selects manually
        collections = select([Collection.id,
                    Collection.name, Collection.version]).execute()
        # pylint: enable-msg=E1101
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
                    descriptions += PackageBuild.query.join(
                        PackageBuild.package).filter(and_(
                            PackageBuild.statuscode!=
                                STATUS['Removed'].statuscodeid,
                            Package.statuscode!=STATUS['Removed'].statuscodeid,
                            func.lower(Package.description).like(
                                '%' + searchword + '%')))
                elif searchon in ['name', 'both']:
                    exact += PackageBuild.query.filter_by(name=searchword
                            ).filter(PackageBuild.statuscode!= \
                                    STATUS['Removed'].statuscodeid)
                    names += PackageBuild.query.filter(and_(
                        PackageBuild.statuscode!= \
                                STATUS['Removed'].statuscodeid,
                    func.lower(PackageBuild.name).like('%'+searchwords+'%')))
                    if searchon == 'both':
                        descriptions += PackageBuild.query.join(
                            PackageBuild.package).filter(and_(
                                    PackageBuild.statuscode!= \
                                            STATUS['Removed'].statuscodeid,
                                    Package.statuscode!= \
                                            STATUS['Removed'].statuscodeid,
                                            func.lower(Package.description
                                                ).like('%'+searchwords+'%')))
        else: # AND operator
            if searchon in ['name', 'both']:
                exact = PackageBuild.query.filter_by(name=query).filter(
                        PackageBuild.statuscode!=STATUS['Removed'].statuscodeid)
                # query the db for every searchword and build a Query object
                # to filter succesively
                query = query.split()
                names = PackageBuild.query.filter(and_(
                    PackageBuild.statuscode!= \
                            STATUS['Removed'].statuscodeid,
                            func.lower(PackageBuild.name).like(
                                '%' + query[0] + '%')))
                for searchword in query:
                    names = names.filter(func.lower(PackageBuild.name).like(
                        '%' + searchword + '%'))
                if searchon == 'both':
                    descriptions = PackageBuild.query.join(
                        PackageBuild.package).filter(and_(
                                PackageBuild.statuscode!= \
                                        STATUS['Removed'].statuscodeid,
                                Package.statuscode!= \
                                        STATUS['Removed'].statuscodeid,
                                func.lower(Package.description).like(
                                    '%' + query[0] + '%')))
                    for searchword in query:
                        descriptions = descriptions.filter(func.lower(
                            Package.description).like('%'+searchword+'%'))
                    descriptions = descriptions
            elif searchon == 'description':
                query = query.split()
                descriptions = PackageBuild.query.join(
                    PackageBuild.package).filter(and_(
                            PackageBuild.statuscode!= \
                                    STATUS['Removed'].statuscodeid,
                            Package.statuscode!= \
                                    STATUS['Removed'].statuscodeid,
                            func.lower(Package.description).like(
                                '%' + searchwords + '%')))

#                for searchword in query:
#                    # pylint: disable-msg=E1103
#                    descriptions = descriptions.filter(
#                            func.lower(Package.description).like(
#                                '%' + searchword + '%'))
#                descriptions = descriptions.all()

        # Return a list of all packages but keeping the order
        buildset = set()
        for group in [exact, names, descriptions]:
            if group:
                for b in group.join(PackageBuild.repo).filter(
                    Repo.collectionid==collection).all():
                    buildset.add(b)

        active_collection = Collection.query.filter_by(id=collection).one()
        # transform the set into a list again
        builds = []
        while buildset:
            builds.append(buildset.pop())

        # dictionary of buildname : [repolist]
        buildrepos = {}
        for build in builds:
            buildrepos[build.name] = Repo.query.join(Repo.collection).join(
                Repo.builds).filter(and_(PackageBuild.name==build.name,
                                         Collection.id==collection)).all()

        collections = Collection.query.all()

        return dict(title=_('%(app)s -- Search packages for: %(words)s')
                    % {'app': self.app_title, 'words': searchwords},
                    query=searchwords,
                    builds=builds,
                    buildrepos=buildrepos,
                    collections=collections,
                    active_collection=active_collection,
                    searchon=searchon,
                    operator=operator)
