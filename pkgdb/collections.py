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
from sqlalchemy.orm import lazyload, eagerload
from turbogears import controllers, expose, paginate, config, identity, flash
from cherrypy import request

import koji
from fedora.tg.util import json_or_redirect

from pkgdb import _
from pkgdb.model.collections import CollectionPackage, Collection, Branch
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
        collections = Collection.query.options(lazyload('listings'),
                lazyload('status')).add_entity(CollectionPackage
                        ).filter(Collection.id==CollectionPackage.id).order_by(
                                (Collection.name, Collection.version))
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
            collection_entry = Collection.query.options(lazyload('listings2'),
                    eagerload('status.locale')
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

    #
    # Read-write methods
    #

    @expose(allow_json=True)
    @json_or_redirect('/collections')
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.in_group('cvsadmin'))
    def mass_branch_test(self, branch):
        flash('testing mass branch %s' % branch)
        return dict(exc='CannotClone', branch_count=0,
                unbranched=['kernel', 'firefox'])

    @expose(allow_json=True)
    @json_or_redirect('/collections')
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.in_group('cvsadmin'))
    def mass_branch(self, branch):
        '''Mass branch all packages listed as non-blocked in koji to the pkgdb.

        Note: At some point, this will need to do the reverse: we'll maintain
        the list of dead packages in the pkgdb and sync that information to
        koji.

        Note: It is safe to call this method repeatedly.  If all packages have
        been branched already, new invokations will have no effect.

        :arg branch: Name of the branch to branch all packages for
        :returns: number of packages branched
        :raises InvalidBranch: If the branch does not exist in the pkgdb or
            koji
        :raises ServiceError: If we cannot log into koji
        :raises CannotClone: If some branches could not be cloned.  This will
            also return the names of the uncloned packages in the `unbranched`
            variable.
        '''
        koji_url = config.get('koji.huburl', 'https://koji.fedoraproject.org/kojihub')
        pkgdb_cert = config.get('cert.user', '/etc/pki/pkgdb/pkgdb.pem')
        user_ca = config.get('cert.user_ca', '/etc/pki/pkgdb/fedora-server-ca.cert')
        server_ca = config.get('cert.server_ca', '/etc/pki/pkgdb/fedora-upload-ca.cert')

        try:
            to_branch = Branch.query.filter_by(branchname=branch).one()
        except InvalidRequestError, e:
            session.rollback()
            flash(_('Unable to locate a branch for %(branch)s') % {'branch':
                branch})
            return dict(exc='InvalidBranch')

        koji_name = to_branch.koji_name
        if not koji_name:
            session.rollback()
            flash(_('Unable to mass branch for %(branch)s because it is not managed by koji') % {'branch': branch})
            return dict(exc='InvalidBranch')

        koji_session = koji.ClientSession(koji_url)
        if not koji_session.ssl_login(cert=pkgdb_cert, ca=user_ca, serverca=server_ca):
            session.rollback()
            flash(_('Unable to log into koji'))
            return dict(exc='ServiceError')

        devel_branch = Collection.by_simple_name('devel')

        pkglist = session.listPackages(tagID=koji_name, inherited=True)
        pkgs = (pkg for pkg in pkglist if not pkg['blocked'])

        unbranched = []
        num_branched = 0
        for pkg in pkgs:
            if pkg.package_name not in to_branch.listings2:
                if pkg.package_name in devel_branch.listings2:
                    # clone the package from the devel branch
                    try:
                        devel_branch.listings2[pkg.package_name].clone(branch)
                    except InvalidRequestError, e:
                        pass
                        # Error will be taked care of further down
                    else:
                        # Success, get us to the next package
                        num_branched = num_branched + 1
                        continue
                # If we get down to here we had an error cloning this package
                unbranched.append(pkg.package_name)

        try:
            session.flush()
        except SQLError, e:
            session.rollback()
            flash(_('Unable to save branched packages for %(branch)s') %
                    {'branch': branch})
            return dict(exc='DatabaseError')

        if unbranched:
            # Uh oh, there were packages which weren't branched.  Tell the
            # user
            flash(_('%(count)s/5(num)s packages were unbranched for %(branch)s'
                ) % {'count': len(unbranched), 'num': len(pkgs),
                    'branch': branch})
            return dict(exc='CannotClone', branch_count=num_branched,
                    unbranched=unbranched)

        flash(_('Succesfully branched all %(num)s packages') %
                {'num': num_branched})
        return dict(branch_count=num_branched)

