import sqlalchemy
from sqlalchemy.ext.selectresults import SelectResults
import sqlalchemy.mods.selectresults
from turbogears import controllers, expose, paginate, config
from turbogears import identity, redirect
from turbogears.database import session
from pkgdb import model
from cherrypy import request, response
from pkgdb import json
import logging
log = logging.getLogger("pkgdb.controllers")

# The Fedora Account System Module
from fedora.accounts.fas import AccountSystem

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
            raise redirect('/collections/not_id')
        ### FIXME: Want to return additional info:
        # date it was created (join log table: creation date)
        # The initial import doesn't have this information, though.
        collection = sqlalchemy.select((model.CollectionTable.c.name,
            model.CollectionTable.c.version, model.CollectionTable.c.owner,
            model.CollectionTable.c.summary, model.CollectionTable.c.description,
            model.StatusTranslationTable.c.statusname),
            sqlalchemy.and_(
                model.CollectionTable.c.status==model.StatusTranslationTable.c.statuscodeid,
                model.StatusTranslationTable.c.language=='C',
                model.CollectionTable.c.id==collectionId), limit=1).execute()
        if collection.rowcount <= 0:
            raise redirect('/collections/unknown',
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

class AclOwners(object):
    '''Owners of package acls.'''
    def __init__(self, name):
        self.name = name
        self.acls = []

class Packages(controllers.Controller):
    @expose(template='pkgdb.templates.pkgoverview')
    @paginate('packages', default_order='name', limit=100,
            allow_limit_override=True, max_pages=13)
    def index(self):
        # Retrieve the complete list of packages
        packages = SelectResults(session.query(model.Package))
        return dict(title=appTitle + ' -- Package Overview', packages=packages)

    @expose(template='pkgdb.templates.pkgpage')
    def id(self, packageId):
        # Return the information about a package.
        pkgRow = sqlalchemy.select((model.PackageTable.c.name,
            model.PackageTable.c.summary, model.PackageTable.c.description,
            model.StatusTranslationTable.c.statusname),
            sqlalchemy.and_(
                model.PackageTable.c.status==model.StatusTranslationTable.c.statuscodeid,
                model.StatusTranslationTable.c.language=='C',
                model.PackageTable.c.id==packageId), limit=1).execute()
        if pkgRow.rowcount <= 0:
            raise redirect('/package/unknown',
                    redirect_params={'packageId' : packageId})
        package = pkgRow.fetchone()

        # Fetch information about all the packageListings for this package
        pkgListingRows = sqlalchemy.select((model.PackageListingTable.c.id,
            model.PackageListingTable.c.owner,
            model.PackageListingTable.c.qacontact,
            model.PackageListingTable.c.collectionid,
            model.CollectionTable.c.name, model.CollectionTable.c.version,
            model.StatusTranslationTable.c.statusname),
            sqlalchemy.and_(
                model.PackageListingTable.c.status==model.StatusTranslationTable.c.statuscodeid,
                model.StatusTranslationTable.c.language=='C',
                model.PackageListingTable.c.collectionid==model.CollectionTable.c.id,
                model.PackageListingTable.c.packageid==packageId),
                order_by=(model.CollectionTable.c.name,
                    model.CollectionTable.c.version)).execute()

        packageListings = pkgListingRows.fetchall()
        for pkg in packageListings:
            # Get real ownership information from the fas
            (user, group) = fas.get_user_info(pkg.owner)
            pkg.ownername = '%s (%s)' % (user['human_name'], user['username'])
            if pkg.qacontact:
                (user, groups) = fas.get_user_info(pkg.qacontact)
                pkg.qacontactname = '%s (%s)' % (user['human_name'],
                        user['username'])
            else:
                pkg.qacontactname = ''

            acls = model.PackageAcl.select((
                model.PackageAcl.c.packagelistingid==pkg.id))

            # Reformat the data so we have it stored per user
            people = {}
            for acl in acls:
                for user in acl.people:
                    if not people.has_key(user.userid):
                        (person, groups) = fas.get_user_info(user.userid)
                        people[user.userid] = AclOwners(person['human_name'])
                    people[user.userid].acls.append({'aclname' : user.acl.acl,
                            'status' : model.StatusTranslation.get_by(
                                model.StatusTranslation.c.statuscodeid==user.status,
                                    model.StatusTranslation.c.language=='C').statusname})

            # Store the acl owners in the package
            pkg.people = people
            
        return dict(title='%s -- %s' % (appTitle, package.name),
                package=package, packageid=packageId,
                packageListings=packageListings)

    @expose(template='pkgdb.templates.errors')
    def unknown(self, pakageIdId):
        msg = 'The packageId you were linked to, %s, does not exist.' \
                ' If you received this error from a link on the' \
                ' fedoraproject.org website, please report it.' % packageId
        return dict(title=appTitle + ' -- Unknown Package', msg=msg)

class Root(controllers.RootController):
    test = Test()
    collections = Collections()
    packages = Packages()

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
                    forward_url=forward_url)

    @expose()
    def logout(self):
        identity.current.logout()
        raise redirect("/")

