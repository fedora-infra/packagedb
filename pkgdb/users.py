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

import sqlalchemy

from turbogears import controllers, expose, paginate, config, \
        redirect, identity
from turbogears.database import session
from cherrypy import request

from pkgdb import model
from fedora.tg.util import request_format

ORPHAN_ID = 9900

class Users(controllers.Controller):
    '''Controller for all things user related.
    
    Status Ids to use with queries.
    '''
    # pylint: disable-msg=E1101
    approvedStatusId = model.StatusTranslation.query.filter_by(
            statusname='Approved', language='C').one().statuscodeid
    awaitingBranchStatusId = model.StatusTranslation.query.filter_by(
            statusname='Awaiting Branch', language='C').one().statuscodeid
    awaitingReviewStatusId = model.StatusTranslation.query.filter_by(
            statusname='Awaiting Review', language='C').one().statuscodeid
    underReviewStatusId = model.StatusTranslation.query.filter_by(
            statusname='Under Review', language='C').one().statuscodeid
    EOLStatusId = model.StatusTranslation.query.filter_by(
            statusname='EOL', language='C').one().statuscodeid
    # pylint: enable-msg=E1101

    allAcls = (('owner', 'owner'), ('approveacls', 'approveacls'),
            ('commit', 'commit'),
            ('watchcommits', 'watchcommits'),
            ('watchbugzilla', 'watchbugzilla'))

    def __init__(self, fas, appTitle):
        '''Create a User Controller.

        :fas: Fedora Account System object.
        :appTitle: Title of the web app.
        '''
        self.fas = fas
        self.appTitle = appTitle

    @expose(template='pkgdb.templates.useroverview')
    def index(self):
        '''Dish some dirt on the requesting user
        '''
        raise redirect(config.get('base_url_filter.base_url') + '/users/info/')

        return dict(title=self.appTitle + ' -- User Overview')

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
        aclList = [(a[0], a[0] in acls, a[1]) for a in self.allAcls]

        # Have to either get fasname from the URL or current user
        if fasname == None:
            if identity.current.anonymous:
                raise identity.IdentityFailure(
                        'You must be logged in to view your information')
            else:
                fasid = identity.current.user.id
                fasname = identity.current.user_name
        else:
            try:
                user = self.fas.cache[fasname]
            except KeyError:
                error = dict(title=self.appTitle + ' -- Invalid Username',
                        status = False, pkgs = [],
                        message='The username you were linked to (%s) cannot' \
                        ' be found.  If you received this error from' \
                        ' a link on the fedoraproject.org website, please' \
                        ' report it.' % fasname
                    )
                if request_format() != 'json':
                        error['tg_template'] = 'pkgdb.templates.errors'
                return error
            fasid = user['id']
        pageTitle = self.appTitle + ' -- ' + fasname + ' -- Packages'

        query = model.Package.query.join('listings').distinct()

        if not eol:
            # We don't want EOL releases, filter those out of each clause
            query = query.join(['listings', 'collection']).filter(
                        model.Collection.c.statuscode != self.EOLStatusId)

        queries = []
        if 'owner' in acls:
            # Return any package for which the user is the owner
            queries.append(query.filter(sqlalchemy.and_(
                        model.Package.c.statuscode.in_((
                            self.approvedStatusId,
                            self.awaitingReviewStatusId,
                            self.underReviewStatusId)),
                        model.PackageListing.c.owner==fasid,
                        model.PackageListing.c.statuscode.in_((
                            self.approvedStatusId,
                            self.awaitingBranchStatusId,
                            self.awaitingReviewStatusId))
                        )))
            del acls[acls.index('owner')]

        if acls:
            # Return any package on which the user has an Approved acl.
            queries.append(query.join(['listings', 'people']).join(
                    ['listings', 'people', 'acls']).filter(sqlalchemy.and_(
                    model.Package.c.statuscode.in_((self.approvedStatusId,
                    self.awaitingReviewStatusId, self.underReviewStatusId)),
                    model.PersonPackageListing.c.userid == fasid,
                    model.PersonPackageListingAcl.c.statuscode == \
                            self.approvedStatusId,
                    model.PackageListing.c.statuscode.in_(
                        (self.approvedStatusId,
                            self.awaitingBranchStatusId,
                            self.awaitingReviewStatusId))
                    )))
            # Return only those acls which the user wants listed
            queries[-1] = queries[-1].filter(
                    model.PersonPackageListingAcl.c.acl.in_(acls))

        if len(queries) == 2:
            myPackages = model.Package.query.select_from(
                            sqlalchemy.union(
                                    queries[0].statement,
                                    queries[1].statement
                                    ))
        else:
            myPackages = queries[0]

        return dict(title=pageTitle, pkgCount=myPackages.count(),
                pkgs=myPackages, acls=aclList, fasname=fasname)

    @expose(template='pkgdb.templates.useroverview')
    def info(self, fasname=None):
        # If fasname is blank, ask for auth, we assume they want their own?
        if fasname == None:
            if identity.current.anonymous:
                raise identity.IdentityFailure(
                        "You must be logged in to view your information")
            else:
                fasid = identity.current.user.id
                fasname = identity.current.user_name
        else:
            try:
                user = self.fas.cache[fasname]
            except KeyError:
                error = dict(status = False,
                        title = self.appTitle + ' -- Invalid Username',
                        message = 'The username you were linked to,' \
                                ' (%username)s does not exist.  If you' \
                                ' received this error from a link on the' \
                                ' fedoraproject.org website, please report' \
                                ' it.' % {'username': fasname})
                if request_format() != 'json':
                    error['tg_template'] = 'pkgdb.templates.errors'
                return error

            fasid = user['id']

        pageTitle = self.appTitle + ' -- ' + fasname + ' -- Info'

        return dict(title=pageTitle, fasid=fasid, fasname=fasname)
