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
from sqlalchemy.ext.selectresults import SelectResults
import sqlalchemy.mods.selectresults

from turbogears import controllers, expose, paginate, config, redirect, identity
from turbogears.database import session

from pkgdb import model

from fedora.accounts.fas import AccountSystem, AuthError

ORPHAN_ID=9900

class Users(controllers.Controller):
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
    def packages(self,fasname=None):
        '''I thought I managed to get this one at last, but it seems not
           I'll tackle it soon though -- Nigel
        '''

        if fasname == None:
            if identity.current.anonymous:
                raise identity.IdentityFailure('You must be logged in to view your information')
            else:
                fasid = identity.current.user.user_id
                fasname = identity.current.user.user_name
        elif fasname == "orphan":
            fasid = ORPHAN_ID
        else:
            try:
                fasid = self.fas.get_user_id(fasname)
            except AuthError:
               raise redirect(config.get('base_url_filter.base_url') + '/users/no_user/' + fasname)

        pageTitle = self.appTitle + ' -- ' + fasname + ' -- Packages'

        myPackages = session.query(model.Package).order_by((model.Package.c.name,)).select(
          sqlalchemy.union(
            model.PackageTable.select(
              sqlalchemy.and_(
                model.Package.c.id==model.PackageListing.c.packageid,
                model.PackageListing.c.owner==fasid
              )
            ),
            model.PackageTable.select(
              sqlalchemy.and_(
                model.Package.c.id==model.PackageListing.c.packageid,
                model.PackageListing.c.id==model.PersonPackageListing.c.packagelistingid,
                model.PersonPackageListing.c.userid==fasid
              )
            ),
            order_by=('name',)
          )
        )

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
                fasid = identity.current.user.user_id
                fasname = identity.current.user.user_name
        else:
            try:
                fasid = self.fas.get_user_id(fasname)
            except AuthError:
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
