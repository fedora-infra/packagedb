# -*- coding: utf-8 -*-
#
# Copyright © 2007  Red Hat, Inc. All rights reserved.
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
Controller for showing Package Collections.
'''

import sqlalchemy
### FIXME: Get rid of this with TurboGears 1.0.4
from sqlalchemy.ext.selectresults import SelectResults
import sqlalchemy.mods.selectresults

from turbogears import controllers, expose, paginate, config, redirect
from turbogears.database import session

from pkgdb import model

class Collections(controllers.Controller):
    def __init__(self, fas, appTitle):
        '''Create a Packages Controller.

        :fas: Fedora Account System object.
        :appTitle: Title of the web app.
        '''
        self.fas = fas
        self.appTitle = appTitle

    @expose(template='pkgdb.templates.collectionoverview', allow_json=True)
    def index(self):
        '''List the Collections we know about.
        '''
        collections = session.query(model.CollectionPackage).order_by(
                (model.CollectionPackage.c.name,
                    model.CollectionPackage.c.version))

        return dict(title=self.appTitle + ' -- Collection Overview',
                collections=collections)

    @expose(template='pkgdb.templates.collectionpage', allow_json=True)
    @paginate('packages', default_order='name', limit=100,
            allow_limit_override=True, max_pages=13)
    def id(self, collectionId):
        '''Return a page with information on a particular Collection
        '''
        try:
            collectionId = int(collectionId)
        except ValueError:
            error = dict(status = False,
                    title = self.appTitle + ' -- Invalid Collection Id',
                    message = 'The collectionId you were linked to is not a' \
                            ' valid id.  If you received this error from a' \
                            ' link on the fedoraproject.org website, please' \
                            ' report it.')
            if not ('tg_format' in request.params and
                    request.params['tg_format'] == 'json'):
                error['tg_template'] = 'pkgdb.templates.errors'
                return error

        ### FIXME: Want to return additional info:
        # date it was created (join log table: creation date)
        # The initial import doesn't have this information, though.
        try:
            collectionEntry = model.Collection.filter_by(id=collectionId).one()
        except sqlalchemy.exceptions.InvalidRequestError, e:
            # Either the id doesn't exist or somehow it references more than
            # one value
            error = dict(status = False,
                    title = self.appTitle + ' -- Invalid Collection Id',
                    message = 'The collectionId you were linked to, %s, does' \
                            ' not exist.  If you received this error from a' \
                            ' link on the fedoraproject.org website, please' \
                            ' report it.' % collectionId)
            if not ('tg_format' in request.params and
                    request.params['tg_format'] == 'json'):
                error['tg_template'] = 'pkgdb.templates.errors'
                return error

        # Get real ownership information from the fas
        user = self.fas.person_by_id(collectionEntry.owner)
        ownerName = '%s (%s)' % (user['human_name'],
                user['username'])

        # Why do we reformat the data returned from the database?
        # 1) We don't need all the information in the collection object
        # 2) We need ownerName and statusname which are not in the specific
        #    table.
        collection = {'name': collectionEntry.name,
                'version': collectionEntry.version,
                'owner': collectionEntry.owner,
                'ownername': ownerName,
                'summary': collectionEntry.summary,
                'description': collectionEntry.description,
                'statusname': collectionEntry.status.translations[0].statusname
                }

        # Retrieve the packagelist for this collection
        ### FIXME: Remove all SelectResults
        # SA-0.4 deprecates SelectResults
        # TurboGears 1.0.4 will support using orm.query for paginate instead
        # Should be able to just switch the lines defining packages when that
        # happens.
        # packages = session.query(model.Package).filter(
        #         sqlalchemy.and_(
        #             model.PackageListing.c.collectionid==collectionId,
        #             model.PackageListing.c.packageid==model.Package.c.id)
        #         )
        packages = SelectResults(session.query(model.Package)).select(
                sqlalchemy.and_(model.PackageListing.c.collectionid==collectionId,
                    model.PackageListing.c.packageid==model.Package.c.id)
                )
        return dict(title='%s -- %s %s' % (self.appTitle, collection['name'],
            collection['version']), collection=collection, packages=packages)
