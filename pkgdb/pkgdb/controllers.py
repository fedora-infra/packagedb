# -*- coding: utf-8 -*-
import sqlalchemy
from sqlalchemy.ext.selectresults import SelectResults
import sqlalchemy.mods.selectresults
from turbogears import controllers, expose, paginate, config
from turbogears import identity, redirect
from turbogears.database import session
from cherrypy import request, response
import logging

from pkgdb import model
from pkgdb import json

from pkgdb.acls import Acls
from pkgdb.collections import Collections
from pkgdb.packages import Packages
from pkgdb.users import Users

log = logging.getLogger("pkgdb.controllers")

# The Fedora Account System Module
from fedora.accounts.fas import AccountSystem, AuthError

class Root(controllers.RootController):
    appTitle = 'Fedora Package Database'
    fas = AccountSystem()

    acls = Acls(fas, appTitle)
    collections = Collections(fas, appTitle)
    packages = Packages(fas, appTitle)
    users = Users(fas, appTitle)

    @expose(template='pkgdb.templates.overview')
    def index(self):
        return dict(title=self.appTitle)

    @expose(template="pkgdb.templates.login", allow_json=True)
    def login(self, forward_url=None, previous_url=None, *args, **kw):
        if not identity.current.anonymous \
            and identity.was_login_attempted() \
            and not identity.get_identity_errors():
                # User is logged in
                if 'tg_format' in request.params and request.params['tg_format'] == 'json':
                    # When called as a json method, doesn't make any sense to
                    # redirect to a page.  Returning the logged in identity
                    # is better.
                    return dict(user = identity.current.user)
                if not forward_url:
                    forward_url=config.get('base_url_filter.base_url') + '/'
                raise redirect(forward_url)
        
        forward_url=None
        previous_url=request.path

        if identity.was_login_attempted():
            msg=_("The credentials you supplied were not correct or "
                   "did not grant access to this resource.")
        elif identity.get_identity_errors():
            msg=_("You must provide your credentials before accessing "
                   "this resource.")
        else:
            msg=_("Please log in.")
            forward_url= request.headers.get("Referer", "/")

        ### FIXME: Is it okay to get rid of this?
        #response.status=403
        return dict(message=msg, previous_url=previous_url, logging_in=True,
                    original_parameters=request.params,
                    forward_url=forward_url, title='Fedora Account System Login')

    @expose()
    def logout(self):
        identity.current.logout()
        raise redirect(request.headers.get("Referer","/"))

