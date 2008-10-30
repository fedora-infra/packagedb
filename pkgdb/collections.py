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

#
# PyLint Disabling
#

# :E1101: SQLAlchemy mapped classes are monkey patched.  Unless otherwise
#   noted, E1101 is disabled due to a static checker not having information
#   about the monkey patches.

from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy.orm import lazyload
from turbogears import controllers, expose, paginate
from cherrypy import request

from pkgdb.model.collections import CollectionPackage, Collection
from pkgdb.model.packages import Package, PackageListing

class Collections(controllers.Controller):
    '''Controller that deals with Collections.

    These are methods that expose Collections to the users.  Collections are
    usually a specific release of a distribution.  For instance, Fedora 8.
    '''
    def __init__(self, fas, app_title):
        '''Create a Packages Controller.

        :arg fas: Fedora Account System object.
        :arg app_title: Title of the web app.
        '''
        self.fas = fas
        self.app_title = app_title

    @expose(template='pkgdb.templates.collectionoverview', allow_json=True)
    def index(self):
        '''List the Collections we know about.
        '''
        # pylint: disable-msg=E1101
        collections = CollectionPackage.query.order_by(
                (CollectionPackage.name, CollectionPackage.version))
        # pylint: enable-msg=E1101

        return dict(title=self.app_title + ' -- Collection Overview',
                collections=collections)

    @expose(template='pkgdb.templates.collectionpage', allow_json=True)
    @paginate('packages', default_order='name', limit=100,
            allow_limit_override=True, max_pages=13)
    # :C0103: id is an appropriate name for this function
    def id(self, collection_id): # pylint: disable-msg=C0103
        '''Return a page with information on a particular Collection

        :arg collection_id: Numeric id of the collection
        '''
        collectionEntry = collection_id
        try:
            collection_id = int(collection_id)
        except ValueError:
            error = dict(status = False,
                    title = self.app_title + ' -- Invalid Collection Id',
                    message = 'The collection_id you were linked to is not a' \
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
            collection_entry = Collection.query.options(lazyload('listings2')
                    ).filter_by(id=collection_id).one()
        except InvalidRequestError:
            # Either the id doesn't exist or somehow it references more than
            # one value
            error = dict(status = False,
                    title = self.app_title + ' -- Invalid Collection Id',
                    message = 'The collection_id you were linked to, %s, does' \
                            ' not exist.  If you received this error from a' \
                            ' link on the fedoraproject.org website, please' \
                            ' report it.' % collection_id)
            if request.params.get('tg_format', 'html') != 'json':
                error['tg_template'] = 'pkgdb.templates.errors'
            return error

        # Get ownership information from the fas
        try:
            user = self.fas.cache[collection_entry.owner]
        except KeyError:
            user = {}
            user['username'] = 'User ID %i' % collection_entry.owner
            user['email'] = 'unknown@fedoraproject.org'

        # Why do we reformat the data returned from the database?
        # 1) We don't need all the information in the collection object
        # 2) We need ownerName and statusname which are not in the specific
        #    table.
        collection = {'name': collection_entry.name,
                'version': collection_entry.version,
                'owner': collection_entry.owner,
                'ownername': user['username'],
                'summary': collection_entry.summary,
                'description': collection_entry.description,
                'statusname': collection_entry.status.locale['C'].statusname
                }

        # Retrieve the packagelist for this collection
        # pylint:disable-msg=E1101
        packages = Package.query.options(lazyload('listings2.people2'),
                lazyload('listings2.groups2')).join('listings2'
                        ).filter_by(collectionid = collection_id)
        # pylint:enable-msg=E1101

        return dict(title='%s -- %s %s' % (self.app_title, collection['name'],
            collection['version']), collection=collection, packages=packages)
