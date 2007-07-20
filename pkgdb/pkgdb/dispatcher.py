import sqlalchemy
from sqlalchemy.ext.selectresults import SelectResults
import sqlalchemy.mods.selectresults

import turbomail
from turbogears import controllers, expose, identity, config
from turbogears.database import session

from fedora.accounts.fas import AuthError

from pkgdb import model

COMMITSLIST=config.get('commits_address')
ORPHAN_ID=9900

def send_msg(msg, subject, recipients):
    '''Send a message from the packagedb.'''
    fromAddr = config.get('from_address')
    for person in recipients:
        email = turbomail.Message(fromAddr, person, '[pkgdb] %s' % (subject,))
        email.plain = msg
        turbomail.enqueue(email)

class PackageDispatcher(controllers.Controller):
    def __init__(self, fas = None):
        self.fas = fas
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
        # Create a mapping from status name => statuscode
        for status in aclStatus:
            ### FIXME: At some point, we have to pull other translations out,
            # not just C
            if status.translations[0].statusname != 'Obsolete':
                self.aclStatusTranslations.append(status.translations[0].statusname)

        ### FIXME: pull groups from somewhere.
        # In the future the list of groups that can commit to packages should
        # be stored in a database somewhere.  Either packagedb or FAS should
        # have a flag.

        # Create a list of groups that can possibly commit to packages
        self.groups = {100300: 'cvsextras',
                101197: 'cvsadmin'}

    def _send_log_msg(self, msg, subject, author, pkgListing, acls=None,
            otherEmail=None):
        # Store the email addresses in a hash to eliminate duplicates
        recipients = {COMMITSLIST: '',
                author.user['email']: ''}

        acls = acls or ('approveacls',)
        if otherEmail:
            for email in otherEmail:
                recipients[email] = ''
        # Get the owner for this package
        if pkgListing.owner != ORPHAN_ID:
            (owner, group) = self.fas.get_user_info(pkgListing.owner)
            recipients[owner['email']] = ''

        # Get the co-maintainers
        aclUsers = SelectResults(session.query(model.PersonPackageListingAcl)
                ).select(model.PersonPackageListingAcl.c.personpackagelistingid == model.PersonPackageListing.c.id
                ).select(model.PersonPackageListing.c.packagelistingid==pkgListing.id
                ).select(model.PersonPackageListingAcl.c.acl.in_(*acls))
        for acl in aclUsers:
            if acl.status.translations[0].statusname=='Approved':
                (person, groups) = self.fas.get_user_info(acl.personpackagelisting.userid)
                recipients[person['email']] = ''

        # Send the log
        send_msg(msg, subject, recipients.keys())

    def _user_can_set_acls(self, identity, pkg):
        '''Check that the current user can set acls.

        This method will return one of these values:
            'admin', 'owner', 'comaintainer', False
        depending on why the user is granted access.  You can therefore use the
        value for finer grained access to some resources.
        '''
        # Find the approved statuscode
        status = model.StatusTranslation.get_by(statusname='Approved')

        # Make sure the current tg user has permission to set acls
        # If the user is a cvsadmin they can
        if identity.in_group('cvsadmin'):
            return 'admin'
        # The owner can
        if identity.current.user.user_id == pkg.owner:
            return 'owner'
        # Wasn't the owner.  See if they have been granted permission
        # explicitly
        for person in pkg.people:
            if person.userid == userid:
                # Check each acl that this person has on the package.
                for acl in person.acls:
                    if (acl.acl == 'approveacls' and acl.statuscode
                            == status.statuscodeid):
                        return 'comaintainer'
                break
        return False

    @expose('json')
    def index(self):
        return dict(methods=self.methods)

    @expose('json')
    # Check that the tg.identity is allowed to set themselves as owner
    @identity.require(identity.in_any_group('cvsextras', 'cvsadmin'))
    def toggle_owner(self, containerId):
        
        # Check that the pkgid is orphaned
        pkg = model.PackageListing.get_by(id=containerId)
        if not pkg:
            return dict(status=False, message='No such package %s' % containerId)
        approved = self._user_can_set_acls(identity, pkg)
        if pkg.owner == ORPHAN_ID:
            # Take ownership
            pkg.owner = identity.current.user.user_id
            ownerName = '%s (%s)' % (identity.current.user.display_name,
                    identity.current.user_name)
            logMessage = 'Package %s in %s %s is now owned by %s' % (
                    pkg.package.name, pkg.collection.name,
                    pkg.collection.version, ownerName)
            status = model.StatusTranslation.get_by(statusname='Owned')
        elif approved in ('admin', 'owner'):
            # Release ownership
            pkg.owner = ORPHAN_ID
            ownerName = 'Orphaned Package (orphan)'
            logMessage = 'Package %s in %s %s was orphaned by %s (%s)' % (
                    pkg.package.name, pkg.collection.name,
                    pkg.collection.version, identity.current.user.display_name,
                    identity.current.user_name)
            status = model.StatusTranslation.get_by(statusname='Orphaned')
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

        # Send a log to people interested in this package as well
        self._send_log_msg(logMessage, '%s %s' % (pkg.package.name,
            status.statusname), identity.current.user, pkg,
            ('approveacls', 'watchbugzilla', 'watchcommits', 'build', 'commit'))

        return dict(status=True, ownerId=pkg.owner, ownerName=ownerName,
                aclStatusFields=self.aclStatusTranslations)

    @expose('json')
    # Check that the requestor is in a group that could potentially set ACLs.
    @identity.require(identity.in_any_group('cvsextras', 'cvsadmin'))
    def set_acl_status(self, pkgid, personid, newAcl, statusname):
        ### FIXME: Changing Obsolete into "" sounds like it should be
        # Pushed out to the view (template) instead of being handled in the
        # controller.

        # We are making Obsolete into "" for our interface.  Need to reverse
        # that here.
        if not statusname or not statusname.strip():
            statusname = 'Obsolete'
        status = model.StatusTranslation.get_by(statusname=statusname)

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
            self.fas.verify_user_pass(personid, '')
        except AuthError, e:
            if str(e).startswith('No such user: '):
                return dict(status=False,
                        message=str(e))
            else:
                raise

        approved = self._user_can_set_acls(identity, pkg)
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
            changePerson = model.PersonPackageListing(personid, pkgid)
            personAcl = model.PersonPackageListingAcl(newAcl,
                    status.statuscodeid)
            personAcl.personpackagelisting = changePerson
        else:
            # Look for an acl for the person
            personAcl = None
            for acl in changePerson.acls:
                if acl.acl == newAcl:
                    # Found the acl, change its status
                    personAcl = acl
                    acl.statuscode = status.statuscodeid
                    break
            if not personAcl:
                # Acl was not found.  Create one.
                personAcl = model.PersonPackageListingAcl(newAcl,
                        status.statuscodeid)
                personAcl.personpackagelisting = changePerson

        # Get the human name and username for the person whose acl we changed
        (user, groups) = self.fas.get_user_info(personAcl.personpackagelisting.userid)
        # Make sure a log is created in the db as well.
        logMessage = u'%s (%s) has set the %s acl on %s (%s %s) to %s for %s (%s)' % (
                    identity.current.user.display_name,
                    identity.current.user_name, newAcl, pkg.package.name,
                    pkg.collection.name, pkg.collection.version,
                    status.statusname,
                    user['human_name'], user['username'])
        log = model.PersonPackageListingAclLog(identity.current.user.user_id,
                status.statuscodeid, logMessage)
        log.acl = personAcl

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Not able to create acl %s on %s with status %s' \
                            % (newAcl, pkgid, status))
        # Send a log to people interested in this package as well
        self._send_log_msg(logMessage, '%s set to %s for %s' % (newAcl,
            status.statusname, user['human_name']), identity.current.user,
            pkg, otherEmail=(user['email'],))

        return dict(status=True)

    @expose('json')
    # Check that the requestor is in a group that could potentially set ACLs.
    @identity.require(identity.in_any_group('cvsextras', 'cvsadmin'))
    def toggle_groupacl_status(self, containerId):
        '''Set the groupacl to determine whether the group can commit.

        WARNING: Do not use changeAcl.status in this method.  There is a high
        chance that it will be out of sync with the current statuscode after
        the status is set.  Updating changeAcl.status at the same time as we
        update changeAcl.statuscodeid makes this method take 10-11s instead of
        <1s.

        If you cannot live without changeAcl.status, try flushing the session
        after changeAcl.statuscodeid is set and see if that can automatically
        refresh the status without the performance hit.
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
        approved = self._user_can_set_acls(identity, pkg)
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
        approvedStatus = model.StatusTranslation.get_by(statusname='Approved')
        deniedStatus = model.StatusTranslation.get_by(statusname='Denied')
        for group in pkg.groups:
            if group.groupid == groupId:
                changeGroup = group
                # See if the group has an acl
                for acl in group.acls:
                    if acl.acl == aclName:
                        changeAcl = acl
                        # toggle status
                        if acl.status.translations[0].statusname == 'Approved':
                            changeAcl.statuscode = deniedStatus.statuscodeid
                        else:
                            changeAcl.statuscode = approvedStatus.statuscodeid
                        ### WARNING: At this point changeAcl.status is out of
                        # sync with changeAcl.statuscode.  There is a large
                        # performance penalty to setting it here.
                        # If you need it, try doing a session.flush() here and
                        # repull the information from the database.
                        break
                if not changeAcl:
                    # if no acl yet create it
                    changeAcl = model.GroupPackageListingAcl(aclName,
                            approvedStatus.statuscodeid)
                    changeAcl.grouppackagelisting = changeGroup
                break

        if not changeGroup:
            # No record for the group yet, create it
            changeGroup = model.GroupPackageListing(groupId, pkgListId)
            changeAcl = model.GroupPackageListingAcl(aclName,
                    approvedStatus.statuscodeid)
            changeAcl.grouppackagelisting = changeGroup
        
        ### WARNING: changeAcl.status is very likely out of sync at this point.
        # See the docstring for an explanation.

        # Make sure a log is created in the db as well.
        statusname = model.StatusTranslation.get_by(
                statuscodeid=changeAcl.statuscode).statusname
        logMessage = '%s (%s) has set the %s acl on %s (%s %s) to %s for %s' % (
                    identity.current.user.display_name,
                    identity.current.user_name, aclName, pkg.package.name,
                    pkg.collection.name, pkg.collection.version, statusname,
                    self.groups[changeGroup.groupid])
        log = model.GroupPackageListingAclLog(identity.current.user.user_id,
                changeAcl.statuscode, logMessage)
        log.acl = changeAcl

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Not able to create acl %s on %s with status %s' \
                            % (newAcl, pkgid, status))

        # Send a log to people interested in this package as well
        self._send_log_msg(logMessage, '%s set to %s for %s' % (aclName,
            statusname, self.groups[changeGroup.groupid]),
            identity.current.user, pkg)

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
        awaitingStatus = model.StatusTranslation.get_by(
                statusname='Awaiting Review')
        obsoleteStatus = model.StatusTranslation.get_by(statusname='Obsolete')
        if not person:
            # There was no association, create it.
            person = model.PersonPackageListing(
                    identity.current.user.user_id, pkgListId)
            personAcl = model.PersonPackageListingAcl(aclName,
                    awaitingStatus.statuscodeid)
            personAcl.personpackagelisting = person
            aclStatus = 'Awaiting Review'
        else:
            # Check whether the person already has this acl
            aclSet = False
            for acl in person.acls:
                if acl.acl == aclName:
                    # Acl already exists, set the status
                    personAcl = acl
                    if obsoleteStatus.statuscodeid == acl.statuscode:
                        acl.statuscode = awaitingStatus.statuscodeid
                        aclStatus = 'Awaiting Review'
                    else:
                        acl.statuscode = obsoleteStatus.statuscodeid
                        aclStatus = ''
                    aclSet = True
                    break
            if not aclSet:
                # Create a new acl
                personAcl = model.PersonPackageListingAcl(aclName,
                        awaitingStatus.statuscodeid)
                personAcl.personpackagelisting = person
                aclStatus = 'Awaiting Review'

        # Make sure a log is created in the db as well.
        if aclStatus == 'Awaiting Review':
            aclAction = 'requested'
        else:
            aclAction = 'given up'
        logMessage = '%s (%s) has %s the %s acl on %s (%s %s)' % (
                    identity.current.user.display_name,
                    identity.current.user_name, aclAction, aclName,
                    pkgListing.package.name, pkgListing.collection.name,
                    pkgListing.collection.version)
        log = model.PersonPackageListingAclLog(identity.current.user.user_id,
                personAcl.statuscode, logMessage)
        log.acl = personAcl

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # Probably the acl is mispelled
            return dict(status=False,
                    message='Not able to create acl %s for %s on %s' %
                        (aclName, identity.current.user.user_id,
                        pkgListId))

        # Send a log to the commits list as well
        self._send_log_msg(logMessage, '%s has %s %s for %s' % (
                    identity.current.user.display_name, aclAction, aclName,
                    pkgListing.package.name), identity.current.user, pkgListing)

        # Return the new value
        return dict(status=True, personId=identity.current.user.user_id,
                aclStatusFields=self.aclStatusTranslations, aclStatus=aclStatus)
