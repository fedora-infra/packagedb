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
from fedora.accounts.fas import AccountSystem, AuthError

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

        ### FIXME: This is happening in two places: Here and in packages::id().
        # We should eventually only pass it in packages::id() but translating
        # from python to javascript makes this hard.

        # Possible statuses for acls:
        aclStatus = SelectResults(session.query(model.PackageAclStatus))
        self.aclStatusTranslations=['']
        self.aclStatusMap = {}
        # Create a mapping from status name => statuscode
        for status in aclStatus:
            ### FIXME: At some point, we have to pull other translations out,
            # not just C
            if status.translations[0].statusname != 'Obsolete':
                self.aclStatusTranslations.append(status.translations[0].statusname)
            self.aclStatusMap[status.translations[0].statusname] = status


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

        return dict(status=True, ownerId=pkg.owner, ownerName=ownerName,
                aclStatusFields=self.aclStatusTranslations)

    @expose('json')
    # Check that the requestor is in a group that could potentially set ACLs.
    @identity.require(identity.in_group("cvsextras"))
    def set_acl_status(self, pkgid, personid, newAcl, status):
        ### FIXME: Changing Obsolete into "" sounds like it should be
        # Pushed out to the view (template) instead of being handled in the
        # controller.

        # We are making Obsolete into "" for our interface.  Need to reverse
        # that here.
        if not status or not status.strip():
            status = 'Obsolete'

        # Change strings into numbers because we do some comparisons later on
        pkgid = int(pkgid)
        personid = int(personid)

        # Make sure the package listing exists
        pkg = model.PackageListing.get_by(
                model.PackageListing.c.id==pkgid)
        if not pkg:
            return dict(status=False,
                    message='Package Listing %s does not exist' % pkgid)

        # Make sure the person we're setting the acl for exists
        try:
            fas.verify_user_pass(int(personid), '')
        except AuthError, e:
            print str(e)
            if str(e).startswith('No such user: '):
                return dict(status=False,
                        message=str(e))
            else:
                raise

        # Make sure the current tg user has permission to set acls
        acls = SelectResults(session.query(model.PackageAcl)).select(
                model.PackageAcl.c.packagelistingid==pkgid)
        if identity.current.user.user_id != pkg.owner:
            # Wasn't the owner, see if they have been granted permission
            comaintAcls = acls.select(
                    model.PackageAcl.c.acl=='approveacls').join_to(
                            'people').select(sqlalchemy.and_(
                                model.PersonPackageAcl.c.userid==identity.current.user.user_id,
                                model.PersonPackageAcl.c.status==self.aclStatusMap['Approved']))
            if not comaintAcls.count():
                return dict(status=False, message='%s is not allowed to approve Package ACLs' % identity.current.user.display_name)
       
        # Look for the acl to change
        acl = acls.select(model.PackageAcl.c.acl==newAcl)
        if not acl.count():
            # Have to create the acl
            packageAcl = model.PackageAcl(pkgid, newAcl)
            personAcl = model.PersonPackageAcl(packageAcl.id,
                personid, self.aclStatusMap[status].statuscodeid)
        else:
            # Look for an acl for the person
            personAcl = None
            for person in acl[0].people:
                if person.userid == personid:
                    personAcl = person
                    person.status = self.aclStatusMap[status].statuscodeid
                    break
            # personAcl wasn't found; create it
            if not personAcl:
                personAcl = model.PersonPackageAcl(acl[0].id,
                        personid,
                        self.aclStatusMap[status].statuscodeid)
        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Not able to create acl %s on %s with status %s' \
                            % (newAcl, pkgid, status))

        return dict(status=True)

    @expose('json')
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.not_anonymous())
    def toggle_acl_request(self, containerId):
        # Make sure package exists
        pkgListId, aclName = containerId.split(':')
        pkgListing = model.PackageListing.get_by(id=pkgListId)
        if not pkgListing:
            return dict(status=False, message='No such package listing %s' % pkgListId)

        # See if the ACL already exists
        pkgList = SelectResults(session.query(model.PackageAcl)).select(
                sqlalchemy.and_(model.PackageAcl.c.packagelistingid==pkgListId,
                    model.PackageAcl.c.acl==aclName))
        if not pkgList.count():
            # Create the acl
            packageAcl = model.PackageAcl(pkgListId, aclName)
            try:
                session.flush()
            except sqlalchemy.exceptions.SQLError, e:
                # Probably the acl is mispelled
                return dict(status=False,
                        message='Not able to create acl %s on %s' %
                            (aclName, pkgListId))

        # See if there's already an acl for this person 
        personPkgList = pkgList.join_to('people').select(
                model.PersonPackageAcl.c.userid ==
                identity.current.user.user_id)
        if (personPkgList.count()):
            # An Acl already exists.  Build on that
            for person in personPkgList[0].people:
                if person.userid == identity.current.user.user_id:
                    personAcl = person
                    break
            if personAcl.status == self.aclStatusMap['Obsolete'].statuscodeid:
                # If the Acl status is obsolete, change to awaiting review
                personAcl.status = self.aclStatusMap['Awaiting Review'].statuscodeid
                aclStatus = 'Awaiting Review'
            else:
                # Set it to obsolete
                personAcl.status = self.aclStatusMap['Obsolete'].statuscodeid
                aclStatus = ''
        else:
            # No ACL yet, create acl
            personAcl = model.PersonPackageAcl(pkgList[0].id,
                    identity.current.user.user_id,
                    self.aclStatusMap['Awaiting Review'].statuscodeid)
            aclStatus = 'Awaiting Review'

        # Return the new value
        return dict(status=True, personId=identity.current.user.user_id,
                aclStatusFields=self.aclStatusTranslations, aclStatus=aclStatus)

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
            if aclStatusTranslations != 'Obsolete':
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
                    personAcl = model.StatusTranslation.get_by(
                            model.StatusTranslation.c.statuscodeid==user.status,
                            model.StatusTranslation.c.language=='C').statusname
                    if personAcl == 'Obsolete':
                        continue
                    if not people.has_key(user.userid):
                        (person, groups) = fas.get_user_info(user.userid)
                        people[user.userid] = AclOwners(
                                '%s (%s)' % (person['human_name'],
                                    person['username']), aclNames)
                    people[user.userid].acls[user.acl.acl] = personAcl

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

