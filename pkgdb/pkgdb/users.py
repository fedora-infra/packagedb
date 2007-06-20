import sqlalchemy
from sqlalchemy.ext.selectresults import SelectResults
import sqlalchemy.mods.selectresults

from turbogears import controllers, expose, paginate, config, redirect, identity
from turbogears.database import session

from pkgdb import model

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

    @expose(template='pkgdb.templates.pkgmine')
    @paginate('pkgs', default_order='name')
    @identity.require(identity.in_group("cvsextras"))
    def packages(self,fasName=None):
        '''I thought I managed to get this one at last, but it seems not
           I'll tackle it soon though -- Nigel
        '''
        
        myPackages = SelectResults(session.query(model.Package)
          ).distinct().select(model.PackageListing.c.packageid ==
          model.Package.c.id).select(model.PackageListing.c.owner ==
          identity.current.user.user_id)
   
        return dict(title=self.appTitle + ' -- My Packages', pkgs=myPackages)

    @expose(template='pkgdb.templates.pkgmine')
    @paginate('pkgs', default_order='name')
    @identity.require(identity.in_group("cvsextras"))
    def acllist(self):

        myAclEntries = SelectResults(session.query(model.Package)).select(
          model.PackageListing.c.packageid == model.Package.c.id).select(
          model.PersonPackageListing.c.packagelistingid ==
          model.PackageListing.c.id).select(model.PersonPackageListing.c.userid
          == identity.current.user.user_id)

        return dict(title=self.appTitle + ' -- My ACL Entries', pkgs=myAclEntries)
