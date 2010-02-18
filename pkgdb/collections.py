# -*- coding: utf-8 -*-
#
# Copyright © 2007-2009  Red Hat, Inc.
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
# :C0103: the method id looks up a collection by id.  Thus the method name is
#   appropriate.
# :C0322: Disable space around operator checking in multiline decorators

import threading
import os
import sys

from sqlalchemy.exceptions import InvalidRequestError, SQLError
from sqlalchemy.orm import lazyload, eagerload
from sqlalchemy.sql import select, and_
from turbogears import controllers, expose, paginate, config, identity, flash
from turbogears.database import session
from cherrypy import request

import koji
from fedora.tg.util import json_or_redirect, request_format, tg_url

from pkgdb import _
from pkgdb.model.collections import CollectionPackage, Collection, Branch
from pkgdb.model.packages import Package, PackageListing, PackageTable
from pkgdb.notifier import EventLogger
from pkgdb.lib.utils import admin_grp, STATUS

MASS_BRANCH_SET = 500

class Collections(controllers.Controller):
    '''Controller that deals with Collections.

    These are methods that expose Collections to the users.  Collections are
    usually a specific release of a distribution.  For instance, Fedora 8.
    '''
    def __init__(self, app_title):
        '''Create a Packages Controller.

        :arg app_title: Title of the web app.
        '''
        self.app_title = app_title

    @expose(template='pkgdb.templates.collectionoverview', allow_json=True)
    def index(self, eol=True):
        '''List the Collections we know about.

        :kwarg eol: Default True.  If set to False, only return collections
            which are not eol
        :returns: list of collections
        '''
        #pylint:disable-msg=E1101
        collections = Collection.query.options(lazyload('listings'),
                lazyload('status')).add_column(CollectionPackage.numpkgs
                ).filter(Collection.id==CollectionPackage.id).order_by(
            Collection.name, Collection.version)
        #pylint:enable-msg=E1101
        if not eol:
            collections = collections.filter(Collection.statuscode!=
                    STATUS['EOL'].statuscodeid)

        status_map = dict(((c[0].statuscode, c[0].status.locale['C'].statusname) for
            c in collections))

        return dict(title=_('%(app)s -- Collection Overview') %
                {'app': self.app_title}, collections=collections,
                status_map=status_map)

    @expose(template='pkgdb.templates.collectionpage', allow_json=True)
    @paginate('packages', default_order='name', limit=100, max_limit=None,
            max_pages=13) #pylint:disable-msg=C0322
    def name(self, collctn):
        '''Return a page with information on a particular Collection

        :arg collctn: Collection shortname
        '''
        ### FIXME: Want to return additional info:
        # date it was created (join log table: creation date)
        # The initial import doesn't have this information, though.
        try:
            #pylint:disable-msg=E1101
            collection = Collection.by_simple_name(collctn)
        except InvalidRequestError:
            # Either the name doesn't exist or somehow it references more than
            # one value
            flash(_('The collection name you were linked to, %(collctn)s,'
                    ' does not exist.  If you received this error from'
                    ' a link on the fedoraproject.org website, please'
                    ' report it.') % {'collctn': collctn})
            if request_format() == 'json':
                error = dict(exc='InvalidCollection')
            else:
                error = dict(title=_('%(app)s -- Invalid Collection Name') % {
                            'app': self.app_title},
                        tg_template='pkgdb.templates.errors')
            return error

        # Why do we reformat the data returned from the database?
        # 1) We don't need all the information in the collection object
        # 2) We need statusname which is not in the specific table.
        collection_entry = {'name': collection.name,
                'version': collection.version,
                'owner': collection.owner,
                'summary': collection.summary,
                'description': collection.description,
                'statusname': collection.status.locale['C'].statusname
                }

        # Retrieve the package list for this collection
        # pylint:disable-msg=E1101
        packages = select((PackageTable,), and_(Package.id==PackageListing.packageid,
                PackageListing.collectionid==collection.id,
                Package.statuscode!=STATUS['Removed'].statuscodeid),
                order_by=(Package.name,)).execute()
        # pylint:enable-msg=E1101

        return dict(title='%s -- %s %s' % (self.app_title, collection.name,
            collection.version), collection=collection_entry,
            packages=packages)

    @expose(template='pkgdb.templates.collectionpage', allow_json=True)
    @paginate('packages', default_order='name', limit=100, max_limit=None,
            max_pages=13) #pylint:disable-msg=C0322
    def id(self, collection_id): #pylint:disable-msg=C0103
        '''Return a page with information on a particular Collection

        :arg collection_id: Numeric id of the collection
        '''
        flash(_('This page is deprecated.  Use %(url)s instead.') %
                {'url': config.get('base_url_filter.base_url',
                    'http://localhost') + tg_url('/collection/name')})
        try:
            collection_id = int(collection_id)
        except ValueError:
            error = dict(status = False,
                    title = _('%(app)s -- Invalid Collection Id') %
                        {'app': self.app_title},
                    message =_('The collection_id you were linked to is not a' \
                            ' valid id.  If you received this error from a' \
                            ' link on the fedoraproject.org website, please' \
                            ' report it.'))
            if request.params.get('tg_format', 'html') != 'json':
                error['tg_template'] = 'pkgdb.templates.errors'
            return error

        ### FIXME: Want to return additional info:
        # date it was created (join log table: creation date)
        # The initial import doesn't have this information, though.
        try:
            #pylint:disable-msg=E1101
            collection_entry = Collection.query.options(
                    lazyload('listings2'), eagerload('status.locale'))\
                    .filter_by(id=collection_id).one()
        except InvalidRequestError:
            # Either the id doesn't exist or somehow it references more than
            # one value
            error = dict(status = False,
                    title = _('%(app)s -- Invalid Collection Id') %
                            {'app': self.app_title},
                    message = _('The collection_id you were linked to, %(id)s,'
                            ' does not exist.  If you received this error from'
                            ' a link on the fedoraproject.org website, please'
                            ' report it.') % {'id': collection_id})
            if request.params.get('tg_format', 'html') != 'json':
                error['tg_template'] = 'pkgdb.templates.errors'
            return error

        # Why do we reformat the data returned from the database?
        # 1) We don't need all the information in the collection object
        # 2) We need statusname which is not in the specific table.
        collection = {'name': collection_entry.name,
                'version': collection_entry.version,
                'owner': collection_entry.owner,
                'summary': collection_entry.summary,
                'description': collection_entry.description,
                'statusname': collection_entry.status.locale['C'].statusname
                }

        # Retrieve the packagelist for this collection
        # pylint:disable-msg=E1101
        packages = Package.query.options(lazyload('listings2.people2'),
                lazyload('listings2.groups2')).join('listings2'
                        ).filter_by(collectionid = collection_id
                        ).filter(Package.statuscode !=
                                STATUS['Removed'].statuscodeid)
        # pylint:enable-msg=E1101

        return dict(title='%s -- %s %s' % (self.app_title, collection['name'],
            collection['version']), collection=collection, packages=packages)

    #
    # Read-write methods
    #

    def _mass_branch_worker(self, to_branch, devel_branch, pkgs, author_name):
        '''Main worker for mass branching.

        :arg to_branch: Branch to put new PackageListings on
        :arg devel_branch: Branch for devel, where we're branching from
        :arg pkgs: List of packages to branch
        :arg author_name: username of person making the branch
        :returns: List of packages which had failures while trying to branch

        This method forks and invokes the branching in a child.  That prevents
        ballooning of memory when all the packages are processed in the main
        server process (note: separate threads don't seem to help.)
        '''
        in_pipe, out_pipe = os.pipe()
        pid = os.fork()
        if pid:
            # Controller
            os.close(out_pipe)
            in_pipe = os.fdopen(in_pipe, 'r')
            raw_unbranched = in_pipe.read()
            retcode = os.waitpid(pid, 0)
        else:
            # Child
            os.close(in_pipe)
            out_pipe = os.fdopen(out_pipe, 'w')
            unbranched = []
            for pkg in pkgs:
                if pkg['package_name'] in devel_branch.listings2:
                    # clone the package from the devel branch
                    try:
                        devel_branch.listings2[pkg['package_name']
                                ].clone(to_branch.branchname, author_name)
                    except InvalidRequestError:
                        # Exceptions will be handled later.
                        pass
                    else:
                        # Success, get us to the next package
                        continue

                # If we get to here we had an error cloning this package
                unbranched.append(pkg['package_name'])

            # Commit the changes
            try:
                session.flush() #pylint:disable-msg=E1101
            except SQLError, e:
                # If we have an error committing we lose this whole block
                session.rollback() #pylint:disable-msg=E1101
                unbranched = pkgs

            # Child prints a \n separated list of unbranched packages
            out_pipe.write('\n'.join(unbranched))
            sys.exit(0)
            ### End of forked child ###

        # Back to the Controller
        if raw_unbranched:
            return raw_unbranched.strip().split('\n')
        else:
            return []

    def _mass_branch(self, to_branch, devel_branch, pkgs, author_name,
            author_email):
        '''Performs a mass branching.  Intended to run in the background.

        :arg to_branch: Branch to put new PackageListings on
        :arg devel_branch: Branch for devel, where we're branching from
        :arg pkgs: List of packages to branch
        :arg author_name: username of person making the branch
        :arg author_email: email of person making the branch

        This method branches all the packages given to it from devel_branch to
        to_branch.  It subdivides the package list and branches each set in a
        forked process.  This is done to keep memory usage reasonable.  After
        it finishes, it emails the user who started the process the results of
        the branching.
        '''
        unbranched = []
        pkg_idx = 0
        # Split this up and fork so we don't blow out all our memory
        for pkg_idx in range(MASS_BRANCH_SET, len(pkgs), MASS_BRANCH_SET):
            unbranched.extend(self._mass_branch_worker(to_branch, devel_branch,
                pkgs[pkg_idx - MASS_BRANCH_SET:pkg_idx], author_name))
        unbranched.extend(self._mass_branch_worker(to_branch, devel_branch,
            pkgs[pkg_idx:], author_name))


        if unbranched:
            # Uh oh, there were packages which weren't branched.  Tell the
            # user
            msg = _('%(count)s/%(num)s packages were unbranched for' \
                    ' %(branch)s\n') % {'count': len(unbranched),
                            'num': len(pkgs), 'branch': to_branch.branchname}
            msg = msg + '\n'.join(unbranched)
        else:
            num_branched = len(pkgs) - len(unbranched)
            msg = _('Succesfully branched all %(num)s packages') % \
                    {'num': num_branched}

        # Send an email to the user to tell them how things turned out
        eventlogger = EventLogger()
        eventlogger.send_msg(msg, _('Mass branching status for %(branch)s') %
                {'branch': to_branch.branchname},
                (author_email,))

    @expose(allow_json=True)
    @json_or_redirect('/collections')
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.in_group(admin_grp))
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
        # Retrieve configuration values
        koji_url = config.get('koji.huburl',
                'https://koji.fedoraproject.org/kojihub')
        pkgdb_cert = config.get('cert.user', '/etc/pki/pkgdb/pkgdb.pem')
        user_ca = config.get('cert.user_ca',
                '/etc/pki/pkgdb/fedora-server-ca.cert')
        server_ca = config.get('cert.server_ca',
                '/etc/pki/pkgdb/fedora-upload-ca.cert')

        # Retrieve the collection to make the new branches on
        try:
            #pylint:disable-msg=E1101
            to_branch = Branch.query.filter_by(branchname=branch).one()
        except InvalidRequestError, e:
            session.rollback() #pylint:disable-msg=E1101
            flash(_('Unable to locate a branch for %(branch)s') % {
                'branch': branch})
            return dict(exc='InvalidBranch')

        if to_branch.statuscode == STATUS['EOL'].statuscodeid:
            session.rollback() #pylint:disable-msg=E1101
            flash(_('Will not branch packages in EOL collection %(branch)s') % {
                'branch': branch})
            return dict(exc='InvalidBranch')

        # Retrieve a koji session to get the list of packages from
        koji_name = to_branch.koji_name
        if not koji_name:
            session.rollback() #pylint:disable-msg=E1101
            flash(_('Unable to mass branch for %(branch)s because it is not'
                ' managed by koji') % {'branch': branch})
            return dict(exc='InvalidBranch')

        koji_session = koji.ClientSession(koji_url)
        if not koji_session.ssl_login(cert=pkgdb_cert, ca=user_ca,
                serverca=server_ca):
            session.rollback() #pylint:disable-msg=E1101
            flash(_('Unable to log into koji'))
            return dict(exc='ServiceError')

        # Retrieve the devel branch for comparison
        #pylint:disable-msg=E1101
        devel_branch = Branch.query.filter_by(branchname='devel').one()
        #pylint:enable-msg=E1101

        # Retrieve the package from koji
        pkglist = koji_session.listPackages(tagID=koji_name, inherited=True)
        # Filter out packages that already branched
        pkgs = (pkg for pkg in pkglist if pkg['package_name'] not in
                to_branch.listings2)
        # Filter out packages blocked in koji
        pkgs = [pkg for pkg in pkgs if not pkg['blocked']]
        # Sort them so that printed statuses show where we are
        pkgs.sort(lambda x, y: cmp(x['package_name'], y['package_name']))

        # Perform the work of branching in a background thread.  This is
        # because branching takes so long the client's connection to the
        # server is likely to time out.
        brancher = threading.Thread(target=self._mass_branch,
                args=[to_branch, devel_branch, pkgs,
                    identity.current.user_name, identity.current.user.email])
        brancher.start()
        ### FIXME: Create a status page for this that we update the database
        # to see.
        flash(_('Mass branch started.  You will be emailed the results.'))
        return {}

    @expose(allow_json=True)
    def by_simple_name(self, collctn_name, collctn_ver):
        '''
        Retrieve a collection by its simple_name
        '''
        collection = Collection.query.filter_by( #pylint:disable-msg=E1101
                name=collctn_name, version=collctn_ver).one()
        return dict(name=collection.simple_name)

    @expose(allow_json=True)
    def by_canonical_name(self, collctn):
        '''
        Retrieve a collection by its canonical_name
        '''
        collection, version = Collection.by_simple_name(collctn)
        return dict(collctn_name=collection, collctn_ver=version)
