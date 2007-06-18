import sqlalchemy
from sqlalchemy.ext.selectresults import SelectResults
import sqlalchemy.mods.selectresults
from turbogears import controllers, expose, paginate, config
from turbogears import identity, redirect
from turbogears.database import session
import turbomail
from cherrypy import request, response
import logging

from pkgdb import model
from pkgdb import json

from pkgdb.packages import Packages

log = logging.getLogger("pkgdb.controllers")

# The Fedora Account System Module
from fedora.accounts.fas import AccountSystem, AuthError

ORPHAN_ID=9900
FROMADDR=config.get('from_address')
TOADDR=config.get('commits_address')

appTitle = 'Fedora Package Database'
fas = AccountSystem()

class Test(controllers.Controller):
    @expose(template="pkgdb.templates.welcome")
    @identity.require(identity.in_group("cvsextras"))
    def index(self):
        import time
        # log.debug("Happy TurboGears Controller Responding For Duty")
        return dict(now=time.ctime())

    @expose(template="pkgdb.templates.try")
    def test(self):
        return dict(title='Test Page', rows=({'1': 'alligator', '2':'bat'},{'1':'avocado', '2':'bannana'}))

    @expose(template='pkgdb.templates.orphans')
    def orphans(self):
        import os
        t = file('/var/tmp/t', 'w')
        #for line in os.environ:
        #    t.writelines('%s: %s\n' % (line, os.environ[line]))
        #t.writelines('%s' % request.wsgi_environ)
        t.writelines('%s' % request.headers)
        t.close()
        pkgs = {}
        orphanedPackages = SelectResults(session.query(model.PackageListing)).select(
                model.PackageListing.c.owner==ORPHAN_ID)
        for pkg in orphanedPackages:
            pkgs[pkg.package.name] = pkg.package.summary

        return dict(title='List Orphans', pkgs=pkgs)

    @expose(template='pkgdb.templates.pkgmine')
    @paginate('pkgs', default_order='name')
    @identity.require(identity.in_group("cvsextras"))
    def mine(self):
        #pkgs = {}
        #myPackages = SelectResults(session.query(model.PackageListing)).select(
        #        model.PackageListing.c.owner==identity.current.user.user_id)
        myPackages = SelectResults(session.query(model.Package)
                ).distinct().select(model.PackageListing.c.packageid == 
                    model.Package.c.id).select(model.PackageListing.c.owner==
                        identity.current.user.user_id)

        #for pkg in myPackages:
        #    pkgs = pkg.package

        return dict(title='My Packages', pkgs=myPackages)

class Collections(controllers.Controller):
    @expose(template='pkgdb.templates.collectionoverview')
    def index(self):
        '''List the Collections we know about.
        '''
        collectionPkg = sqlalchemy.select(
                (model.PackageListingTable.c.collectionid.label('id'),
                    sqlalchemy.func.count(1).label('numpkgs')),
                group_by=(model.PackageListingTable.c.collectionid,)).alias(
                        'collectionpkg')
        collections = sqlalchemy.select(
                (model.CollectionTable, collectionPkg.c.numpkgs),
                model.CollectionTable.c.id == collectionPkg.c.id,
                order_by=(model.CollectionTable.c.name,
                    model.CollectionTable.c.version)).execute()

        return dict(title=appTitle + ' -- Collection Overview',
                collections=collections)

    @expose(template='pkgdb.templates.collectionpage')
    @paginate('packages', default_order='name', limit=100,
            allow_limit_override=True, max_pages=13)
    def id(self, collectionId):
        '''Return a page with information on a particular Collection
        '''
        try:
            collectionId = int(collectionId)
        except ValueError:
            raise redirect(config.get('base_url_filter.base_url') + '/collections/not_id')
        ### FIXME: Want to return additional info:
        # date it was created (join log table: creation date)
        # The initial import doesn't have this information, though.
        collection = sqlalchemy.select((model.CollectionTable.c.name,
            model.CollectionTable.c.version, model.CollectionTable.c.owner,
            model.CollectionTable.c.summary, model.CollectionTable.c.description,
            model.StatusTranslationTable.c.statusname),
            sqlalchemy.and_(
                model.CollectionTable.c.statuscode==model.StatusTranslationTable.c.statuscodeid,
                model.StatusTranslationTable.c.language=='C',
                model.CollectionTable.c.id==collectionId), limit=1).execute()
        if collection.rowcount <= 0:
            raise redirect(config.get('base_url_filter.base_url') + '/collections/unknown',
                    redirect_params={'collectionId':collectionId})
        collection = collection.fetchone()

        # Get real ownership information from the fas
        (user, groups) = fas.get_user_info(collection.owner)
        collection.ownername = '%s (%s)' % (user['human_name'],
                user['username'])

        # Retrieve the packagelist for this collection
        packages = SelectResults(session.query(model.Package)).select(
                sqlalchemy.and_(model.PackageListing.c.collectionid==collectionId,
                    model.PackageListing.c.packageid==model.Package.c.id)
                )
        return dict(title='%s -- %s %s' % (appTitle, collection.name,
            collection.version), collection=collection, packages=packages)

    @expose(template='pkgdb.templates.errors')
    def unknown(self, collectionId):
        msg = 'The collectionId you were linked to, %s, does not exist.' \
                ' If you received this error from a link on the' \
                ' fedoraproject.org website, please report it.' % collectionId
        return dict(title=appTitle + ' -- Unknown Collection', msg=msg)

    @expose(template='pkgdb.templates.errors')
    def not_id(self):
        msg = 'The collectionId you were linked to is not a valid id.' \
                ' If you received this error from a link on the' \
                ' fedoraproject.org website, please report it.'
        return dict(title=appTitle + ' -- Invalid Collection Id', msg=msg)

class Root(controllers.RootController):
    appTitle = 'Fedora Package Database'
    fas = AccountSystem()

    test = Test()
    collections = Collections()
    packages = Packages(fas, appTitle)

    @expose(template='pkgdb.templates.overview')
    def index(self):
        return dict(title=appTitle)

    @expose(template="pkgdb.templates.login")
    def login(self, forward_url=None, previous_url=None, *args, **kw):
        if not identity.current.anonymous \
            and identity.was_login_attempted() \
            and not identity.get_identity_errors():
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

