# -*- coding: utf-8 -*-
#
# Copyright © 2008  Ionuț Arțăriși
# Copyright © 2008, 2009  Red Hat, Inc.
# Copyright (C) 2012 Frank Chiulli
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
#            Frank Chiulli <frankc.fedora@gmail.com>
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

from pkgdb.model import Collection, Package, PackageBuild, PackageListing, \
                        Repo
from pkgdb.model import CollectionTable, PackageTable, PackageBuildTable, \
                        ReposTable
from pkgdb.lib.sort import get_collection_info
from pkgdb.lib.utils import STATUS
from pkgdb import _


COLLECTION = 21
#
# Fedora devel
#
COLLECTION_ID = 8

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

        # a little helper so we don't have to write/update form selects
        # manually
        collection_list = []
        collection_list = get_collection_info()

        #pylint:enable-msg=E1101
        return dict(title=_('%(app)s -- Advanced Search') % {
                    'app': self.app_title}, collections=collection_list,
                    collection_id=COLLECTION_ID, searchwords='', operator='AND',
                    searchon='both')

    @expose(template='pkgdb.templates.search', allow_json=True)
    @validate(validators={'collection':Int()})
    @paginate('builds', limit=20, max_pages=13)
    def package(self, searchwords='', collection=COLLECTION, searchon='both',
                operator='AND'):
        '''Searches for packagebuilds

        This method returns a list of packages that match the given
        searchwords.  Other information useful to the view is also returned:
        :query: words that were used for the search, unchanged
        :active_collection: the matching Collection object
        :collections: all the Collections in the pkgdb
        :builds: a list of all the found PackageBuilds
        :buildrepos: a dictionary of 'buildname': list of corresponding Repo
                     key-value pairs.
        :operator: 'AND'/'OR' unchanged
        :searchon: same as the argument, unchanged

        :kwarg collection: id of a collection
        :kwarg searchon: where to search; one of: 'description', 'name' or
                         'both'
        :kwarg operator: 'AND' or 'OR'
        :kwarg searchwords: one or more words which will be used to search for
        matches. 
        '''

        if searchwords == '' or searchwords.isspace():
            raise redirect('/search/')

        # case insensitive
        swords = searchwords.lower()

        descriptions, names, exact = [], [], []
        desc_query = ''
        name_query = ''
        exact_query = ''
        if operator == 'OR':
            swords = swords.split()
            desc_query = select((PackageBuild.name,
                                 Package.summary),
                                 and_(PackageBuild.packageid == Package.id,
                                      Package.statuscode != STATUS['Removed']
                                     ),
                                 use_labels=True
                                )
            for searchword in swords:
                if searchon == 'description':
                    #pylint:disable-msg=E1101
                    pattern = '%' + searchword + '%'
                    desc_query = desc_query.where(func.lower(
                                                  Package.description).\
                                                      like(pattern))

                #pylint:enable-msg=E1101
                elif searchon in ['name', 'both']:
                    #pylint:disable-msg=E1101
#                    exact += PackageBuild.query.filter_by(name=searchword)
#                    names += PackageBuild.query.filter(func.lower(
#                        PackageBuild.name).like('%'+searchwords+'%'))
                    #pylint:enable-msg=E1101
                    if searchon == 'both':
                        #pylint:disable-msg=E1101
                        desc_query = desc_query.where(
                                         func.lower(Package.description).like(
                                             '%'+searchwords+'%'))
                        #pylint:enable-msg=E1101
        else: # AND operator
            if searchon in ['name', 'both']:
                #pylint:disable-msg=E1101
                # query the db for every searchword and build a Query object
                # to filter succesively
                swords = swords.split()

                #pylint:enable-msg=E1101
                desc_query = select((PackageBuild.name,
                                     Package.summary,
                                     Collection.branchname,
                                     PackageListing.id),
                                     and_(PackageBuild.packageid == Package.id,
                                          Package.statuscode !=
                                              STATUS['Removed'],
                                          Collection.id == collection,
                                          Package.id ==
                                              PackageListing.packageid,
                                          PackageListing.collectionid ==
                                              collection
                                         ),
                                     use_labels=True
                                    )
                if searchon == 'both':
                    #pylint:enable-msg=E1101
                    for searchword in swords:
                        #pylint:disable-msg=E1101
                        pattern = '%' + searchword + '%'
                        desc_query = desc_query.where(
                                         func.lower(Package.description).\
                                             like(pattern))

                        #pylint:enable-msg=E1101

            elif searchon == 'description':
                swords = swords.split()

        # Return a list of all packages but keeping the order
        pkg_list = {}
        for row in desc_query.execute():
            pkg_name = row[PackageBuildTable.c.name]
            pkg_summary = row[PackageTable.c.summary]
            cbname = row[CollectionTable.c.branchname]
            if not pkg_list.has_key(pkg_name):
                pkg_list[pkg_name] = []
                pkg_list[pkg_name].append(pkg_summary)
                pkg_list[pkg_name].append(cbname)
                pkg_list[pkg_name].append({})

        #pylint:disable-msg=E1101
        result = select((CollectionTable,),
                        and_(Collection.id == collection)).execute()
        active_collection = result.fetchone()
        #pylint:enable-msg=E1101
        # transform the set into a list again

        # dictionary of buildname : [repolist]
        buildrepos = {}
        #
        # @paginate does not like dictionaries.  But it does like a list of
        # dictionaries.
        #
        pkgs = []
        pkg_names = pkg_list.keys()
        pkg_names.sort()
        for pkg_name in pkg_names:
            pkg_info = {}
            pkg_info['name'] = pkg_name
            pkg_info['summary'] = pkg_list[pkg_name][0]
            pkg_info['cbname'] = pkg_list[pkg_name][1]

            repos = {}
            repo_query = select((Repo.shortname,),
                                and_(Collection.id == collection,
                                     Collection.id == Repo.collectionid,
                                     Collection.id ==
                                         PackageListing.collectionid,
                                     PackageListing.packageid == Package.id,
                                     Package.name == pkg_name),
                                use_labels = True
                               )
            for row in repo_query.execute():
                sname = row[ReposTable.c.shortname]
                repos[sname] = 1

            pkg_info['repos'] = repos

            pkgs.append(pkg_info)

        #pylint:enable-msg=E1101
        collections = select((CollectionTable,)).execute()
        #pylint:disable-msg=E1101

        return dict(title=_('%(app)s -- Search packages for: %(words)s')
                    % {'app': self.app_title, 'words': searchwords},
                    query=searchwords,
                    builds=pkgs,
                    buildrepos=buildrepos,
                    collections=collections,
                    active_collection=active_collection,
                    searchon=searchon,
                    operator=operator)
