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
    @identity.require(identity.in_group("cvsextras"))
    def index(self):
        '''Dish some dirt on the requesting user
        '''
        
        return dict(title=self.appTitle + ' -- User Overview')

    @expose(template='pkgdb.templates.userpkgs')
    @paginate('pkgs', default_order='name')
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
        else:
            try:
                fasid = self.fas.get_user_id(fasname)
            except AuthError:
               raise redirect(config.get('base_url_filter.base_url') + '/users/no_user/' + fasname)

        pageTitle = self.appTitle + ' -- ' + fasname + ' -- Packages'
        
        myPackages = SelectResults(session.query(model.Package)
            ).distinct().select(model.PackageListing.c.packageid ==
            model.Package.c.id).select(model.PackageListing.c.owner == fasid)
   
        return dict(title=pageTitle, pkgs=myPackages, fasname=fasname)

    @expose(template='pkgdb.templates.userpkgs')
    @paginate('pkgs', default_order='name')
    def acllist(self,fasname=None):

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

        pageTitle = self.appTitle + ' -- ' + fasname + ' -- ACL Entries'

        myAclEntries = SelectResults(session.query(model.Package)).select(
            model.PackageListing.c.packageid == model.Package.c.id).select(
            model.PersonPackageListing.c.packagelistingid ==
            model.PackageListing.c.id).select(
            model.PersonPackageListing.c.userid == fasid)

        return dict(title=pageTitle, pkgs=myAclEntries, fasname=fasname)

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

    @expose(template='pkgdb.templates.orphans', allow_json=True)
    def orphans(self):
        orphanedPackages = SelectResults(session.query(model.PackageListing)).select(
        model.PackageListing.c.owner==ORPHAN_ID)
        pkgs = {}
        for pkg in orphanedPackages:
            pkgs[pkg.package.name] = pkg.package.summary
        return dict(title=self.appTitle + ' -- Orphan List', pkgs=pkgs)
