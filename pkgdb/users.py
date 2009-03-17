# -*- coding: utf-8 -*-
#
# Copyright © 2007  Nigel Jones
# Copyright © 2007  Red Hat, Inc.
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
# Author(s): Nigel Jones <nigelj@fedoraproject.org>
#            Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Controller to show information about packages by user.
'''

#
# PyLint Explanation
#

# :E1101: SQLAlchemy monkey patches the db fields into the class mappers so we
#   have to disable this check wherever we use the mapper classes.

import sqlalchemy
from sqlalchemy.orm import lazyload

from turbogears import controllers, expose, paginate, config, \
        redirect, identity

from pkgdb.model import Collection, Package, PackageListing, \
        StatusTranslation, PersonPackageListing, PersonPackageListingAcl

from fedora.tg.util import request_format

ORPHAN_ID = 9900

class Users(controllers.Controller):
    '''Controller for all things user related.

    Status Ids to use with queries.
    '''
    # pylint: disable-msg=E1101
    approvedStatusId = StatusTranslation.query.filter_by(
            statusname='Approved', language='C').one().statuscodeid
    awaitingBranchStatusId = StatusTranslation.query.filter_by(
            statusname='Awaiting Branch', language='C').one().statuscodeid
    awaitingReviewStatusId = StatusTranslation.query.filter_by(
            statusname='Awaiting Review', language='C').one().statuscodeid
    underReviewStatusId = StatusTranslation.query.filter_by(
            statusname='Under Review', language='C').one().statuscodeid
    EOLStatusId = StatusTranslation.query.filter_by(
            statusname='EOL', language='C').one().statuscodeid
    # pylint: enable-msg=E1101

    allAcls = (('owner', 'owner'), ('approveacls', 'approveacls'),
            ('commit', 'commit'),
            ('watchcommits', 'watchcommits'),
            ('watchbugzilla', 'watchbugzilla'))

    def __init__(self, app_title):
        '''Create a User Controller.

        :app_title: Title of the web app.
        '''
        self.app_title = app_title

    @expose(template='pkgdb.templates.useroverview')
    def index(self):
        '''Dish some dirt on the requesting user
        '''
        raise redirect(config.get('base_url_filter.base_url') + '/users/info/')

    @expose(template='pkgdb.templates.userpkgs', allow_json=True)
    @paginate('pkgs', limit=100, default_order='name',
            allow_limit_override=True, max_pages=13)
    def packages(self, fasname=None, acls=None, eol=None):
        '''List packages that the user is interested in.

        This method returns a list of packages owned by the user in current,
        non-EOL distributions.  The user has the ability to filter this to
        provide more or less information by adding query params for acls and
        EOL.

        Arguments:
        :fasname: The name of the user to get the package list for.
                  Default: The logged in user.
        :acls: List of acls to select.
               Note: for backwards compatibility, this can also be a comma
               separated string of acls.
               Default: all acls.
        :eol: If set, list packages that are in EOL distros.
        Returns: A list of packages.
        '''
        # Set EOL to false for a few obvious values
        if not eol or eol.lower() in ('false', 'f', '0'):
            eol = False
        else:
            eol = bool(eol)

        if not acls:
            # Default to all acls
            acls = [k[0] for k in self.allAcls]
        elif isinstance(acls, basestring):
            # For backwards compatibility, make acls into a list if it's a
            # comma separated string of values
            acls = acls.split(',')

        # Create a list where store acl name, whether the acl is currently
        # being filtered for, and the label to use to display the acl.
        acl_list = [(a[0], a[0] in acls, a[1]) for a in self.allAcls]

        # Have to either get fasname from the URL or current user
        if fasname == None:
            if identity.current.anonymous:
                raise identity.IdentityFailure(
                        'You must be logged in to view your information')
            else:
                fasname = identity.current.user_name

        page_title = self.app_title + ' -- ' + fasname + ' -- Packages'

        # pylint: disable-msg=E1101
        query = Package.query.join('listings2').distinct().options(
                lazyload('listings2.groups2'), 
                lazyload('listings2.groups2.acls2'),
                lazyload('listings2.people2'), 
                lazyload('listings2.people2.acls2'), lazyload('listings2'))

        if not eol:
            # We don't want EOL releases, filter those out of each clause
            query = query.join(['listings2', 'collection']).filter(
                        Collection.c.statuscode != self.EOLStatusId)

        queries = []
        if 'owner' in acls:
            # Return any package for which the user is the owner
            queries.append(query.filter(sqlalchemy.and_(
                        Package.c.statuscode.in_((
                            self.approvedStatusId,
                            self.awaitingReviewStatusId,
                            self.underReviewStatusId)),
                        PackageListing.c.owner==fasname,
                        PackageListing.c.statuscode.in_((
                            self.approvedStatusId,
                            self.awaitingBranchStatusId,
                            self.awaitingReviewStatusId))
                        )))
            del acls[acls.index('owner')]

        if acls:
            # Return any package on which the user has an Approved acl.
            queries.append(query.join(['listings2', 'people2']).join(
                    ['listings2', 'people2', 'acls2']).filter(sqlalchemy.and_(
                    Package.c.statuscode.in_((self.approvedStatusId,
                    self.awaitingReviewStatusId, self.underReviewStatusId)),
                    PersonPackageListing.c.username == fasname,
                    PersonPackageListingAcl.c.statuscode == \
                            self.approvedStatusId,
                    PackageListing.c.statuscode.in_(
                        (self.approvedStatusId,
                            self.awaitingBranchStatusId,
                            self.awaitingReviewStatusId))
                    )))
            # Return only those acls which the user wants listed
            queries[-1] = queries[-1].filter(
                    PersonPackageListingAcl.c.acl.in_(acls))

        if len(queries) == 2:
            my_pkgs = Package.query.select_from(
                            sqlalchemy.union(
                                    queries[0].statement,
                                    queries[1].statement
                                    ))
        else:
            my_pkgs = queries[0]

        my_pkgs = my_pkgs.options(lazyload('listings2.people2'), lazyload('listings2.people2.acls2'), lazyload('listings2.groups2'), lazyload('listings2.groups2.acls2'), lazyload('listings2')).order_by(Package.name)
        # pylint: enable-msg=E1101
        pkg_list = []
        for pkg in my_pkgs:
            pkg.json_props = {'Package': ('listings',)}
            pkg_list.append(pkg)

        return dict(title=page_title, pkgCount=len(pkg_list),
                pkgs=pkg_list, acls=acl_list, fasname=fasname)

    @expose(template='pkgdb.templates.useroverview')
    def info(self, fasname=None):
        '''Return some info and links for the user.

        Currently this page does nothing.  Eventually we want it to return an
        overview of what the user can do.  A TODO queue of people/packages
        they need to approve.  Links to FAS. Etc.

        Keyword Arguments:
        :fasname: If given, the name of hte user to display information for.
            Defaults to the logged in user.
        '''
        # If fasname is blank, ask for auth, we assume they want their own?
        if fasname == None:
            if identity.current.anonymous:
                raise identity.IdentityFailure(
                        "You must be logged in to view your information")
            else:
                fasname = identity.current.user_name

        page_title = self.app_title + ' -- ' + fasname + ' -- Info'
        return dict(title=page_title, fasname=fasname)
