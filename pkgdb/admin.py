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
Controller for handling admin commands.  These are the dispatcher type methods.
'''

#
# Pylint Explanations
#

# :E1101: SQLAlchemy monkey patches the database fields into the mapper
#   classes so we have to disable these checks.


from turbogears import controllers, expose, config, redirect, identity 
import koji

from pkgdb import model
from pkgdb.dispatcher import PackageDispatcher
from pkgdb.bugs import Bugs
from pkgdb.letter_paginator import Letters

from cherrypy import request

class Request():
    def __init__(self):
        pass
    def request_branch(self):
        pass
    def request_package(self):
        pass

class Admin(controllers.Controller):
    def __init__(self, fas):
        self.fas = fas

    def index(self):
        '''List the possible actions to perform.'''
        pass

    @expose(allow_json=True)
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
        pkgdb_cert = config.get('cert.user', '/etc/pki/pkgdb.cert')
        user_ca = config.get('cert.user_ca', '/etc/pki/fedora-server-ca.cert')
        server_ca = config.get('cert.server_ca', '/etc/pki/fedora-server-ca.cert')

        try:
            to_branch = Branch.query.filter_by(branchname=branch).one()
        except InvalidRequestError, e:
            flash(_('Unable to locate a branch for %(branch)s') % {'branch':
                branch})
            return dict(exc='InvalidBranch')

        koji_name = to_branch.koji_name
        if not koji_name:
            flash(_('Unable to mass branch for %(branch)s because it is not managed by koji') % {'branch': branch})
            return dict(exc='InvalidBranch')

        koji_session = koji.ClientSession(koji_url)
        if not koji_session.ssl_login(cert=pkgdb_cert, ca=user_ca, serverca=server_ca):
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

        if unbranched:
            # Uh oh, there were packages which weren't branched.  Tell the
            # user
            flash(_('%(count)s packages were unbranched for %(branch)s') %
                    {'count': len(unbranched), 'branch': branch})
            return dict(exc='CannotClone', branch_count=num_branched,
                    unbranched=unbranched)
        return dict(branch_count=num_branched)

    def create_collection(self):
        '''Let the user fill in the information for a new collection.'''
        pass

    def remove_package(self):
        '''Mark a package as removed.'''
        pass

    def rename_package(self):
        '''Rename a package to another name:: Note, still need to do things on
        the cvs server and in bugzilla after this.'''
        pass

    def view_queue(self):
        '''View pending admin requests
        '''
        pass
