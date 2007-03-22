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
log = logging.getLogger("pkgdb.controllers")

# The Fedora Account System Module
from fedora.accounts.fas import AccountSystem, AuthError

appTitle = 'Fedora Package Database'
fas = AccountSystem()

ORPHAN_ID=9900
FROMADDR=config.get('from_address')
TOADDR=config.get('commits_address')

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

        ### FIXME: pull groups from somewhere.
        # In the future the list of groups that can commit to packages should
        # be stored in a database somewhere.  Either packagedb or FAS should
        # have a flag.

        # Create a list of groups that can possibly commit to packages
        self.groups = {100300: 'cvsextras'}

    def _user_can_set_acls(self, userid, pkg):
        '''Check that the current user can set acls.
        '''
        # Make sure the current tg user has permission to set acls
        if userid == pkg.owner:
            # We're talking to the owner
            return True
        # Wasn't the owner.  See if they have been granted permission
        for person in pkg.people:
            if person.userid == userid:
                # Check each acl that this person has on the package.
                for acl in person.acls:
                    if (acl.acl == 'approveacls' and acl.statuscode
                            == self.aclStatusMap['Approved'].statuscodeid):
                        return True
                break
        return False

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
            logMessage = 'Package %s in %s %s was orphaned by %s (%s)' % (
                    pkg.package.name, pkg.collection.name,
                    pkg.collection.version, identity.current.user.display_name,
                    identity.current.user_name)
            status = model.StatusTranslation.get_by(statusname='Orphaned')
        elif pkg.owner == ORPHAN_ID:
            # Take ownership
            pkg.owner = identity.current.user.user_id
            ownerName = '%s (%s)' % (identity.current.user.display_name,
                    identity.current.user_name)
            logMessage = 'Package %s in %s %s is now owned by %s' % (
                    pkg.package.name, pkg.collection.name,
                    pkg.collection.version, ownerName)
            status = model.StatusTranslation.get_by(statusname='Owned')
        else:
            return dict(status=False, message=
                    'Package %s not available for taking' % containerId)

        # Make sure a log is created in the db as well.
        log = model.PackageListingLog(identity.current.user.user_id,
                status.statuscodeid, logMessage, None, containerId)
        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Not able to change owner information for %s' \
                            % (containerId))

        # Send a log to the commits list as well
        email = turbomail.Message(FROMADDR, TOADDR, '[pkgdb] %s %s' % (
            pkg.package.name, status.statusname))
        email.plain = logMessage
        turbomail.enqueue(email)

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
            fas.verify_user_pass(personid, '')
        except AuthError, e:
            if str(e).startswith('No such user: '):
                return dict(status=False,
                        message=str(e))
            else:
                raise

        approved = self._user_can_set_acls(identity.current.user.user_id, pkg)
        if not approved:
            return dict(status=False, message=
                    '%s is not allowed to approve Package ACLs' %
                    identity.current.user.display_name)

        # Create the ACL
        changePerson = None
        for person in pkg.people:
            # Check for the person who's acl we're setting
            if person.userid == personid:
                changePerson = person
                break
        if not changePerson:
            # Person has no ACLs on this Package yet.  Create a record
            personPackage = model.PersonPackageListing(personid, pkgid)
            personPackage.acls.append(model.PersonPackageListingAcl(
                newAcl, self.aclStatusMap[status].statuscodeid))
        else:
            # Look for an acl for the person
            personAcl = None
            for acl in changePerson.acls:
                if acl.acl == newAcl:
                    # Found the acl, change its status
                    personAcl = acl
                    acl.statuscode = self.aclStatusMap[status].statuscodeid
                    break
            if not personAcl:
                # Acl was not found.  Create one.
                changePerson.acls.append(model.PersonPackageListingAcl(
                    newAcl, self.aclStatusMap[status].statuscodeid))
        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Not able to create acl %s on %s with status %s' \
                            % (newAcl, pkgid, status))

        return dict(status=True)

    @expose('json')
    # Check that the requestor is in a group that could potentially set ACLs.
    @identity.require(identity.in_group("cvsextras"))
    def toggle_groupacl_status(self, containerId):
        '''Set the groupacl to determine whether the group can commit.
        '''
        # Pull apart the identifier
        pkgListId, groupId, aclName = containerId.split(':')
        pkgListId = int(pkgListId)
        groupId = int(groupId)

        # Make sure the package listing exists
        pkg = model.PackageListing.get_by(
                model.PackageListing.c.id==pkgListId)
        if not pkg:
            return dict(status=False,
                    message='Package Listing %s does not exist' % pkgListId)

        # Check whether the user is allowed to set this
        approved = self._user_can_set_acls(identity.current.user.user_id, pkg)
        if not approved:
            return dict(status=False, message=
                    '%s is not allowed to approve Package ACLs' %
                    identity.current.user.display_name)

        # Make sure the group exists
        # Note: We don't let every group in the FAS have access to packages.
        if groupId not in self.groups:
            return dict(status=False, message='%s is not a group that can commit'
                    ' to packages' % groupId)
       
        # See if the group has a record
        changeGroup = None
        changeAcl = None
        for group in pkg.groups:
            if group.groupid == groupId:
                changeGroup = group
                # See if the group has an acl
                for acl in group.acls:
                    if acl.acl == aclName:
                        changeAcl = acl
                        # toggle status
                        if acl.status.translations[0].statusname == 'Approved':
                            acl.statuscode = self.aclStatusMap['Denied'].statuscodeid
                        else:
                            acl.statuscode = self.aclStatusMap['Approved'].statuscodeid
                        break
                if not changeAcl:
                    # if no acl yet create it
                    changeAcl = model.GroupPackageListingAcl(changeGroup.id,
                            'commit',
                            self.aclStatusMap['Approved'].statuscodeid)
                break

        if not changeGroup:
            # No record for the group yet, create it
            changeGroup = model.GroupPackageListing(groupId, pkgListId)
            changeAcl = model.GroupPackageListingAcl(changeGroup.id, 'commit',
                    self.aclStatusMap['Approved'].statuscodeid)

        return dict(status=True,
                newAclStatus=changeAcl.status.translations[0].statusname)

    @expose('json')
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.not_anonymous())
    def toggle_acl_request(self, containerId):
        # Make sure package exists
        pkgListId, aclName = containerId.split(':')
        pkgListing = model.PackageListing.get_by(id=pkgListId)
        if not pkgListing:
            return dict(status=False, message='No such package listing %s' % pkgListId)

        # See if the Person is already associated with the pkglisting.
        person = model.PersonPackageListing.get_by(sqlalchemy.and_(
                model.PersonPackageListing.c.packagelistingid==pkgListId,
                model.PersonPackageListing.c.userid==
                    identity.current.user.user_id))
        if not person:
            # There was no association, create it.
            person = model.PersonPackageListing(
                identity.current.user.user_id, pkgListId)
            person.acls.append(model.PersonPackageListingAcl(aclName,
                self.aclStatusMap['Awaiting Review'].statuscodeid))
            aclStatus = 'Awaiting Review'
        else:
            # Check whether the person already has this acl
            aclSet = False
            for acl in person.acls:
                if acl.acl == aclName:
                    # Acl already exists, set the status
                    if self.aclStatusMap['Obsolete'].statuscodeid == acl.statuscode:
                        acl.statuscode = self.aclStatusMap['Awaiting Review'].statuscodeid
                        aclStatus = 'Awaiting Review'
                    else:
                        acl.statuscode = self.aclStatusMap['Obsolete'].statuscodeid
                        aclStatus = ''
                    aclSet = True
                    break
            if not aclSet:
                # Create a new acl
                person.acls.append(model.PersonPackageListingAcl(aclName,
                        self.aclStatusMap['Awaiting Review'].statuscodeid))
                aclStatus = 'Awaiting Review'

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # Probably the acl is mispelled
            return dict(status=False,
                    message='Not able to create acl %s for %s on %s' %
                        (aclName, identity.current.user.user_id,
                        pkgListId))

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
                model.PackageTable.c.statuscode ==
                    model.StatusTranslationTable.c.statuscodeid,
                model.StatusTranslationTable.c.language=='C',
                model.PackageTable.c.id==packageId), limit=1).execute()
        if pkgRow.rowcount <= 0:
            raise redirect(config.get('base_url_filter.base_url') + '/packages/unknown',
                redirect_params={'packageId' : packageId})
        package = pkgRow.fetchone()

        # Possible ACLs
        aclNames = ('watchbugzilla', 'watchcommits', 'commit', 'approveacls')
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

            for person in pkg.people:
                # Retrieve info from the FAS about the people watching the pkg
                (fasPerson, groups) = fas.get_user_info(person.userid)
                person.name = '%s (%s)' % (fasPerson['human_name'],
                        fasPerson['username'])
                # Setup acls to be accessible via aclName
                person.aclOrder = {}
                for acl in aclNames:
                    person.aclOrder[acl] = None
                for acl in person.acls:
                    if acl.status.translations[0].statusname != 'Obsolete':
                        person.aclOrder[acl.acl] = acl

            for group in pkg.groups:
                # Retrieve info from the FAS about a group
                fasGroup = fas.get_group_info(group.groupid)
                group.name = fasGroup['name']
                # Setup acls to be accessible via aclName
                group.aclOrder = {}
                for acl in aclNames:
                    group.aclOrder[acl] = None
                for acl in group.acls:
                    group.aclOrder[acl.acl] = acl

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

