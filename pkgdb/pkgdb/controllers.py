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

ORPHAN_ID=9900

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
            raise redirect(config.get('base_url_filter.base_url') + '/collections/not_id')
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

class AclOwners(object):
    '''Owners of package acls.'''
    def __init__(self, name, acls):
        self.name = name
        self.acls = {}
        for aclName in acls:
            self.acls[aclName] = None

class PackageDispatcher(controllers.Controller):
    def __init__(self):
        controllers.Controller.__init__(self)
        # We want to expose a list of public methods to the outside world so
        # they know what RPC's they can make
        ### FIXME: It seems like there should be a better way.
        self.methods = [ m for m in dir(self) if
                hasattr(getattr(self, m), 'exposed') and 
                getattr(self, m).exposed]

    @expose('json')
    def index(self):
        return dict(methods=self.methods)

    @expose('json')
    # Check that the tg.identity is allowed to set themselves as owner
    @identity.require(identity.in_group("cvsextras"))
    def toggle_owner(self, containerId):
        
        # Check that the pkgid is orphaned
        pkg = model.PackageListing.get_by(id=containerId)
        if not pkg:
            return dict(status=False, message='No such package %s' % containerId)
        ### FIXME: We want to allow "admin" users to set orphan status as well.
        if pkg.owner == identity.current.user.user_id:
            # Release ownership
            pkg.owner = ORPHAN_ID
            ownerName = 'Orphaned Package (orphan)'
        elif pkg.owner == ORPHAN_ID:
            # Take ownership
            pkg.owner = identity.current.user.user_id
            ownerName = '%s (%s)' % (identity.current.user.display_name,
                    identity.current.user_name)
        else:
            return dict(status=False, message='Package %s not available for taking' % containerId)

        ### FIXME: This is happening in two places: Here and in packages::id().
        # We should eventually only pass it in packages::id() but translating
        # from python to javascript makes this hard.

        # Possible statuses for acls:
        aclStatus = SelectResults(session.query(model.PackageAclStatus))
        aclStatusTranslations=['']
        for status in aclStatus:
            ### FIXME: At some point, we have to pull other translations out,
            # not just C
            aclStatusTranslations.append(status.translations[0].statusname)

        return dict(status=True, ownerId=pkg.owner, ownerName=ownerName,
                aclStatusFields=aclStatusTranslations)

    @expose('json')
    # Check that the requestor is in a group that can approve ACLs
    @identity.require(identity.in_group("cvsextras"))
    def set_acl_status(self):
        pass

    @expose('json')
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.not_anonymous())
    def toggle_acl_request(self):
        pass

class Packages(controllers.Controller):
    dispatcher = PackageDispatcher()

    @expose(template='pkgdb.templates.pkgoverview')
    @paginate('packages', default_order='name', limit=100,
            allow_limit_override=True, max_pages=13)
    def index(self):
        # Retrieve the complete list of packages
        packages = SelectResults(session.query(model.Package))
        return dict(title=appTitle + ' -- Package Overview', packages=packages)

    @expose(template='pkgdb.templates.pkgpage')
    def id(self, packageId):
        try:
            packageId = int(packageId)
        except ValueError:
            raise redirect(config.get('base_url_filter.base_url') + '/packages/not_id')
        # Return the information about a package.
        pkgRow = sqlalchemy.select((model.PackageTable.c.name,
            model.PackageTable.c.summary, model.PackageTable.c.description,
            model.StatusTranslationTable.c.statusname),
            sqlalchemy.and_(
                model.PackageTable.c.status==model.StatusTranslationTable.c.statuscodeid,
                model.StatusTranslationTable.c.language=='C',
                model.PackageTable.c.id==packageId), limit=1).execute()
        if pkgRow.rowcount <= 0:
            raise redirect(config.get('base_url_filter.base_url') + '/packages/unknown',
                redirect_params={'packageId' : packageId})
        package = pkgRow.fetchone()

        # Possible ACLs
        aclNames = ('checkout', 'watchbugzilla', 'watchcommits', 'commit', 'build', 'approveacls')
        # Possible statuses for acls:
        aclStatus = SelectResults(session.query(model.PackageAclStatus))
        aclStatusTranslations=['']
        for status in aclStatus:
            ### FIXME: At some point, we have to pull other translations out,
            # not just C
            aclStatusTranslations.append(status.translations[0].statusname)

        # Fetch information about all the packageListings for this package
        pkgListings = SelectResults(session.query(model.PackageListing)).select(
                model.PackageListingTable.c.packageid==packageId
                )

        for pkg in pkgListings:
            # Get real ownership information from the fas
            (user, group) = fas.get_user_info(pkg.owner)
            ### FIXME: Handle the case where the owner is unknown
            pkg.ownername = '%s (%s)' % (user['human_name'], user['username'])
            pkg.ownerid = user['id']
            if pkg.qacontact:
                (user, groups) = fas.get_user_info(pkg.qacontact)
                pkg.qacontactname = '%s (%s)' % (user['human_name'],
                        user['username'])
            else:
                pkg.qacontactname = ''

            ### FIXME: Reevaluate this as we've added a relation/backref
            # To access acls
            acls = model.PackageAcl.select((
                model.PackageAcl.c.packagelistingid==pkg.id))

            # Reformat the data so we have it stored per user
            people = {}
            for acl in acls:
                for user in acl.people:
                    if not people.has_key(user.userid):
                        (person, groups) = fas.get_user_info(user.userid)
                        people[user.userid] = AclOwners(
                                '%s (%s)' % (person['human_name'],
                                    person['username']), aclNames)

                    people[user.userid].acls[user.acl.acl] = \
                            model.StatusTranslation.get_by(
                                model.StatusTranslation.c.statuscodeid==user.status,
                                model.StatusTranslation.c.language=='C').statusname

            # Store the acl owners in the package
            pkg.people = people
        return dict(title='%s -- %s' % (appTitle, package.name),
                package=package, packageid=packageId,
                packageListings=pkgListings, aclNames=aclNames,
                aclStatus=aclStatusTranslations)

    @expose(template='pkgdb.templates.errors')
    def unknown(self, packageId):
        msg = 'The packageId you were linked to, %s, does not exist.' \
                ' If you received this error from a link on the' \
                ' fedoraproject.org website, please report it.' % packageId
        return dict(title=appTitle + ' -- Unknown Package', msg=msg)

    @expose(template='pkgdb.templates.errors')
    def not_id(self):
        msg = 'The packageId you were linked to is not a valid id.' \
                ' If you received this error from a link on the' \
                ' fedoraproject.org website, please report it.'
        return dict(title=appTitle + ' -- Invalid Package Id', msg=msg)

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
                    forward_url=forward_url, title='Fedora Account System Login')

    @expose()
    def logout(self):
        identity.current.logout()
        raise redirect(request.headers.get("Referer","/"))

