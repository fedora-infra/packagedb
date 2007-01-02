from turbogears import controllers, expose
from pkgdb import model
from turbogears import identity, redirect
from cherrypy import request, response
from pkgdb import json
# import logging
# log = logging.getLogger("pkgdb.controllers")

class Test(controllers.RootController):
    @expose(template="pkgdb.templates.welcome")
    # @identity.require(identity.in_group("admin"))
    def index(self):
        import time
        # log.debug("Happy TurboGears Controller Responding For Duty")
        return dict(now=time.ctime())

    @expose(template="pkgdb.templates.login")
    def login(self, forward_url=None, previous_url=None, *args, **kw):

        if not identity.current.anonymous \
            and identity.was_login_attempted() \
            and not identity.get_identity_errors():
            raise redirect(forward_url)

        forward_url=None
        previous_url= request.path

        if identity.was_login_attempted():
            msg=_("The credentials you supplied were not correct or "
                   "did not grant access to this resource.")
        elif identity.get_identity_errors():
            msg=_("You must provide your credentials before accessing "
                   "this resource.")
        else:
            msg=_("Please log in.")
            forward_url= request.headers.get("Referer", "/")
            
        response.status=403
        return dict(message=msg, previous_url=previous_url, logging_in=True,
                    original_parameters=request.params,
                    forward_url=forward_url)

    @expose()
    def logout(self):
        identity.current.logout()
        raise redirect("/")

class Collections(controllers.Controller):
    @expose(template='pkgdb.templates.collectionoverview')
    def index(self):
        return dict(title='Fedora Package Database -- Collection Overview',
                collections=model.Collection.select())

    @expose(template='pkgdb.templates.collectionpage')
    def id(self, collectionId):
        try:
            collectionId = int(collectionId)
        except ValueError:
            raise redirect('/collections/not_id')
        collection = model.Collection.get_by(id=collectionId)
        if not collection:
            raise redirect('/collections/unknown',
                    redirect_params={'collectionId':collectionId})
        return dict(title='Test page', collection=model.Collection.get_by(id=collectionId))

    @expose(template='pkgdb.templates.errors')
    def unknown(self, collectionId):
        msg = 'The collectionId you were linked to, %s, does not exist.' \
                ' If you received this error from a link on the' \
                ' fedoraproject.org website, please report it.' % collectionId
        return dict(title='Unknown Collection', msg=msg)

    @expose(template='pkgdb.templates.errors')
    def not_id(self):
        msg = 'The collectionId you were linked to is not a valid id.' \
                ' If you received this error from a link on the' \
                ' fedoraproject.org website, please report it.'
        return dict(title='Invalid Collection Id', msg=msg)

class Packages(controllers.RootController):
    @expose(template='pkgdb.templates.pkgoverview')
    def index(self):
        return dict(title='Fedora Package Database -- Package Overview')

    @expose(template='pkgdb.templates.pkgpage')
    def id(self, packageId):
        return dict(title='Fedora Package Database')

class Root(controllers.RootController):
    test = Test()
    collections = Collections()
    packages = Packages()

    @expose(template='pkgdb.templates.overview')
    def index(self):
        return dict(title='Fedora Package Database')
