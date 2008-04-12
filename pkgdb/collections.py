# -*- coding: utf-8 -*-
#
# Copyright © 2007-2008  Red Hat, Inc. All rights reserved.
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

from turbogears import controllers, expose, paginate
from turbogears.database import session

from pkgdb import model
from cherrypy import request

class Collections(controllers.Controller):
    '''Controller that deals with Collections.

    These are methods that expose Collections to the users.  Collections are
    usually a specific release of a distribution.  For instance, Fedora 8.
    '''
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
        # pylint: disable-msg=E1101
        collections = model.CollectionPackage.query.order_by(
                (model.CollectionPackage.c.name,
                    model.CollectionPackage.c.version))
        # pylint: enable-msg=E1101

        return dict(title=self.appTitle + ' -- Collection Overview',
                collections=collections)

    @expose(template='pkgdb.templates.collectionpage', allow_json=True)
    @paginate('packages', default_order='name', limit=100,
            allow_limit_override=True, max_pages=13)
    def id(self, collectionId): # pylint: disable-msg=C0103
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
            if request.params.get('tg_format', 'html') != 'json':
                error['tg_template'] = 'pkgdb.templates.errors'
            return error

        ### FIXME: Want to return additional info:
        # date it was created (join log table: creation date)
        # The initial import doesn't have this information, though.
        try:
            # pylint: disable-msg=E1101
            collectionEntry = model.Collection.query.filter_by(id=collectionId).one()
        except sqlalchemy.exceptions.InvalidRequestError, e:
            # Either the id doesn't exist or somehow it references more than
            # one value
            error = dict(status = False,
                    title = self.appTitle + ' -- Invalid Collection Id',
                    message = 'The collectionId you were linked to, %s, does' \
                            ' not exist.  If you received this error from a' \
                            ' link on the fedoraproject.org website, please' \
                            ' report it.' % collectionId)
            if request.params.get('tg_format', 'html') != 'json':
                error['tg_template'] = 'pkgdb.templates.errors'
            return error

        # Get ownership information from the fas
        try:
            user = self.fas.cache[collectionEntry.owner]
        except KeyError:
            user = {}
            user['human_name'] = 'Unknown'
            user['username'] = 'User ID %i' % collectionEntry.owner
            user['email'] = 'unknown@fedoraproject.org'
        ownerName = '%(human_name)s (%(username)s)' % user

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
        packages = model.Package.query.filter(
                sqlalchemy.and_(model.PackageListing.c.collectionid==collectionId,
                    model.PackageListing.c.packageid==model.Package.c.id)
                )
        return dict(title='%s -- %s %s' % (self.appTitle, collection['name'],
            collection['version']), collection=collection, packages=packages)
