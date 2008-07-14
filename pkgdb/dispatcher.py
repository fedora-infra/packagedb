# -*- coding: utf-8 -*-
#
# Copyright © 2007-2008  Red Hat, Inc. All rights reserved.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.  You should have
# received a copy of the GNU General Public License along with this program;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
# incorporated in the source code or documentation are not subject to the GNU
# General Public License and may only be used or replicated with the express
# permission of Red Hat, Inc.
#
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Controller to process requests to change package information.
'''

import sqlalchemy
from sqlalchemy.exceptions import InvalidRequestError

from turbogears import controllers, expose, identity, config
from turbogears.database import session

import simplejson

from pkgdb import model
from pkgdb.notifier import EventLogger

ORPHAN_ID = 9900
MAXSYSTEMUID = 9999

class AclNotAllowedError(Exception):
    '''The entity specified is not allowed to hold the requested acl.
    '''
    pass

class PackageDispatcher(controllers.Controller):
    '''Controller for all methods which modify the package tables.
    '''
    eventLogger = EventLogger()

    ### FIXME: pull groups from somewhere.
    # In the future the list of groups that can commit to packages should
    # be stored in a database somewhere.  Either packagedb or FAS should
    # have a flag.
    # Nearer term, we want to split name=>id mapping from id=>name mapping.
    # Waiting for the cvsextras=>packager rename will make this easier though.

    # Create a list of groups that can possibly commit to packages
    groups = {100300: 'cvsextras',
            101197: 'cvsadmin',
            107427: 'uberpackager',
            'cvsextras': 100300,
            'cvsadmin': 101197,
            'uberpackager': 107427}
    groupnames = ('cvsextras', 'packager', 'cvsadmin', 'uberpackager')

    # Status codes
    addedStatus = model.StatusTranslation.query.filter_by(
            statusname='Added').one()
    approvedStatus = model.StatusTranslation.query.filter_by(
            statusname='Approved').one()
    awaitingReviewStatus = model.StatusTranslation.query.filter_by(
            statusname='Awaiting Review').one()
    deniedStatus = model.StatusTranslation.query.filter_by(
            statusname='Denied').one()
    modifiedStatus = model.StatusTranslation.query.filter_by(
            statusname='Modified').one()
    obsoleteStatus = model.StatusTranslation.query.filter_by(
            statusname='Obsolete').one()
    orphanedStatus = model.StatusTranslation.query.filter_by(
            statusname='Orphaned').one()
    ownedStatus = model.StatusTranslation.query.filter_by(
            statusname='Owned').one()

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
        aclStatus = session.query(model.PackageAclStatus)
        self.aclStatusTranslations = ['']
        # Create a mapping from status name => statuscode
        for status in aclStatus:
            ### FIXME: At some point, we have to pull other translations out,
            # not just C
            if status.translations[0].statusname != 'Obsolete':
                self.aclStatusTranslations.append(
                        status.translations[0].statusname)

    def _send_log_msg(self, msg, subject, author, listings, acls=None,
            otherEmail=None):
        '''Send a log message to interested parties.

        This takes a message and determines who to send it to.

        Arguments:
        :msg: The log message to send
        :subject: Subject or summary for the message
        :author: Author of the change
        :listings: Package Listings affected by the change
        :acls: If specified, people on these acls will be notified.  Defaults
            to the people in the approveacls group
        :otherEmail: Other email addresses to send notification to
        '''
        # Store the email addresses in a hash to eliminate duplicates
        recipients = {author['email']: ''}

        # Note: We have to copy information from the config system to our
        # own variables because the config system is writable persistent
        # storage.  ie: If we don't the list of recipients will keep getting
        # longer and longer.
        for recipient in config.get('email.recipients',
                ('toshio@fedoraproject.org',)):
            recipients[recipient] = ''

        acls = acls or ('approveacls',)
        if otherEmail:
            for email in otherEmail:
                recipients[email] = ''
        # Get the owners for this package
        for pkgListing in listings:
            if pkgListing.owner != ORPHAN_ID:
                try:
                    owner = self.fas.cache[pkgListing.owner]
                except KeyError:
                    owner = {}
                else:
                    recipients[owner['email']] = ''

            # Get the co-maintainers
            aclUsers = model.PersonPackageListingAcl.query.filter(
                sqlalchemy.and_(
                    model.PersonPackageListingAcl.c.personpackagelistingid == model.PersonPackageListing.c.id,
                model.PersonPackageListing.c.packagelistingid==pkgListing.id,
                model.PersonPackageListingAcl.c.acl.in_(*acls)))

            for acl in aclUsers:
                if acl.status.translations[0].statusname=='Approved':
                    try:
                        person = self.fas.cache[acl.personpackagelisting.userid]
                    except KeyError:
                        person = {}
                    else:
                        recipients[person['email']] = ''

        # Append a link to the package to the message
        msg = msg + '\n\nTo make changes to this package see:' \
              '\n  %s/packages/name/%s' % (
                      config.get('base_url_filter.base_url'),
                      listings[0].package.name)

        # Send the log
        self.eventLogger.send_msg(msg, subject, recipients.keys())

    def _user_can_set_acls(self, ident, pkg):
        '''Check that the current user can set acls.

        This method will return one of these values::
            'admin', 'owner', 'comaintainer', False
        depending on why the user is granted access.  You can therefore use the
        value for finer grained access to some resources.

        :ident: the identity instance from this request
        :pkg: the packagelisting to find the user's permissions on
        '''
        # Find the approved statuscode
        status = self.approvedStatus

        # Make sure the current tg user has permission to set acls
        # If the user is a cvsadmin they can
        if ident.in_group('cvsadmin'):
            return 'admin'
        # The owner can
        if identity.current.user.id == pkg.owner:
            return 'owner'
        # Wasn't the owner.  See if they have been granted permission
        # explicitly
        for person in pkg.people:
            if person.userid == identity.current.user.id:
                # Check each acl that this person has on the package.
                for acl in person.acls:
                    if (acl.acl == 'approveacls' and acl.statuscode
                            == status.statuscodeid):
                        return 'comaintainer'
                break
        return False

    def _acl_can_be_held_by_user(self, acl, user=None):
        '''Return true if the user is allowed to hold the specified acl.

        Args:
        :acl: The acl to verify
        :user: The user to check.  Either a user, group tuple from FAS or None.
               If None, the current identity will be used.
        '''
        # Anyone can hold watchbugzilla or watchcommits
        if acl in ('watchbugzilla', 'watchcommits'):
            return True

        if acl == 'owner':
            if user:
                if user['id'] <= MAXSYSTEMUID:
                    # Any pseudo user can be the package owner
                    return True
                elif [group for group in user['approved_memberships'] if group['name'] in
                        self.groupnames]:
                    # If the user is in cvsextras or cvsadmin they are allowed
                    return True
                raise AclNotAllowedError('%s must be in one of these groups:' \
                        ' %s to own a package' %
                        (user['username'], self.groupnames))
            # Anyone in cvsextras or cvsadmin can potentially own the package
            elif identity.in_any_group(*self.groupnames):
                return True
            raise AclNotAllowedError(
                    '%s must be in one of these groups: %s to own a package' %
                    (identity.current.user_name, self.groupnames))

        # For any other acl, check whether the person is in an allowed group
        if user:
            # If the person isn't in cvsextras or cvsadmin raise an error
            if [group for group in user['approved_memberships'] if group['name'] in
                    self.groupnames]:
                return True
            raise AclNotAllowedError(
                    '%s must be in one of these groups: %s to hold the %s acl' %
                    (user['username'], self.groupnames, acl))
        elif identity.in_any_group(*self.groupnames):
            return True
        raise AclNotAllowedError(
                '%s must be in one of these groups: %s to hold the %s acl' %
                (identity.current.user_name, self.groupnames, acl))

    def _create_or_modify_acl(self, pkgList, personId, newAcl, status):
        '''Create or modify an acl.

        Set an acl for a user.  This takes a packageListing and makes sure
        there's an ACL for them with the given status.  It will create a new
        ACL or modify an existing one depending on what's in the db already.

        Arguments:
        :pkgList: PackageListing on which to set the ACL.
        :personId: PersonId to set the ACL for.
        :newAcl: ACL name to set.
        :status: Status DB Object we're setting the ACL to.
        '''
        # Create the ACL
        changePerson = None
        for person in pkgList.people:
            # Check for the person who's acl we're setting
            if person.userid == personId:
                changePerson = person
                break

        if not changePerson:
            # Person has no ACLs on this Package yet.  Create a record
            changePerson = model.PersonPackageListing(personId)
            pkgList.people.append(changePerson)
            personAcl = model.PersonPackageListingAcl(newAcl,
                    status.statuscodeid)
            changePerson.acls.append(personAcl) # pylint: disable-msg=E1101
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
                changePerson.acls.append(personAcl)

            # For now, we specialcase the build acl to reflect the commit
            # this is because we need to remove notifications and UI that
            # depend on any acl being set adn for now, the commit acl is being
            # used for build and push
            if newAcl == 'commit':
                self._create_or_modify_acl(pkgList, personId, 'build', status)

        return personAcl

    def _create_or_modify_group_acl(self, pkgList, groupId, newAcl, status):
        '''Create or modify a group acl.

        Set an acl for a group.  This takes a packageListing and makes sure
        there's an ACL for it with the given status.  It will create a new
        ACL or modify an existing one depending on what's in the db already.

        Arguments:
        :pkgList: PackageListing on which to set the ACL.
        :groupId: GroupId to set the ACL for.
        :newAcl: ACL name to set.
        :status: Status DB Objcet we're setting the ACL to.
        '''
        # Create the ACL
        changeGroup = None
        for group in pkgList.groups:
            # Check for the group who's acl we're setting
            if group.groupid == groupId:
                changeGroup = group
                break

        if not changeGroup:
            # Group has no ACLs on this Package yet.  Create a record
            changeGroup = model.GroupPackageListing(groupId)
            pkgList.groups.append(changeGroup)
            groupAcl = model.GroupPackageListingAcl(newAcl,
                    status.statuscodeid)
            changeGroup.acls.append(groupAcl) # pylint: disable-msg=E1101
        else:
            # Look for an acl for the group
            groupAcl = None
            for acl in changeGroup.acls:
                if acl.acl == newAcl:
                    # Found the acl, change its status
                    groupAcl = acl
                    acl.statuscode = status.statuscodeid
                    break
            if not groupAcl:
                # Acl was not found.  Create one.
                groupAcl = model.GroupPackageListingAcl(newAcl,
                        status.statuscodeid)
                changeGroup.acls.append(groupAcl)

        # For now, we specialcase the build acl to reflect the commit
        # this is because we need to remove notifications and UI that
        # depend on any acl being set adn for now, the commit acl is being
        # used for build and push
        if newAcl == 'commit':
            self._create_or_modify_group_acl(pkgList, groupId, 'build', status)
        return groupAcl

    @expose(allow_json=True)
    def index(self):
        '''
        Return a list of methods that can be called on this dispatcher.
        '''
        return dict(methods=self.methods)

    @expose(allow_json=True)
    @identity.require(identity.not_anonymous())
    def toggle_owner(self, containerId):
        '''Orphan package or set the owner to the logged in user.'''
        # Check that the pkg exists
        try:
            pkg = model.PackageListing.query.filter_by(id=containerId).one()
        except InvalidRequestError:
            return dict(status=False, message='No such package %s' % containerId)
        approved = self._user_can_set_acls(identity, pkg)
        if pkg.owner == ORPHAN_ID:
            # Check that the tg.identity is allowed to set themselves as owner
            try:
                self._acl_can_be_held_by_user('owner')
            except AclNotAllowedError, e:
                return dict(status=False, message=str(e))

            # Take ownership
            pkg.owner = identity.current.user.id
            ownerName = '%s (%s)' % (identity.current.display_name,
                    identity.current.user_name)
            logMessage = 'Package %s in %s %s is now owned by %s' % (
                    pkg.package.name, pkg.collection.name,
                    pkg.collection.version, ownerName)
            status = self.ownedStatus
        elif approved in ('admin', 'owner'):
            # Release ownership
            pkg.owner = ORPHAN_ID
            ownerName = 'Orphaned Package (orphan)'
            logMessage = 'Package %s in %s %s was orphaned by %s (%s)' % (
                    pkg.package.name, pkg.collection.name,
                    pkg.collection.version, identity.current.display_name,
                    identity.current.user_name)
            status = self.orphanedStatus
        else:
            return dict(status=False, message=
                    'Package %s not available for taking' % containerId)

        # Make sure a log is created in the db as well.
        log = model.PackageListingLog(identity.current.user.id,
                status.statuscodeid, logMessage, None, containerId)
        log.packagelistingid = pkg.id

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Not able to change owner information for %s' \
                            % (containerId))

        # Send a log to people interested in this package as well
        self._send_log_msg(logMessage, '%s ownership updated' %
            pkg.package.name, identity.current.user, (pkg,),
            ('approveacls', 'watchbugzilla', 'watchcommits', 'build', 'commit'))

        return dict(status=True, ownerId=pkg.owner, ownerName=ownerName,
                aclStatusFields=self.aclStatusTranslations)

    @expose(allow_json=True)
    # Check that the requestor is in a group that could potentially set ACLs.
    @identity.require(identity.not_anonymous())
    def set_acl_status(self, pkgid, personid, newAcl, statusname):
        '''Set the acl on a package to a particular status.

        :pkgid: packageListing.id
        :personid: userid of the person to make the request for
        :newAcl: The acl we're changing the status of
        :statusname: Status to change the acl to
        '''
        ### FIXME: Changing Obsolete into "" sounds like it should be
        # Pushed out to the view (template) instead of being handled in the
        # controller.
        
        # We are making Obsolete into "" for our interface.  Need to reverse
        # that here.
        if not statusname or not statusname.strip():
            statusname = 'Obsolete'
        try:
            status = model.StatusTranslation.query.filter_by(
                    statusname=statusname).one()
        except InvalidRequestError:
            return dict(status=False,
                    message='Invalid Status: %s' % statusname)

        # Change strings into numbers because we do some comparisons later on
        pkgid = int(pkgid)
        personid = int(personid)

        # Make sure the package listing exists
        try:
            pkg = model.PackageListing.query.filter_by(id=pkgid).one()
        except InvalidRequestError:
            return dict(status=False,
                    message='Package Listing %s does not exist' % pkgid)

        # Make sure the person we're setting the acl for exists
        # This can't come from cache ATM because it is used to call
        # _acl_can_be_held_by_user() which needs approved_group data.
        user = self.fas.person_by_id(personid)
        if not user:
            return dict(status=False,
                message='No such user for ID %(id)s, for package %(pkg)s in' \
                        ' %(collection)s %(version)s' %
                        {'id': personid, 'pkg': pkg.package.name,
                            'collection': pkg.collection.name,
                            'version': pkg.collection.version})

        # Check that the current user is allowed to change acl statuses
        approved = self._user_can_set_acls(identity, pkg)
        if not approved:
            return dict(status=False, message=
                    '%s is not allowed to approve Package ACLs' %
                    identity.current.display_name)

        #
        # Make sure the person is allowed on this acl
        #

        # Always allowed to remove an acl
        if statusname not in ('Denied', 'Obsolete'):
            try:
                self._acl_can_be_held_by_user(newAcl, user)
            except AclNotAllowedError, e:
                return dict(status=False, message=str(e))

        personAcl = self._create_or_modify_acl(pkg, personid, newAcl, status)

        # Make sure a log is created in the db as well.
        logMessage = u'%s (%s) has set the %s acl on %s (%s %s) to %s for' \
                ' %s (%s)' % (
                    identity.current.display_name,
                    identity.current.user_name, newAcl, pkg.package.name,
                    pkg.collection.name, pkg.collection.version, statusname,
                    user['human_name'], user['username'])
        log = model.PersonPackageListingAclLog(identity.current.user.id,
                status.statuscodeid, logMessage)
        log.acl = personAcl # pylint: disable-msg=W0201

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Not able to create acl %s on %s with status %s' \
                            % (newAcl, pkgid, statusname))
        # Send a log to people interested in this package as well
        self._send_log_msg(logMessage, '%s had acl change status' % (
                    pkg.package.name), identity.current.user, (pkg,),
                    otherEmail=(user['email'],))

        return dict(status=True)

    @expose(allow_json=True)
    # Check that the requestor is in a group that could potentially set ACLs.
    @identity.require(identity.not_anonymous())
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
        try:
            pkg = model.PackageListing.query.filter_by(id=pkgListId).one()
        except InvalidRequestError:
            return dict(status=False,
                    message='Package Listing %s does not exist' % pkgListId)

        # Check whether the user is allowed to set this acl
        approved = self._user_can_set_acls(identity, pkg)
        if not approved:
            return dict(status=False, message=
                    '%s is not allowed to approve Package ACLs for %s (%s %s)' %
                    (identity.current.display_name, pkg.package.name,
                        pkg.collection.name, pkg.collection.version))

        # Check that the group is one that we allow access to packages
        if groupId not in self.groups:
            return dict(status=False, message='%s is not a group that can '
                    'commit to packages' % groupId)

        #
        # Set the new acl status
        #

        aclStatus = 'Approved'
        # Determine if the group already has an acl
        try:
            acl = model.GroupPackageListingAcl.query.filter(sqlalchemy.and_(
                    model.GroupPackageListingAcl.c.grouppackagelistingid==model.GroupPackageListing.c.id,
                    model.GroupPackageListing.c.groupid==groupId,
                    model.GroupPackageListingAcl.c.acl==aclName,
                    model.GroupPackageListing.c.packagelistingid==pkgListId
                )).one()
        except InvalidRequestError:
            pass
        else:
            if acl.status.translations[0].statusname == 'Approved':
                aclStatus = 'Denied'

        status = {'Approved': self.approvedStatus,
                'Denied': self.deniedStatus}[aclStatus]
        # Change the acl
        groupAcl = self._create_or_modify_group_acl(pkg, groupId, aclName,
                status)
        
        ### WARNING: changeAcl.status is very likely out of sync at this point.
        # See the docstring for an explanation.

        # Make sure a log is created in the db as well.
        logMessage = '%s (%s) has set the %s acl on %s (%s %s) to %s for %s' % (
                    identity.current.display_name,
                    identity.current.user_name, aclName, pkg.package.name,
                    pkg.collection.name, pkg.collection.version, aclStatus,
                    self.groups[groupId])
        log = model.GroupPackageListingAclLog(identity.current.user.id,
                status.statuscodeid, logMessage)
        log.acl = groupAcl # pylint: disable-msg=W0201

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError:
            # An error was generated
            return dict(status=False, message='Not able to create acl %s on' \
                    ' %s(%s %s) with status %s' % (aclName,
                        pkg.package.name, pkg.collection.name,
                        pkg.collection.version, aclStatus))

        # Send a log to people interested in this package as well
        self._send_log_msg(logMessage, '%s had groupAcl changed' % (
                    pkg.package.name), identity.current.user, (pkg,))

        return dict(status=True, newAclStatus=aclStatus)

    @expose(allow_json=True)
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.not_anonymous())
    def toggle_acl_request(self, containerId):
        '''Request an acl or revoke a request.

        :containerId: The packageListing.id and aclName separated by a ":"
        '''
        # Make sure package exists
        pkgListId, aclName = containerId.split(':')
        try:
            pkgListing = model.PackageListing.query.filter_by(
                    id=pkgListId).one()
        except InvalidRequestError:
            return dict(status=False,
                    message='No such package listing %s' % pkgListId)

        # Determine whether we need to set a new acl
        aclStatus = 'Awaiting Review'
        # Determine if the user already has an acl
        try:
            acl = model.PersonPackageListingAcl.query.filter(sqlalchemy.and_(
                    model.PersonPackageListingAcl.c.personpackagelistingid == \
                            model.PersonPackageListing.c.id,
                    model.PersonPackageListing.c.userid == \
                            identity.current.user.id,
                    model.PersonPackageListingAcl.c.acl == aclName,
                    model.PersonPackageListing.c.packagelistingid == pkgListId)
                ).one()
        except InvalidRequestError:
            pass
        else:
            if acl.status.translations[0].statusname != 'Obsolete':
                aclStatus = 'Obsolete'

        if aclStatus != 'Obsolete':
            # Check that the person is in a correct group to receive the acl
            try:
                self._acl_can_be_held_by_user(aclName)
            except AclNotAllowedError, e:
                return dict(status=False, message=str(e))
        status = {'Awaiting Review': self.awaitingReviewStatus,
                'Obsolete': self.obsoleteStatus}[aclStatus]

        # Assign person to package
        personAcl = self._create_or_modify_acl(pkgListing,
                identity.current.user.id, aclName, status)

        # Make sure a log is created in the db as well.
        if aclStatus == 'Awaiting Review':
            aclAction = 'requested'
        else:
            aclAction = 'given up'
        logMessage = '%s (%s) has %s the %s acl on %s (%s %s)' % (
                    identity.current.display_name,
                    identity.current.user_name, aclAction, aclName,
                    pkgListing.package.name, pkgListing.collection.name,
                    pkgListing.collection.version)
        log = model.PersonPackageListingAclLog(identity.current.user.id,
                personAcl.statuscode, logMessage)
        log.acl = personAcl

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # Probably the acl is mispelled
            return dict(status=False,
                    message='Not able to create acl %s for %s on %s' %
                        (aclName, identity.current.user.id,
                        pkgListId))

        # Send a log to the commits list as well
        self._send_log_msg(logMessage, '%s: %s has %s %s' % (
                    pkgListing.package.name,
                    identity.current.user_name, aclAction, aclName),
                    identity.current.user, (pkgListing,))

        # Return the new value
        return dict(status=True, personId=identity.current.user.id,
                aclStatusFields=self.aclStatusTranslations, aclStatus=aclStatus)

    @expose(allow_json=True)
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.not_anonymous())
    def add_package(self, package, owner, summary):
        '''Add a new package to the database.
        '''
        # Check that the tg.identity is allowed to set an owner
        if not identity.in_any_group('cvsadmin'):
            return dict(status=False, message='User must be in cvsadmin')

        # Make sure the package doesn't already exist
        pkg = model.Package.query.filter_by(name=package)
        if pkg.count():
            return dict(status=False,
                    message='Package %s already exists' % package)

        # This can't be taken from the cache at the moment because it is used
        # to call _acl_can_be_held_by_user() which needs the approved_group
        # information
        person = self.fas.person_by_username(owner)
        if not person:
            return dict(status=False,
                    message='Specified owner ID %s does not have a Fedora' \
                    ' Account' % owner)

        # Make sure the owner is in the correct group
        try:
            self._acl_can_be_held_by_user('owner', person)
        except AclNotAllowedError, e:
            return dict(status=False, message=str(e))

        # Retrieve the devel Collection so we can use its id later.
        develCollection = model.Collection.query.filter_by(
                name='Fedora', version='devel').one()

        # Create the package
        pkg = model.Package(package, summary, self.approvedStatus.statuscodeid)
        pkgListing = model.PackageListing(person['id'],
                self.approvedStatus.statuscodeid)
        pkgListing.collection = develCollection
        pkgListing.package = pkg

        changedAcls = ()

        for group in ('cvsextras', 'uberpackager'):
            groupListing = model.GroupPackageListing(self.groups[group])
            groupListing.packagelisting = pkgListing
            groupCommitAcl = model.GroupPackageListingAcl('commit',
                    self.approvedStatus.statuscodeid)
            groupCommitAcl.grouppackagelisting = groupListing
            groupBuildAcl = model.GroupPackageListingAcl('build',
                    self.approvedStatus.statuscodeid)
            groupBuildAcl.grouppackagelisting = groupListing
            groupCheckoutAcl = model.GroupPackageListingAcl('checkout',
                    self.approvedStatus.statuscodeid)
            groupCheckoutAcl.grouppackagelisting = groupListing
            changedAcls += (groupCommitAcl, groupBuildAcl, groupCheckoutAcl)
        # pylint: enable-msg=W0201

        # Create a log of changes
        logs = []
        pkgLogMessage = '%s (%s) has added Package %s with summary %s' % (
                identity.current.display_name,
                identity.current.user_name,
                pkg.name,
                pkg.summary)
        logs.append(pkgLogMessage)
        pkgLog = model.PackageLog(
                identity.current.user.id, self.addedStatus.statuscodeid,
                pkgLogMessage)
        pkgLog.package = pkg # pylint: disable-msg=W0201
        pkgLogMessage = '%s (%s) has approved Package %s' % (
                identity.current.display_name,
                identity.current.user_name,
                pkg.name)
        logs.append(pkgLogMessage)
        pkgLog = model.PackageLog(
                identity.current.user.id, self.approvedStatus.statuscodeid,
                pkgLogMessage)
        pkgLog.package = pkg

        pkgLogMessage = '%s (%s) has added a %s %s branch for %s with an' \
                ' owner of %s' % (
                        identity.current.display_name,
                        identity.current.user_name,
                        pkgListing.collection.name,
                        pkgListing.collection.version,
                        pkgListing.package.name,
                        owner)
        logs.append(pkgLogMessage)
        pkgListLog = model.PackageListingLog(
                identity.current.user.id, self.addedStatus.statuscodeid,
                pkgLogMessage
                )
        pkgListLog.listing = pkgListing # pylint: disable-msg=W0201

        pkgLogMessage = '%s (%s) has approved %s in %s %s' % (
                    identity.current.display_name,
                    identity.current.user_name,
                    pkgListing.package.name,
                    pkgListing.collection.name,
                    pkgListing.collection.version)
        logs.append(pkgLogMessage)
        pkgListLog = model.PackageListingLog(
                identity.current.user.id, self.approvedStatus.statuscodeid,
                pkgLogMessage
                )
        pkgListLog.listing = pkgListing

        pkgLogMessage = '%s (%s) has approved Package %s' % (
                identity.current.display_name,
                identity.current.user_name,
                pkg.name)
        logs.append(pkgLogMessage)
        pkgLog = model.PackageLog(
                identity.current.user.id, self.approvedStatus.statuscodeid,
                pkgLogMessage)
        pkgLog.package = pkg

        for changedAcl in changedAcls:
            pkgLogMessage = '%s (%s) has set %s to %s for %s on %s (%s %s)' % (
                    identity.current.display_name,
                    identity.current.user_name,
                    changedAcl.acl,
                    model.StatusTranslation.query.filter_by(
                        statuscodeid=changedAcl.statuscode).one().statusname,

                    self.groups[changedAcl.grouppackagelisting.groupid],
                    pkgListing.package.name,
                    pkgListing.collection.name,
                    pkgListing.collection.version)
            pkgLog = model.GroupPackageListingAclLog(
                    identity.current.user.id,
                    changedAcl.statuscode, pkgLogMessage)
            pkgLog.acl = changedAcl
            logs.append(pkgLogMessage)

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            return dict(status=False,
                    message='Unable to create PackageListing(%s, %s, %s, %s)' %
                        (pkg.id, develCollection.id, person['id'],
                        self.approvedStatus.statuscodeid))

        # Send notification of the new package
        self._send_log_msg('\n'.join(logs),
                '%s was added for %s' % (pkg.name, owner),
                identity.current.user, (pkgListing,))

        # Return the new values
        return dict(status=True, package=pkg, packageListing=pkgListing)

    @expose(allow_json=True)
    @identity.require(identity.not_anonymous())
    def toggle_shouldopen(self, containerId):
        # Make sure the package exists
        pkgName = containerId
        try:
            pkg = model.Package.query.filter_by(name=pkgName).one()
        except InvalidRequestError:
            return dict(status=False,
                    message='Package %s does not exist' % pkgName)

        # Check that the user has rights to set this field
        # cvsadmin, owner on any branch, or approveacls holder
        if not identity.in_any_group('cvsadmin'):
            owners = [x.owner for x in pkg.listings]
            if not (self._user_in_approveacls(pkg) or
                    identity.current.user.id in owners):
                return dict(status=False, message="Permission denied")

        pkg.shouldopen = not pkg.shouldopen
        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Unable to modify PackageListing %s in %s' \
                            % (pkgList.id, pkgList.collection.id))
        return dict(status=True, shouldopen=pkg.shouldopen)

    def _user_in_approveacls(self, pkg):
        for people in [x.people for x in pkg.listings]:
            for person in people:
                if person.userid == identity.current.user.id:
                    for acl in person.acls:
                        if acl.acl == 'approveacls' and acl.status == self.approvedStatus.statuscodeid:
                            return True
        return False

    @expose(allow_json=True)
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.not_anonymous())
    def edit_package(self, package, **changes):
        '''Add a new package to the database.
        '''
        # Check that the tg.identity is allowed to make changes to the package
        if not identity.in_any_group('cvsadmin'):
            return dict(status=False, message='User must be in cvsadmin')

        # Log message for all owners
        pkgLogMsg = None
        # Log message for owners of a branch
        pkgListLogMsg = {}

        # Make sure the package exists
        try:
            pkg = model.Package.query.filter_by(name=package).one()
        except InvalidRequestError:
            return dict(status=False,
                    message='Package %s does not exist' % package)
        # No changes to make
        if not changes:
            return dict(status=True, package=pkg)

        # Change the summary
        if 'summary' in changes:
            pkg.summary = changes['summary']
            logMessage = '%s (%s) set package %s summary to %s' % (
                    identity.current.display_name,
                    identity.current.user_name, package, changes['summary'])
            log = model.PackageLog(identity.current.user.id,
                    self.modifiedStatus.statuscodeid, logMessage)
            log.package = pkg
            pkgLogMsg = logMessage

        # Retrieve the owner for use later
        person = None
        ownerId = None
        if 'owner' in changes:
            # This can't come from the cache ATM as it is used in a call to
            # _acl_can_be_held_by_user() which needs group information.
            person = self.fas.person_by_username(changes['owner'])
            if not person:
                return dict(status=False,
                        message='Specified owner %s does not have a Fedora'
                        ' Account' % changes['owner'])
            # Make sure the owner is in the correct group
            try:
                self._acl_can_be_held_by_user('owner', person)
            except AclNotAllowedError, e:
                return dict(status=False, message=str(e))

            ownerId = person['id']

        if 'collections' in changes:
            # Save a reference to the pkgListings in here
            listings = []

            # Retrieve the id of the initial package owner
            if not ownerId:
                # Retrieve the id for the develCollection
                develCollection = model.Collection.query.filter_by(
                        name='Fedora', version='devel').one()

                develPackage = model.PackageListing.query.filter_by(packageid=pkg.id,
                        collectionid=develCollection.id).one()
                ownerId = develPackage.owner

            # Turn JSON collection data back to python
            collectionData = simplejson.loads(changes['collections'])
            for collectionName in collectionData:
                for version in collectionData[collectionName]:
                    # Check if collection/version exists
                    try:
                        collection = model.Collection.query.filter_by(
                                name=collectionName, version=version).one()
                    except InvalidRequestError:
                        return dict(status=False,
                                message='No collection %s %s' %
                                (collectionName, version))

                    # Create the packageListing if necessary
                    try:
                        pkgListing = model.PackageListing.query.filter_by(
                                collectionid=collection.id,
                                packageid=pkg.id).one()
                    except InvalidRequestError:
                        pkgListing = model.PackageListing(ownerId,
                                self.approvedStatus.statuscodeid)
                        pkgListing.package = pkg
                        pkgListing.collection = collection
                        cvsextrasListing = model.GroupPackageListing(
                                self.groups['cvsextras'])
                        cvsextrasListing.packagelisting = pkgListing
                        cvsextrasCommitAcl = model.GroupPackageListingAcl(
                                'commit', self.approvedStatus.statuscodeid)
                        cvsextrasCommitAcl.grouppackagelisting = \
                                cvsextrasListing
                        cvsextrasBuildAcl = model.GroupPackageListingAcl(
                                'build', self.approvedStatus.statuscodeid)
                        cvsextrasBuildAcl.grouppackagelisting = cvsextrasListing
                        cvsextrasCheckoutAcl = model.GroupPackageListingAcl(
                                'checkout', self.approvedStatus.statuscodeid)
                        cvsextrasCheckoutAcl.grouppackagelisting = \
                                cvsextrasListing

                        logMessage = '%s (%s) added a %s %s branch for %s' % (
                                identity.current.display_name,
                                identity.current.user_name,
                                pkgListing.collection.name,
                                pkgListing.collection.version,
                                pkgListing.package.name)
                        pkgLog = model.PackageListingLog(
                                identity.current.user.id,
                                self.addedStatus.statuscodeid,
                                logMessage
                                )
                        pkgLog.listing = pkgListing
                        pkgListLogMsg[pkgListing] = [logMessage]
                        for changedAcl in (cvsextrasCommitAcl,
                                cvsextrasBuildAcl, cvsextrasCheckoutAcl):
                            pkgLogMessage = '%s (%s) has set %s to %s for' \
                                    ' %s on %s (%s %s)' % (
                                    identity.current.display_name,
                                    identity.current.user_name,
                                    changedAcl.acl,
                                    model.StatusTranslation.query.filter_by(
                                        statuscodeid = changedAcl.statuscode
                                        ).one().statusname,
                                    self.groups[
                                        changedAcl.grouppackagelisting.groupid],
                                    pkgListing.package.name,
                                    pkgListing.collection.name,
                                    pkgListing.collection.version)
                            pkgLog = model.GroupPackageListingAclLog(
                                    identity.current.user.id,
                                    changedAcl.statuscode, pkgLogMessage)
                            pkgLog.acl = changedAcl
                            pkgListLogMsg[pkgListing].append(pkgLogMessage)


                    # Save a reference to all pkgListings
                    listings.append(pkgListing)

        # If ownership, change the owners
        if 'owner' in changes:
            # Already retrieved owner into person
            for pkgList in listings:
                pkgList.owner = person['id']
                logMessage = '%s (%s) changed owner of %s in %s %s to %s' % (
                        identity.current.display_name,
                        identity.current.user_name,
                        pkgList.package.name,
                        pkgList.collection.name, pkgList.collection.version,
                        person['username']
                        )
                pkgLog = model.PackageListingLog(
                        identity.current.user.id,
                        self.ownedStatus.statuscodeid,
                        logMessage
                        )
                pkgLog.listing = pkgList
                try:
                    pkgListLogMsg[pkgList].append(logMessage)
                except KeyError:
                    pkgListLogMsg[pkgList] = [logMessage]
        
        # Change the cclist
        if 'ccList' in changes:
            ccList = simplejson.loads(changes['ccList'])
            for username in ccList:
                # Lookup the list members in fas
                try:
                    person = self.fas.cache[username]
                except KeyError:
                    return dict(status=False,
                            message='New cclist member %s is not in FAS' %
                                    username)
                # Add Acls for them to the packages
                for pkgList in listings:
                    for acl in ('watchbugzilla', 'watchcommits'):
                        personAcl = self._create_or_modify_acl(pkgList,
                                person['id'], acl, self.approvedStatus)
                        logMessage = '%s (%s) approved %s on %s (%s %s)' \
                                ' for %s' % (
                                        identity.current.display_name,
                                        identity.current.user_name,
                                        acl, pkgList.package.name,
                                        pkgList.collection.name,
                                        pkgList.collection.version,
                                        person['username']
                                        )
                        pkgLog = model.PersonPackageListingAclLog(
                                identity.current.user.id,
                                self.approvedStatus.statuscodeid,
                                logMessage
                                )
                        pkgLog.acl = personAcl
                        try:
                            pkgListLogMsg[pkgList].append(logMessage)
                        except KeyError:
                            pkgListLogMsg[pkgList] = [logMessage]

        # Change the comaintainers
        if 'comaintList' in changes:
            comaintList = simplejson.loads(changes['comaintList'])
            for username in comaintList:
                # Lookup the list members in fas
                # Note: this can't come from the cache ATM as it is used in a
                # call to _acl_can_be_held_by_user() which needs group
                # information.
                person = self.fas.person_by_username(username)
                if not person:
                    return dict(status=False,
                            message='New comaintainer %s does not have a' \
                            ' Fedora Account' % username)

                # Make sure the comaintainer is in the correct group
                try:
                    self._acl_can_be_held_by_user('approveacls', person)
                except AclNotAllowedError, e:
                    return dict(status=False, message=str(e))

                # Add Acls for them to the packages
                for pkgList in listings:
                    for acl in ('watchbugzilla', 'watchcommits', 'commit',
                            'build', 'approveacls'):
                        personAcl = self._create_or_modify_acl(pkgList,
                                person['id'], acl, self.approvedStatus)

                        # Make sure a log is created in the db as well.
                        logMessage = u'%s (%s) approved %s on %s (%s %s)' \
                                ' for %s' % (
                                        identity.current.display_name,
                                        identity.current.user_name, acl,
                                        pkgList.package.name,
                                        pkgList.collection.name,
                                        pkgList.collection.version,
                                        person['username'])
                        pkgLog = model.PersonPackageListingAclLog(
                                identity.current.user.id,
                                self.approvedStatus.statuscodeid,
                                logMessage
                                )
                        pkgLog.acl = personAcl
                        try:
                            pkgListLogMsg[pkgList].append(logMessage)
                        except KeyError:
                            pkgListLogMsg[pkgList] = [logMessage]

        if 'groups' in changes:
            # Change whether the group can commit to cvs.
            groupList = simplejson.loads(changes['groups'])
            for group in groupList:
                # We don't let every group commit
                try:
                    groupId = self.groups[group]
                except KeyError:
                    return dict(status=False,
                            message='Group %s is not allowed to commit' % group)

                for pkgList in listings:
                    if groupList[group] == True:
                        status = self.approvedStatus
                    else:
                        status = self.deniedStatus

                    groupAcl = self._create_or_modify_group_acl(pkgList,
                            groupId, 'commit', status)

                    # Make sure a log is created in the db as well.
                    logMessage = u'%s (%s) %s %s for commit access on %s' \
                            ' (%s %s)' % (
                                    identity.current.display_name,
                                    identity.current.user_name,
                                    status.statusname,
                                    group,
                                    pkgList.package.name,
                                    pkgList.collection.name,
                                    pkgList.collection.version)
                    pkgLog = model.GroupPackageListingAclLog(
                            identity.current.user.id,
                            status.statuscodeid,
                            logMessage
                            )
                    pkgLog.acl = groupAcl
                    try:
                        pkgListLogMsg[pkgList].append(logMessage)
                    except KeyError:
                        pkgListLogMsg[pkgList] = [logMessage]

        try:
            session.flush()
        except sqlalchemy.exceptions.SQLError, e:
            # An error was generated
            return dict(status=False,
                    message='Unable to modify PackageListing %s in %s' \
                            % (pkgList.id, pkgList.collection.id))

        # Send a log to people interested in this package as well
        if pkgLogMsg:
            self._send_log_msg(pkgLogMsg, '%s summary updated by %s' % (
                pkg.name, identity.current.user_name),
                identity.current.user, pkg.listings)
        for pkgListing in pkgListLogMsg.keys():
            self._send_log_msg('\n'.join(pkgListLogMsg[pkgListing]),
                    '%s (%s, %s) updated by %s' % (pkg.name,
                        pkgListing.collection.name,
                        pkgListing.collection.version,
                        identity.current.user_name),
                    identity.current.user, (pkgListing,))
        return dict(status=True)
