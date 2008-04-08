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

from pkgdb import model

ORPHAN_ID=9900

class Users(controllers.Controller):
    '''Controller for all things user related.
    
    Status Ids to use with queries.
    '''
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
    @paginate('pkgs', default_order='name', limit=100,
            allow_limit_override=True, max_pages=13)
    def packages(self, fasname=None, acls='any', EOL=False):
        '''List packages that the user is interested in.
           
        This method returns a list of packages owned by the user in current,
        non-EOL distributions.  The user has the ability to filter this to
        provide more or less information by adding query params for acls and
        EOL.

        Arguments:
        :fasname: The name of the user to get the package list for.
                  Default: The logged in user.
        :acls: Comma separated list of acls that we're looking for the user to
                have on the package to list it.  Default: any acls.
        :EOL: If set, list packages that are in EOL distros.
        Returns: A list of packages.
        '''
        # Set EOL to false for a few obvious values
        if not EOL or EOL.lower() in ('false', 'f', '0'):
            EOL = False
        else:
            EOL = bool(EOL)

        # Make acls into a list
        acls = acls.split(',')

        # Have to either get fasname from the URL or current user
        if fasname == None:
            if identity.current.anonymous:
                raise identity.IdentityFailure('You must be logged in to view your information')
            else:
                fasid = identity.current.user.id
                fasname = identity.current.user_name
        else:
            user = self.fas.person_by_username(fasname)
            if user:
                fasid = user['id']
            else:
                return dict(title=self.appTitle + ' -- Invalid Username',
                        tg_template='pkgdb.templates.errors', status=False,
                        pkgs=[],
                        message='The username you were linked to (%s) does' \
                        ' can not be found.  If you received this error from' \
                        ' a link on the fedoraproject.org website, please' \
                        ' report it.' % fasname
                    )
        pageTitle = self.appTitle + ' -- ' + fasname + ' -- Packages'

        # Create the clauses of the package finding query
        clauses = []

        if 'any' in acls or 'owner' in acls:
            # Return any package for which the user is the owner
            clauses.append(model.Package.query.filter(
                    sqlalchemy.and_(
                        model.Package.c.id==model.PackageListing.c.packageid,
                        model.Package.c.statuscode.in_(self.approvedStatusId,
                            self.awaitingReviewStatusId,
                            self.underReviewStatusId),
                        model.PackageListing.c.owner==fasid,
                        model.PackageListing.c.statuscode.in_(
                            self.approvedStatusId,
                            self.awaitingBranchStatusId,
                            self.awaitingReviewStatusId)
                        ),
                    ))
            if 'owner' in acls:
                del acls[acls.index('owner')]

        if acls:
            # Return any package on which the user has an Approved acl.
            clauses.append(model.Package.query.filter(
              sqlalchemy.and_(
                model.Package.c.id==model.PackageListing.c.packageid,
                model.Package.c.statuscode.in_(self.approvedStatusId,
                    self.awaitingReviewStatusId, self.underReviewStatusId),
                model.PackageListing.c.id==model.PersonPackageListing.c.packagelistingid,
                model.PersonPackageListing.c.userid==fasid,
                model.PersonPackageListing.c.id==model.PersonPackageListingAcl.c.personpackagelistingid,
                model.PersonPackageListingAcl.c.statuscode==self.approvedStatusId,
                model.PackageListing.c.statuscode.in_(self.approvedStatusId,
                    self.awaitingBranchStatusId, self.awaitingReviewStatusId)
              )
            ))
            if 'any' not in acls:
                # Return only those acls which the user wants listed
                clauses[-1] = clauses[-1].filter(model.PersonPackageListingAcl.c.acl.in_(*acls))

        if not EOL:
            # We don't want EOL releases, filter those out of each clause
            clauses = map(lambda clause: clause.filter(sqlalchemy.and_(
                        model.PackageListing.c.collectionid==model.Collection.c.id,
                        model.Collection.c.statuscode!=self.EOLStatusId)),
                    clauses)

        query = map(lambda clause: clause.compile(), clauses)
        if len(query) == 2:
            myPackages = model.Package.query.filter(sqlalchemy.union(query[0], query[1], order_by=('package_name',)))
        elif len(query) == 1:
            myPackages = model.Package.query.filter(sqlalchemy.union(query[0], order_by=('package_name',)))

        return dict(title=pageTitle, pkgs=myPackages, fasname=fasname)

    @expose(template='pkgdb.templates.userpkgs', allow_json=True)
    @paginate('pkgs', default_order='name', limit=100,
            allow_limit_override=True, max_pages=13)
    def acllist(self,fasname=None):

        if fasname == None:
            raise redirect(config.get('base_url_filter.base_url') + '/users/packages/')
        else:
            raise redirect(config.get('base_url_filter.base_url') + '/users/packages/' + fasname)

    @expose(template='pkgdb.templates.useroverview')
    def info(self,fasname=None):
        # If fasname is blank, ask for auth, we assume they want their own?
        if fasname == None:
            if identity.current.anonymous:
                raise identity.IdentityFailure("You must be logged in to view your information")
            else:
                fasid = identity.current.user.id
                fasname = identity.current.user_name
        else:
            user = self.fas.person_by_username(fasname)
            if user:
                fasid = user['id']
            else:
                raise redirect(config.get('base_url_filter.base_url') + '/users/no_user/' + fasname)

        pageTitle = self.appTitle + ' -- ' + fasname + ' -- Info'

        return dict(title=pageTitle, fasid=fasid, fasname=fasname)

    @expose(template='pkgdb.templates.errors')
    def no_user(self, fasname=None):
        msg = 'The username you were linked to (%s) does not appear' \
                ' can not be found.' \
                ' If you received this error from a link on the' \
                ' fedoraproject.org website, please report it.' % fasname
        return dict(title=self.appTitle + ' -- Invalid Username', message=msg)
