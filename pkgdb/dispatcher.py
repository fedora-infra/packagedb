# -*- coding: utf-8 -*-
#
# Copyright © 2007-2009  Red Hat, Inc.
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

#
# PyLint Explanations
#

# :E1101: SQLAlchemy monkey patches the ORM Mappers so we have to disable this
#   check whenever we use a db mapped class.

import xmlrpclib

from sqlalchemy import and_
from sqlalchemy.exceptions import InvalidRequestError, SQLError
from sqlalchemy.orm import eagerload, lazyload

from turbogears import controllers, expose, identity, config, flash
from turbogears.database import session

import simplejson

from pkgdb.model import StatusTranslation, PackageAclStatus, \
        GroupPackageListing, GroupPackageListingAcl, PersonPackageListing, \
        PersonPackageListingAcl, PackageListing, PackageListingLog, Package, \
        Collection, PersonPackageListingAclLog, GroupPackageListingAclLog, \
        PackageLog, Branch

from pkgdb import _
from pkgdb.notifier import EventLogger
from pkgdb.utils import fas, bugzilla, admin_grp, pkger_grp, LOG, STATUS

from fedora.tg.util import tg_url

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
    groups = {101197: 'cvsadmin',
              107427: 'provenpackager',
              'cvsadmin': 101197,
              'provenpackager': 107427}
    groupnames = (admin_grp, 'provenpackager')

    # Groups that a person must be in to own or co-maintain a package
    owner_memberships = (admin_grp, pkger_grp, 'provenpackager')

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

        # pylint: disable-msg=E1101
        # Possible statuses for acls:
        acl_status = PackageAclStatus.query.options(eagerload('locale'))
        # pylint: enable-msg=E1101
        self.acl_status_translations = ['']
        # Create a mapping from status name => statuscode
        for status in acl_status:
            ### FIXME: At some point, we have to pull other translations out,
            # not just C
            if status.locale['C'].statusname != 'Obsolete':
                self.acl_status_translations.append(
                        status.locale['C'].statusname)

    def _send_log_msg(self, msg, subject, author, listings, acls=None,
            other_email=None):
        '''Send a log message to interested parties.

        This takes a message and determines who to send it to.

        :arg msg: The log message to send
        :arg subject: Subject or summary for the message
        :arg author: Author of the change
        :arg listings: Package Listings affected by the change
        :kwarg acls: If specified, people on these acls will be notified.
            Defaults to the people in the approveacls group
        :kwarg other_email: Other email addresses to send notification to
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
        if other_email:
            for email in other_email:
                recipients[email] = ''
        # Get the owners for this package
        for pkg_listing in listings:
            if pkg_listing.owner != 'orphan':
                try:
                    owner = fas.cache[pkg_listing.owner]
                except KeyError:
                    owner = {}
                else:
                    recipients[owner['email']] = ''

            # pylint: disable-msg=E1101
            # Get the co-maintainers
            acl_users = PersonPackageListingAcl.query.options(
                    eagerload('status.locale')).filter(and_(
                    PersonPackageListingAcl.c.personpackagelistingid ==
                    PersonPackageListing.c.id,
                    PersonPackageListing.c.packagelistingid == pkg_listing.id,
                    PersonPackageListingAcl.c.acl.in_(acls)))
            # pylint: enable-msg=E1101

            for acl in acl_users:
                if acl.status.locale['C'].statusname == 'Approved':
                    try:
                        person = fas.cache[acl.personpackagelisting.username]
                    except KeyError:
                        person = {}
                    else:
                        recipients[person['email']] = ''

        # Append a link to the package to the message
        msg = _('%(msg)s\n\nTo make changes to this package see:\n'
                '  %(url)s\n') % {'msg': msg,
                        'url': config.get('base_url_filter.base_url') +
                        tg_url('/packages/name/%s' % listings[0].package.name)}

        # Send the log
        self.eventLogger.send_msg(msg, subject, recipients.keys())

    def _user_can_set_acls(self, ident, pkg):
        '''Check that the current user can set acls.

        This method will return one of these values::

            'admin', 'owner', 'comaintainer', False

        depending on why the user is granted access.  You can therefore use the
        value for finer grained access to some resources.

        :arg ident: identity instance from this request
        :arg pkg: packagelisting to find the user's permissions on
        '''
        # Make sure the current tg user has permission to set acls
        # If the user is in the admin group they can
        if ident.in_group(admin_grp):
            return 'admin'
        # The owner can
        if identity.current.user_name == pkg.owner:
            return 'owner'
        # Wasn't the owner.  See if they have been granted permission
        # explicitly
        for person in pkg.people:
            if person.username == identity.current.user_name:
                # Check each acl that this person has on the package.
                for acl in person.acls:
                    if (acl.acl == 'approveacls' and acl.statuscode
                            == STATUS['Approved'].statuscodeid):
                        return 'comaintainer'
                break
        return False

    def _acl_can_be_held_by_user(self, acl, user=None):
        '''Return true if the user is allowed to hold the specified acl.

        :arg acl: The acl to verify
        :kwarg user: The user to check.  Either a (user, group) tuple from FAS
            or None.  If None, the current identity will be used.
        '''
        if not user:
            user = identity.current.user
        # watchbugzilla and owner needs a valid bugzilla address
        if acl in ('watchbugzilla', 'owner'):
            if not 'bugzilla_email' in user:
                # identity doesn't come with bugzilla_email, get it from the
                # cache
                user.bugzilla_email = fas.cache[user.username]['bugzilla_email']
            try:
                bugzilla.getuser(user.bugzilla_email)
            except xmlrpclib.Fault, e:
                if e.faultCode == 51:
                    # No such user
                    raise AclNotAllowedError(_('Email address'
                            ' %(bugzilla_email)s'
                            ' is not a valid bugzilla email address.  Either'
                            ' make a bugzilla account with that email address'
                            ' or change your email address in the Fedora'
                            ' Account System'
                            ' https://admin.fedoraproject.org/accounts/ to a'
                            ' valid bugzilla email address and try again.')
                            % user)
                raise

        # Anyone can hold watchcommits and watchbugzilla
        if acl in ('watchbugzilla', 'watchcommits'):
            return True

        if acl == 'owner':
            if user:
                if user['id'] <= MAXSYSTEMUID:
                    # Any pseudo user can be the package owner
                    return True
                elif [group for group in user['approved_memberships']
                        if group['name'] in self.owner_memberships]:
                    # If the user is in a knwon group they are allowed
                    return True
                raise AclNotAllowedError(_('%(user)s must be in one of these'
                        ' groups: %(groups)s to own a package') %
                        {'user': user['username'],
                            'groups': self.owner_memberships})
            # Anyone in a known group can potentially own the package
            elif identity.in_any_group(*self.owner_memberships):
                return True
            raise AclNotAllowedError(_('%(user)s must be in one of these'
                    ' groups: %(groups)s to own a package') %
                    {'user': identity.current.user_name,
                        'groups': self.owner_memberships})

        # For any other acl, check whether the person is in an allowed group
        if user:
            # If the person isn't in a known group raise an error
            if [group for group in user['approved_memberships']
                    if group['name'] in self.owner_memberships]:
                return True
            raise AclNotAllowedError(_('%(user)s must be in one of these'
                ' groups: %(groups)s to hold the %(acl)s acl') % {
                    'user': user['username'], 'groups': self.owner_memberships,
                    'acl': acl})
        elif identity.in_any_group(*self.owner_memberships):
            return True
        raise AclNotAllowedError(_('%(user)s must be in one of these'
            ' groups: %(groups)s to hold the %(acl)s acl') % {
                'user': identity.current.user_name,
                'groups': self.owner_memberships, 'acl': acl})

    def _create_or_modify_acl(self, pkg_listing, person_name, new_acl, status):
        '''Create or modify an acl.

        Set an acl for a user.  This takes a packageListing and makes sure
        there's an ACL for them with the given status.  It will create a new
        ACL or modify an existing one depending on what's in the db already.

        :arg pkg_listing: PackageListing on which to set the ACL.
        :arg person_name: PersonName to set the ACL for.
        :arg new_acl: ACL name to set.
        :arg status: Status DB Object we're setting the ACL to.
        '''
        # watchbugzilla and watchcommits are autocommit
        if new_acl in ('watchbugzilla', 'watchcommits') and status == STATUS['Awaiting Review']:
            status = STATUS['Approved']

        change_person = pkg_listing.people2.get(person_name, None)
        if not change_person:
            # Person has no ACLs on this Package yet.  Create a record
            change_person = PersonPackageListing(person_name)
            pkg_listing.people.append(change_person)
            person_acl = PersonPackageListingAcl(new_acl,
                    status.statuscodeid)
            change_person.acls.append(person_acl) # pylint: disable-msg=E1101
        else:
            # Look for an acl for the person
            person_acl = None
            for acl in change_person.acls:
                if acl.acl == new_acl:
                    # Found the acl, change its status
                    person_acl = acl
                    acl.statuscode = status.statuscodeid
                    break
            if not person_acl:
                # Acl was not found.  Create one.
                person_acl = PersonPackageListingAcl(new_acl,
                        status.statuscodeid)
                change_person.acls.append(person_acl)

            # For now, we specialcase the build acl to reflect the commit
            # this is because we need to remove notifications and UI that
            # depend on any acl being set and for now, the commit acl is being
            # used for build and push
            if new_acl == 'commit':
                self._create_or_modify_acl(pkg_listing, person_name, 'build',
                        status)
        person_acl.status = session.query(PackageAclStatus).filter(
                PackageAclStatus.statuscodeid==status.statuscodeid).one()

        return person_acl

    def _create_or_modify_group_acl(self, pkg_listing, group_name, new_acl,
            status):
        '''Create or modify a group acl.

        Set an acl for a group.  This takes a packageListing and makes sure
        there's an ACL for it with the given status.  It will create a new
        ACL or modify an existing one depending on what's in the db already.

        :arg pkg_listing: PackageListing on which to set the ACL.
        :arg group_name: GroupName to set the ACL for.
        :arg new_acl: ACL name to set.
        :arg status: Status DB Objcet we're setting the ACL to.
        '''
        # Create the ACL
        change_group = None
        for group in pkg_listing.groups:
            # Check for the group who's acl we're setting
            if group.groupname == group_name:
                change_group = group
                break

        if not change_group:
            # Group has no ACLs on this Package yet.  Create a record
            change_group = GroupPackageListing(group_name)
            pkg_listing.groups.append(change_group)
            group_acl = GroupPackageListingAcl(new_acl,
                    status.statuscodeid)
            change_group.acls.append(group_acl) # pylint: disable-msg=E1101
        else:
            # Look for an acl for the group
            group_acl = None
            for acl in change_group.acls:
                if acl.acl == new_acl:
                    # Found the acl, change its status
                    group_acl = acl
                    acl.statuscode = status.statuscodeid
                    break
            if not group_acl:
                # Acl was not found.  Create one.
                group_acl = GroupPackageListingAcl(new_acl,
                        status.statuscodeid)
                change_group.acls.append(group_acl)

        # For now, we specialcase the build acl to reflect the commit
        # this is because we need to remove notifications and UI that
        # depend on any acl being set adn for now, the commit acl is being
        # used for build and push
        if new_acl == 'commit':
            self._create_or_modify_group_acl(pkg_listing, group_name, 'build',
                    status)
        return group_acl

    def _most_eligible_comaintainer(self, pkg_listing):
        '''Find the comaintainer that's been on the package the longest.

        This method returns the name of the comaintainer that requested
        approveacls the longest time ago. This gives a good approximation
        of who has been comaintaining the package the longest.

        :arg pkg_listing: Package listing to retrieve the comaintainer.
        :returns: User name of the person who has held approveacls the
            longest. If no on is found, return 'orphan'.
        :raises InvalidRequestError: if there's problem retrieving
            information from the database.
        '''
        #get acls to comparison
        acls = PersonPackageListingAcl.query.filter(and_(
                   PersonPackageListingAcl.c.personpackagelistingid
                       == PersonPackageListing.c.id,
                   PersonPackageListing.c.packagelistingid
                       == PackageListing.c.id,
                   PackageListing.c.id == pkg_listing.id,
                   PersonPackageListingAcl.c.statuscode 
                       == STATUS['Approved'].statuscodeid,
                   PersonPackageListingAcl.c.acl == 'approveacls')
                   ).all()
        username = ''
        #get acl with min personpackagelistingacl.id
        if len(acls) > 0:
            search_acl = acls[0]
            for acl in acls:
                if search_acl.id > acl.id:
                    search_acl = acl
            username = search_acl.personpackagelisting.username
        else:
            username = 'orphan'

        pkg_listing.owner = username

        return username

    def _set_bugzilla_owner(self, user_email, pkg_name, collectn,
            collectn_version, bzComment):
        '''Change the package owner

         :arg user_email: User email address to change the owner
         :arg pkg_name: Name of the package to change the owner
         :arg collectn: Collection name of the package
         :arg collectn_version: Collection version
         :arg bzComment: the comment of changes
        '''
        bzMail = '%s' % user_email
        bzQuery = {}
        bzQuery['product'] = collectn
        bzQuery['component'] = pkg_name
        bzQuery['bug_status'] = ['NEW', 'ASSIGNED', 'ON_DEV', 'ON_QA',
                'MODIFIED', 'POST', 'FAILS_QA', 'PASSES_QA',
                'RELEASE_PENDING']
        bzQuery['version'] = collectn_version
        if bzQuery['version'] == 'devel':
            bzQuery['version'] = 'rawhide'
        queryResults = bugzilla.query(bzQuery)
        for bug in queryResults:
            if config.get('bugzilla.enable_modification', False):
                bug.setassignee(assigned_to=bzMail, comment=bzComment)
            else:
                LOG.debug(_('Would have reassigned bug #%(bug_num)s'
                ' from %(former)s to %(current)s') % {
                    'bug_num': bug.bug_id, 'former': bug.assigned_to,
                    'current': bzMail})

    @expose(allow_json=True)
    def index(self):
        '''
        Return a list of methods that can be called on this dispatcher.
        '''
        return dict(methods=self.methods)

    @expose(allow_json=True)
    @identity.require(identity.not_anonymous())
    def toggle_owner(self, pkg_listing_id):
        '''Orphan package or set the owner to the logged in user.

        :arg pkg_listing_id: The packagelisting to change ownership for.
        '''
        # Check that the pkg exists
        try:
            # pylint: disable-msg=E1101
            pkg = PackageListing.query.filter_by(id=pkg_listing_id).one()
        except InvalidRequestError:
            return dict(status=False, message=_('No such package %(pkg_id)s') %
                    {'pkg_id': pkg_listing_id})
        approved = self._user_can_set_acls(identity, pkg)

        if pkg.statuscode == STATUS['Deprecated'].statuscodeid:
            # Retired packages must be brought out of retirement first
            return dict(status=False, message=_('This package is retired.  It'
                ' must be unretired first'))

        bzComment = 'This package has changed ownership in the Fedora'\
                        ' Package Database.  Reassigning to the new owner'\
                        ' of this component.'

        if pkg.owner == 'orphan':
            # Check that the tg.identity is allowed to set themselves as owner
            try:
                self._acl_can_be_held_by_user('owner')
            except AclNotAllowedError, e:
                return dict(status=False, message=str(e))

            # Take ownership
            pkg.owner = identity.current.user_name
            pkg.statuscode = STATUS['Approved'].statuscodeid
            log_msg = 'Package %s in %s %s is now owned by %s' % (
                    pkg.package.name, pkg.collection.name,
                    pkg.collection.version, pkg.owner)
            status = STATUS['Owned']
            self._set_bugzilla_owner(identity.current.user.email, 
                pkg.package.name, pkg.collection.name,
                pkg.collection.version, bzComment)
        elif approved in ('admin', 'owner'):
            try:
                owner_name = self._most_eligible_comaintainer(pkg)
            except InvalidRequestError, e:
                return dict(status=False, 
                    message=_('Acls error: %(err)s') % {'err': e})
            if owner_name != 'orphan':
                pkg.statuscode = STATUS['Approved'].statuscodeid
                log_msg = 'Package %s in %s %s is now owned by %s' % (
                    pkg.package.name, pkg.collection.name,
                    pkg.collection.version, owner_name)
                status = STATUS['Owned']
                try:
                    person = fas.cache[owner_name]
                    email = person['bugzilla_email']
                except KeyError:
                    log_msg += ' Specified owner %s does not have a Fedora'\
                               ' Account' % owner_name
                    email = identity.current.user.email
                self._set_bugzilla_owner(email, pkg.package.name,
                    pkg.collection.name, pkg.collection.version, bzComment)
            else:
                # Release ownership
                pkg.statuscode = STATUS['Orphaned'].statuscodeid
                log_msg = 'Package %s in %s %s was orphaned by %s' % (
                        pkg.package.name, pkg.collection.name,
                        pkg.collection.version, identity.current.user_name)
                status = STATUS['Orphaned']
        else:
            return dict(status=False, message=_('Package %(pkg)s not available'
                ' for taking') % {'pkg': pkg.package.name})

        # Make sure a log is created in the db as well.
        log = PackageListingLog(identity.current.user_name,
                status.statuscodeid, log_msg, None, pkg_listing_id)
        log.packagelistingid = pkg.id

        try:
            session.flush()
        except SQLError, e:
            # An error was generated
            return dict(status=False, message=_('Not able to change owner'
                ' information for %(pkg)s') % {'pkg': pkg.package.name})

        # Send a log to people interested in this package as well
        self._send_log_msg(log_msg, _('%(pkg)s ownership updated') % {
            'pkg': pkg.package.name}, identity.current.user, (pkg,),
            ('approveacls', 'watchbugzilla', 'watchcommits', 'build', 'commit'))

        return dict(status=True, owner=pkg.owner,
                aclStatusFields=self.acl_status_translations)

    @expose(allow_json=True)
    @identity.require(identity.not_anonymous())
    def toggle_retirement(self, pkg_listing_id):
        '''Retire/Unretire package

        Rules for retiring:
        - owned packages - can be retired by: maintainers and cvsadmin
        - orphaned packages - can be retired by: anyone
        Unretiring can only be done by cvsadmin

        :arg pkg_listing_id: The PackageListing to be (un)retired.
        '''
        # Check that the pkg exists
        try:
            # pylint: disable-msg=E1101
            pkg = PackageListing.query.filter_by(id=pkg_listing_id).one()
        except InvalidRequestError:
            return dict(status=False, message=_('No such package %(pkg)s') %
                    {'pkg': pkg_listing_id})
        approved = self._user_can_set_acls(identity, pkg)

        if (pkg.statuscode != STATUS['Deprecated'].statuscodeid and (
            pkg.statuscode == STATUS['Orphaned'].statuscodeid or
            approved in ('admin', 'owner'))):
            # Retire package
            if pkg.owner != 'orphan':
                # let toggle_owner handle bugzilla and other stuff
                self.toggle_owner(pkg_listing_id)
            pkg.statuscode = STATUS['Deprecated'].statuscodeid
            log_msg = 'Package %s in %s %s has been retired by %s' % (
                pkg.package.name, pkg.collection.name,
                pkg.collection.version, identity.current.user_name)
            status = STATUS['Deprecated']
            retirement = 'Retired'
        elif (pkg.statuscode == STATUS['Deprecated'].statuscodeid and
              approved == 'admin'):
            # Unretire package
            pkg.statuscode = STATUS['Orphaned'].statuscodeid
            log_msg = 'Package %s in %s %s has been unretired by %s and' \
                    ' is now orphan.' % (
                            pkg.package.name, pkg.collection.name,
                            pkg.collection.version, identity.current.user_name)
            status = STATUS['Orphaned']
            retirement = 'Unretired'
        else:
            return dict(status=False, message=
                    _('The (un)retiring of package %(pkg)s could not be' \
                            ' completed. Check your permissions.') % {
                                'pkg': pkg.package.name})
        # Retired and just-unretired packages are orphan
        pkg.owner = 'orphan'
        # Make a log in the db.
        log = PackageListingLog(identity.current.user_name,
                status.statuscodeid, log_msg, None, pkg_listing_id)
        log.packagelistingid = pkg.id

        try:
            session.flush()
        except SQLError, e:
            # An error was generated
            return dict(status=False,
                message=_('Unable to (un)retire package %(pkg)s') % {
                    'pkg': pkg_listing_id})
        # Send a log to people interested in the package
        self._send_log_msg(log_msg, _('%(pkg)s (un)retirement') % {
            'pkg': pkg.package.name}, identity.current.user, (pkg,),
            ('approveacls', 'watchbugzilla', 'watchcommits', 'build', 'commit'))
        return dict(status=True, retirement=retirement,
               aclStatusFields=self.acl_status_translations)

    @expose(allow_json=True)
    # Check that the requestor is in a group that could potentially set ACLs.
    @identity.require(identity.not_anonymous())
    def set_acl_status(self, pkgid, person_name, new_acl, statusname):
        '''Set the acl on a package to a particular status.

        :arg pkgid: packageListing.id
        :arg person_name: username of the person to make the request for
        :arg new_acl: The acl we're changing the status of
        :arg statusname: Status to change the acl to
        '''
        ### FIXME: Changing Obsolete into "" sounds like it should be
        # Pushed out to the view (template) instead of being handled in the
        # controller.

        # We are making Obsolete into "" for our interface.  Need to reverse
        # that here.
        if not statusname or not statusname.strip():
            statusname = 'Obsolete'
        try:
            # pylint: disable-msg=E1101
            status = StatusTranslation.query.filter_by(
                    statusname=statusname).one()
        except InvalidRequestError:
            return dict(status=False, message=_('Invalid Status: %(status)s')
                    % {'status': statusname})

        # Change strings into numbers because we do some comparisons later on
        pkgid = int(pkgid)

        # Make sure the package listing exists
        try:
            # pylint: disable-msg=E1101
            pkg = PackageListing.query.filter_by(id=pkgid).one()
        except InvalidRequestError:
            return dict(status=False,
                    message=_('PackageListing %(pkg)s does not exist') % {
                        'pkg': pkgid})

        # Make sure the person we're setting the acl for exists
        try:
            user = fas.cache[person_name]
        except KeyError:
            return dict(status=False, message=_('No such user %(username),'
                ' for package %(pkg)s in %(collection)s %(version)s') % {
                    'username': person_name, 'pkg': pkg.package.name,
                    'collection': pkg.collection.name,
                    'version': pkg.collection.version})

        # Check that the current user is allowed to change acl statuses
        approved = self._user_can_set_acls(identity, pkg)
        if not approved:
            return dict(status=False, message=
                    _('%(user)s is not allowed to approve Package ACLs') % {
                        'user': identity.current.user_name})

        #
        # Make sure the person is allowed on this acl
        #

        # Always allowed to remove an acl
        if statusname not in ('Denied', 'Obsolete'):
            try:
                self._acl_can_be_held_by_user(new_acl, user)
            except AclNotAllowedError, e:
                return dict(status=False, message=str(e))

        person_acl = self._create_or_modify_acl(pkg, person_name, new_acl, status)

        # Make sure a log is created in the db as well.
        log_msg = u'%s has set the %s acl on %s (%s %s) to %s for %s' % (
                    identity.current.user_name, new_acl, pkg.package.name,
                    pkg.collection.name, pkg.collection.version, statusname,
                    user['username'])
        log = PersonPackageListingAclLog(identity.current.user_name,
                status.statuscodeid, log_msg)
        log.acl = person_acl # pylint: disable-msg=W0201

        try:
            session.flush()
        except SQLError, e:
            # An error was generated
            return dict(status=False, message=_('Not able to create acl'
                ' %(acl)s on %(pkg)s with status %(status)s') % {
                    'acl': new_acl, 'pkg': pkgid, 'status': statusname})
        # Send a log to people interested in this package as well
        self._send_log_msg(log_msg, _('%(pkg)s had acl change status') % {
            'pkg': pkg.package.name}, identity.current.user, (pkg,),
            other_email=(user['email'],))

        return dict(status=True)

    @expose(allow_json=True)
    # Check that the requestor is in a group that could potentially set ACLs.
    @identity.require(identity.not_anonymous())
    def toggle_groupacl_status(self, container_id):
        '''Set the groupacl to determine whether the group can commit.

        WARNING: Do not use changeAcl.status in this method.  There is a high
        chance that it will be out of sync with the current statuscode after
        the status is set.  Updating changeAcl.status at the same time as we
        update changeAcl.statuscodeid makes this method take 10-11s instead of
        <1s.

        If you cannot live without changeAcl.status, try flushing the session
        after changeAcl.statuscodeid is set and see if that can automatically
        refresh the status without the performance hit.

        :arg container_id: a string of three ids needed for this function
            separated by colons (':').  pkg_listing_id, group_name, and the
            new acl name.
        '''
        # Pull apart the identifier
        pkg_listing_id, group_name, acl_name = container_id.split(':')
        pkg_listing_id = int(pkg_listing_id)

        # Make sure the package listing exists
        try:
            # pylint: disable-msg=E1101
            pkg = PackageListing.query.filter_by(id=pkg_listing_id).one()
        except InvalidRequestError:
            return dict(status=False, message=_('Package Listing with id:'
                ' %(pkg)s does not exist') % {'pkg': pkg_listing_id})

        if pkg.statuscode == STATUS['Deprecated'].statuscodeid:
            # Retired packages must be brought out of retirement first
            return dict(status=False, message=_('This package is retired.  It'
                ' must be unretired first'))

        # Only admins can change whether the provenpackager group can
        # commit.
        if not identity.in_group(admin_grp):
            return dict(status=False, message=_('%(user)s is not allowed to'
                ' approve Package ACLs for %(pkg)s (%(collctn)s %(ver)s)') % {
                    'user': identity.current.user_name,
                    'pkg': pkg.package.name, 'collctn': pkg.collection.name,
                    'ver': pkg.collection.version})

        # Check that the group is one that we allow access to packages
        if group_name not in self.groups:
            return dict(status=False, message=_('%(group)s is not a group'
                ' that can commit to packages') % {'group': group_name})

        #
        # Set the new acl status
        #

        acl_status = 'Approved'
        # Determine if the group already has an acl
        try:
            # pylint: disable-msg=E1101
            acl = GroupPackageListingAcl.query.options(
                    eagerload('status.locale')).filter(and_(
                    GroupPackageListingAcl.c.grouppackagelistingid \
                            == GroupPackageListing.c.id,
                    GroupPackageListing.c.groupname == group_name,
                    GroupPackageListingAcl.c.acl == acl_name,
                    GroupPackageListing.c.packagelistingid == pkg_listing_id
                )).one()
        except InvalidRequestError:
            pass
        else:
            if acl.status.locale['C'].statusname == 'Approved':
                acl_status = 'Denied'

        status = STATUS[acl_status]
        # Change the acl
        group_acl = self._create_or_modify_group_acl(pkg, group_name, acl_name,
                status)

        ### WARNING: changeAcl.status is very likely out of sync at this point.
        # See the docstring for an explanation.

        # Make sure a log is created in the db as well.
        log_msg = '%s has set the %s acl on %s (%s %s) to %s for %s' % (
                    identity.current.user_name, acl_name, pkg.package.name,
                    pkg.collection.name, pkg.collection.version, acl_status,
                    self.groups[group_name])
        log = GroupPackageListingAclLog(identity.current.user_name,
                status.statuscodeid, log_msg)
        log.acl = group_acl # pylint: disable-msg=W0201

        try:
            session.flush()
        except SQLError:
            # An error was generated
            return dict(status=False, message=_('Not able to create acl'
                ' %(acl)s on %(pkg)s (%(collctn)s %(ver)s) with status'
                ' %(status)s') % {
                    'acl': acl_name, 'pkg': pkg.package.name,
                    'collctn': pkg.collection.name,
                    'ver': pkg.collection.version, 'status': acl_status})

        # Send a log to people interested in this package as well
        self._send_log_msg(log_msg, _('%(pkg)s had group_acl changed') % {
            'pkg': pkg.package.name}, identity.current.user, (pkg,))

        return dict(status=True, newAclStatus=acl_status)

    @expose(allow_json=True)
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.not_anonymous())
    def toggle_acl_request(self, container_id):
        '''Request an acl or revoke a request.

        :arg container_id: The PackageListing.id and name of the acl to toggle
            the status for separated by a ":"
        '''
        # Make sure package exists
        pkg_listing_id, acl_name = container_id.split(':')
        try:
            # pylint: disable-msg=E1101
            pkg_listing = PackageListing.query.filter_by(
                    id=pkg_listing_id).one()
        except InvalidRequestError:
            return dict(status=False, message=_('No such package listing'
                ' %(pkg)s') % {'pkg': pkg_listing_id})

        # Determine whether we need to set a new acl
        acl_status = 'Awaiting Review'
        # Determine if the user already has an acl
        try:
            # pylint: disable-msg=E1101
            acl = PersonPackageListingAcl.query.options(
                    eagerload('status.locale')).filter(and_(
                    PersonPackageListingAcl.c.personpackagelistingid == \
                            PersonPackageListing.c.id,
                    PersonPackageListing.c.username == \
                            identity.current.user_name,
                    PersonPackageListingAcl.c.acl == acl_name,
                    PersonPackageListing.c.packagelistingid == pkg_listing_id)
                ).one()
        except InvalidRequestError:
            pass
        else:
            if acl.status.locale['C'].statusname != 'Obsolete':
                acl_status = 'Obsolete'

        if acl_status != 'Obsolete':
            # Check that the person is in a correct group to receive the acl
            try:
                self._acl_can_be_held_by_user(acl_name)
            except AclNotAllowedError, e:
                return dict(status=False, message=str(e))
        status = STATUS[acl_status]

        # Assign person to package
        person_acl = self._create_or_modify_acl(pkg_listing,
                identity.current.user_name, acl_name, status)
        acl_status = person_acl.status.translations[0].statusname

        # Make sure a log is created in the db as well.
        if acl_status == 'Awaiting Review':
            acl_action = 'requested'
        else:
            acl_action = 'given up'
        log_msg = '%s has %s the %s acl on %s (%s %s)' % (
                    identity.current.user_name, acl_action, acl_name,
                    pkg_listing.package.name, pkg_listing.collection.name,
                    pkg_listing.collection.version)
        log = PersonPackageListingAclLog(identity.current.user_name,
                person_acl.statuscode, log_msg)
        log.acl = person_acl

        try:
            session.flush()
        except SQLError, e:
            # Probably the acl is mispelled
            return dict(status=False, message=_('Not able to create acl'
                ' %(acl)s for %(user)s on %(pkg)s') % {
                    'acl': acl_name, 'user': identity.current.user_name,
                    'pkg': pkg_listing_id})

        # Send a log to the commits list as well
        self._send_log_msg(log_msg, _('%(pkg)s: %(user)s has %(action)s'
            ' %(acl)s') % {'pkg': pkg_listing.package.name,
                'user': identity.current.user_name, 'action': acl_action,
                'acl': acl_name}, identity.current.user, (pkg_listing,))

        # Return the new value
        return dict(status=True, personName=identity.current.user_name,
                aclStatusFields=self.acl_status_translations,
                aclStatus=acl_status)

    @expose(allow_json=True)
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.not_anonymous())
    def add_package(self, package, owner, summary):
        '''Add a new package to the database.

        :arg package: name of package to add
        :arg owner: username of the owner of the new package
        :arg summary: summary description for the new package
        '''
        # Replace newlines with spaces in the summary
        summary = summary.replace('\n', ' ')
        # Check that the tg.identity is allowed to set an owner
        if not identity.in_any_group(admin_grp):
            return dict(status=False, message=_('User must be in admin_grp'))

        # Make sure the package doesn't already exist
        # pylint: disable-msg=E1101
        pkg = Package.query.filter_by(name=package)
        # pylint: enable-msg=E1101
        if pkg.count():
            return dict(status=False, message=_('Package %(pkg)s already'
                ' exists') % {'pkg': package})

        try:
            person = fas.cache[owner]
        except KeyError:
            return dict(status=False, message=_('Specified owner ID %(owner)s'
                ' does not have a Fedora Account') % {'owner': owner})
        # Make sure the owner is in the correct group
        try:
            self._acl_can_be_held_by_user('owner', person)
        except AclNotAllowedError, e:
            return dict(status=False, message=str(e))

        # Retrieve the devel Collection so we can use its id later.
        # pylint: disable-msg=E1101
        devel_collection = Collection.query.filter_by(
                name='Fedora', version='devel').one()
        # pylint: enable-msg=E1101

        # Create the package
        pkg = Package(package, summary, STATUS['Approved'].statuscodeid)
        pkg_listing = pkg.create_listing(devel_collection, person['username'],
                STATUS['Approved'],
                author_name = identity.current.user_name)
        try:
            session.flush()
        except SQLError, e:
            return dict(status=False, message=_('Unable to create'
                ' PackageListing for %(pkg)s(Fedora devel), %(user)s),'
                ' %(status)s') % { 'pkg': package, 'user': person['username'],
                    'status': STATUS['Approved'].statuscodeid})
        changed_acls = []
        for group in ('provenpackager',):
            changed_acls.append(GroupPackageListingAcl.query.filter(and_(
                    GroupPackageListingAcl.c.grouppackagelistingid
                        == GroupPackageListing.c.id,
                    GroupPackageListing.c.packagelistingid 
                        == pkg_listing.id,
                    GroupPackageListing.c.groupname == group)).all())

        # pylint: enable-msg=W0201

        # Create a log of changes
        logs = []
        pkg_log_msg = '%s has added Package %s with summary %s' % (
                identity.current.user_name,
                pkg.name,
                pkg.summary)
        logs.append(pkg_log_msg)
        pkg_log = PackageLog(
                identity.current.user_name, STATUS['Added'].statuscodeid,
                pkg_log_msg)
        pkg_log.package = pkg # pylint: disable-msg=W0201
        pkg_log_msg = '%s has approved Package %s' % (
                identity.current.user_name,
                pkg.name)
        logs.append(pkg_log_msg)
        pkg_log = PackageLog(
                identity.current.user_name, STATUS['Approved'].statuscodeid,
                pkg_log_msg)
        pkg_log.package = pkg

        pkg_log_msg = '%s has added a %s %s branch for %s with an' \
                ' owner of %s' % (
                        identity.current.user_name,
                        devel_collection.name,
                        devel_collection.version,
                        pkg.name,
                        owner)
        logs.append(pkg_log_msg)

        pkg_log_msg = '%s has approved %s in %s %s' % (
                    identity.current.user_name,
                    pkg.name,
                    devel_collection.name,
                    devel_collection.version)
        logs.append(pkg_log_msg)

        pkg_log_msg = '%s has approved Package %s' % (
                identity.current.user_name,
                pkg.name)
        logs.append(pkg_log_msg)
        pkg_log = PackageLog(
                identity.current.user_name, STATUS['Approved'].statuscodeid,
                pkg_log_msg)
        pkg_log.package = pkg

        for group_acls in changed_acls:
            for change_acl in group_acls:
                pkg_log_msg = '%s has set %s to %s for %s on %s (%s %s)' % (
                    identity.current.user_name,
                    change_acl.acl,
                    # pylint: disable-msg=E1101
                    StatusTranslation.query.filter_by(
                        statuscodeid=change_acl.statuscode).one().statusname,
                    # pylint: enable-msg=E1101

                    self.groups[change_acl.grouppackagelisting.groupname],
                    pkg.name,
                    devel_collection.name,
                    devel_collection.version)
                pkg_log = GroupPackageListingAclLog(
                    identity.current.user_name,
                    change_acl.statuscode, pkg_log_msg)
                pkg_log.acl = change_acl
                logs.append(pkg_log_msg)

        try:
            session.flush()
        except SQLError, e:
            return dict(status=False, message=_('Unable to create'
                ' PackageListing for %(pkg)s(Fedora devel), %(user)s),'
                ' %(status)s') % { 'pkg': pkg.name, 'user': person['username'],
                    'status': STATUS['Approved'].statuscodeid})

        # Send notification of the new package
        self._send_log_msg('\n'.join(logs), _('%(pkg)s was added for %(owner)s')
                % {'pkg': pkg.name, 'owner': owner}, identity.current.user,
                (pkg_listing,))

        # Return the new values
        return dict(status=True, package=pkg, packageListing=pkg_listing)


    @expose(allow_json=True)
    @identity.require(identity.not_anonymous())
    def toggle_shouldopen(self, pkg_name):
        '''Toggle whether the acls for the package should be opened to the
        provenpackager group.

        :arg pkg_name: Name of the package to toggle the shouldopen flag for.
        '''
        # Make sure the package exists
        try:
            # pylint: disable-msg=E1101
            pkg = Package.query.filter_by(name=pkg_name).one()
        except InvalidRequestError:
            return dict(status=False, message=_('Package %(pkg)s does not'
                ' exist') % {'pkg': pkg_name})

        # Check that the user has rights to set this field
        # admin_grp, owner on any branch, or approveacls holder
        if not identity.in_any_group(admin_grp):
            owners = [x.owner for x in pkg.listings]
            if not (self._user_in_approveacls(pkg) or
                    identity.current.user_name in owners):
                return dict(status=False, message=_('Permission denied'))

        pkg.shouldopen = not pkg.shouldopen
        try:
            session.flush()
        except SQLError:
            # An error was generated
            return dict(status=False, message=_('Unable to set shouldopen on'
                ' Package %(pkg)s') % {'pkg': pkg_name})

        return dict(status=True, shouldopen=pkg.shouldopen)

    def _user_in_approveacls(self, pkg):
        '''Check that the current user is listed in approveacls.

        :arg pkg: Package object on which we should be checking
        :returns: True if the person is in approveacls, False otherwise.
        '''
        people_lists = (listing.people for listing in pkg.listings)
        while True:
            try:
                # Each iteration, retrieve a set of people from the list
                people = people_lists.next()
                # Retrieve all the lists of acls for the current user for each
                # PackageListing
                acl_lists = (p.acls for p in people
                        if p.username == identity.current.user_name)
                # For each list of acls...
                for acls in acl_lists:
                    # Check each acl
                    for acl in acls:
                        if acl.acl == 'approveacls' and acl.statuscode \
                                == STATUS['Approved'].statuscodeid:
                            return True
            except StopIteration:
                # Exhausted the list, approveaclswas not found
                return False

    @expose(allow_json=True)
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.not_anonymous())
    def edit_package(self, package, **changes):
        '''Add a new package to the database.

        :arg package: name of the package to edit
        :arg changes: dict of changes to make to this package
        '''
        # Check that the tg.identity is allowed to make changes to the package
        if not identity.in_any_group(admin_grp):
            return dict(status=False, message=_('User must be in admin_grp'))

        # Log message for all owners
        pkg_log_msg = None
        # Log message for owners of a branch
        pkg_list_log_msgs = {}

        # Make sure the package exists
        try:
            # pylint: disable-msg=E1101
            pkg = Package.query.filter_by(name=package).one()
        except InvalidRequestError:
            return dict(status=False, message=_('Package %(pkg)s does not'
                ' exist') % { 'pkg': package})
        # No changes to make
        if not changes:
            return dict(status=True, package=pkg)

        # Change the summary
        if 'summary' in changes:
            pkg.summary = changes['summary'].replace('\n', ' ')
            log_msg = '%s set package %s summary to %s' % (
                    identity.current.user_name, package, changes['summary'])
            log = PackageLog(identity.current.user_name,
                    STATUS['Modified'].statuscodeid, log_msg)
            log.package = pkg
            pkg_log_msg = log_msg

        # Retrieve the owner for use later
        person = None
        owner_name = None
        if 'owner' in changes:
            try:
                person = fas.cache[changes['owner']]
            except KeyError:
                return dict(status=False, message=_('Specified owner %(owner)s'
                    ' does not have a Fedora Account') % {
                        'owner': changes['owner']})
            # Make sure the owner is in the correct group
            try:
                self._acl_can_be_held_by_user('owner', person)
            except AclNotAllowedError, e:
                return dict(status=False, message=str(e))

            owner_name = person['username']

        if 'collections' in changes:
            # Save a reference to the pkg_listings in here
            listings = []

            # Retrieve the id of the initial package owner
            if not owner_name:
                # pylint: disable-msg=E1101
                # Retrieve the id for the devel_collection
                devel_collection = Collection.query.filter_by(
                        name='Fedora', version='devel').one()

                devel_pkg = PackageListing.query.filter_by(packageid=pkg.id,
                        collectionid=devel_collection.id).one()
                # pylint: enable-msg=E1101
                owner_name = devel_pkg.owner

            collection_data = changes['collections']
            if not isinstance(collection_data,(tuple,list)):
                collection_data = [collection_data]
            for collection_name in collection_data:
                # Check if collection/version exists
                try:
                    # pylint: disable-msg=E1101
                    collection = Collection.by_simple_name(
                            collection_name)
                except InvalidRequestError:
                    return dict(status=False, message=_('No collection'
                        ' %(collctn)s') % {'collctn': collection_name})

                # Create the packageListing if necessary
                try:
                    # pylint: disable-msg=E1101
                    pkg_listing = PackageListing.query.filter_by(
                            collectionid=collection.id,
                            packageid=pkg.id).one()
                except InvalidRequestError:
                    if owner_name == 'orphan':
                        status = STATUS['Orphaned']
                    else:
                        status = STATUS['Approved']
                    pkg_listing = pkg.create_listing(collection,
                            owner_name,
                            status,
                            author_name = identity.current.user_name)
                    try:
                        session.flush()
                    except SQLError, e:
                        return dict(status=False, message=_('Unable to create'
                            ' PackageListing for %(pkg)s(Fedora devel),'
                            ' %(user)s), %(status)s') % {
                                'pkg': package, 'user': person['username'],
                                'status': status})
                    changed_acls = []
                    for group in ('provenpackager',):
                        changed_acls.append(GroupPackageListingAcl.query.filter(
                            and_(
                            GroupPackageListingAcl.c.grouppackagelistingid
                                == GroupPackageListing.c.id,
                            GroupPackageListing.c.packagelistingid
                                == pkg_listing.id,
                            GroupPackageListing.c.groupname
                                == group)).all())
                    log_msg = '%s added a %s %s branch for %s' % (
                            identity.current.user_name,
                            collection.name,
                            collection.version,
                            pkg.name)
                    pkg_list_log_msgs[pkg_listing] = [log_msg]
                    for group_acls in changed_acls:
                        for change_acl in group_acls:
                            pkg_listing_log_msg = '%s has set %s to %s' \
                                ' for %s on %s (%s %s)' % (
                                identity.current.user_name,
                                change_acl.acl,
                                # pylint: disable-msg=E1101
                                StatusTranslation.query.filter_by(
                                    statuscodeid = change_acl.statuscode
                                    ).one().statusname,
                                # pylint: enable-msg=E1101
                                self.groups[
                                    change_acl.grouppackagelisting.groupname],
                                pkg.name,
                                collection.name,
                                collection.version)
                            pkg_log = GroupPackageListingAclLog(
                                identity.current.user_name,
                                change_acl.statuscode, pkg_listing_log_msg)
                            pkg_log.acl = change_acl
                            pkg_list_log_msgs[pkg_listing].append(
                                pkg_listing_log_msg)

                # Save a reference to all pkg_listings
                listings.append(pkg_listing)
        else:
            # Default to the devel branch
            collection = Collection.query.filter_by(
                    name='Fedora', version='devel').one()
            pkg_listing = PackageListing.query.filter_by(
                    collectionid=collection.id,
                    packageid=pkg.id).one()
            listings = [pkg_listing]

        # If ownership, change the owners
        if 'owner' in changes:
            # Already retrieved owner into person
            for pkg_listing in listings:
                pkg_listing.owner = person['username']
                log_msg = '%s changed owner of %s in %s %s to %s' % (
                        identity.current.user_name,
                        pkg_listing.package.name,
                        pkg_listing.collection.name,
                        pkg_listing.collection.version,
                        person['username'],
                        )
                if person['username'] == 'orphan':
                    status = STATUS['Orphaned']
                else:
                    status = STATUS['Owned']
                pkg_log = PackageListingLog(
                        identity.current.user_name,
                        status.statuscodeid,
                        log_msg
                        )
                pkg_log.listing = pkg_listing
                try:
                    pkg_list_log_msgs[pkg_listing].append(log_msg)
                except KeyError:
                    pkg_list_log_msgs[pkg_listing] = [log_msg]

        # Change the cclist
        if 'ccList' in changes:
            cc_list = simplejson.loads(changes['ccList'])
            for username in cc_list:
                # Lookup the list members in fas
                try:
                    person = fas.cache[username]
                except KeyError:
                    return dict(status=False, message=_('New cclist member'
                        ' %(user)s is not in FAS') % {'user':  username})
                # Add Acls for them to the packages
                for pkg_listing in listings:
                    for acl in ('watchbugzilla', 'watchcommits'):
                        person_acl = self._create_or_modify_acl(pkg_listing,
                                username, acl, STATUS['Approved'])
                        log_msg = '%s approved %s on %s (%s %s)' \
                                ' for %s' % (
                                        identity.current.user_name,
                                        acl, pkg_listing.package.name,
                                        pkg_listing.collection.name,
                                        pkg_listing.collection.version,
                                        username)
                        pkg_log = PersonPackageListingAclLog(
                                identity.current.user_name,
                                STATUS['Approved'].statuscodeid,
                                log_msg
                                )
                        pkg_log.acl = person_acl
                        try:
                            pkg_list_log_msgs[pkg_listing].append(log_msg)
                        except KeyError:
                            pkg_list_log_msgs[pkg_listing] = [log_msg]

        # Change the comaintainers
        if 'comaintList' in changes:
            comaint_list = simplejson.loads(changes['comaintList'])
            for username in comaint_list:
                # Lookup the list members in fas
                # Note: this can't come from the cache ATM as it is used in a
                # call to _acl_can_be_held_by_user() which needs group
                # information.
                person = fas.person_by_username(username)
                if not person:
                    return dict(status=False, message=_('New comaintainer'
                        '%(user)s does not have a Fedora Account') % {
                            'user': username})

                # Make sure the comaintainer is in the correct group
                try:
                    self._acl_can_be_held_by_user('approveacls', person)
                except AclNotAllowedError, e:
                    return dict(status=False, message=str(e))

                # Add Acls for them to the packages
                for pkg_listing in listings:
                    for acl in ('watchbugzilla', 'watchcommits', 'commit',
                            'build', 'approveacls'):
                        person_acl = self._create_or_modify_acl(pkg_listing,
                                username, acl, STATUS['Approved'])

                        # Make sure a log is created in the db as well.
                        log_msg = u'%s approved %s on %s (%s %s)' \
                                ' for %s' % (
                                        identity.current.user_name, acl,
                                        pkg_listing.package.name,
                                        pkg_listing.collection.name,
                                        pkg_listing.collection.version,
                                        username)
                        pkg_log = PersonPackageListingAclLog(
                                identity.current.user_name,
                                STATUS['Approved'].statuscodeid,
                                log_msg
                                )
                        pkg_log.acl = person_acl
                        try:
                            pkg_list_log_msgs[pkg_listing].append(log_msg)
                        except KeyError:
                            pkg_list_log_msgs[pkg_listing] = [log_msg]

        if 'groups' in changes:
            # Change whether the group can commit to cvs.
            group_list = simplejson.loads(changes['groups'])
            for group in group_list:
                # True means approve commit, False means deny
                if group_list[group] == True:
                    status = STATUS['Approved']
                else:
                    status = STATUS['Denied']

                # We don't let every group commit
                try:
                    self.groups[group]
                except KeyError:
                    if status == STATUS['Denied']:
                        # If we're turning it off we don't have to worry
                        continue
                    return dict(status=False, message=_('Group %(group)s is'
                        ' not allowed to commit') % {'group': group})

                for pkg_listing in listings:
                    group_acl = self._create_or_modify_group_acl(pkg_listing,
                            group, 'commit', status)

                    # Make sure a log is created in the db as well.
                    log_msg = u'%s %s %s for commit access on %s' \
                            ' (%s %s)' % (
                                    identity.current.user_name,
                                    status.statusname,
                                    group,
                                    pkg_listing.package.name,
                                    pkg_listing.collection.name,
                                    pkg_listing.collection.version)
                    pkg_log = GroupPackageListingAclLog(
                            identity.current.user_name,
                            status.statuscodeid,
                            log_msg
                            )
                    pkg_log.acl = group_acl
                    try:
                        pkg_list_log_msgs[pkg_listing].append(log_msg)
                    except KeyError:
                        pkg_list_log_msgs[pkg_listing] = [log_msg]

        try:
            session.flush()
        except SQLError, e:
            # :E1103: PackageListing is monkey patched by SQLAlchemy to have
            # the db fields.  So we have to disable this check here.
            # An error was generated
            return dict(status=False, message=_('Unable to modify'
                ' PackageListing %(pkg)s(%(collctn)s-%(ver)s)') % {
                    'pkg': pkg_listing.package.name,
                    'collctn': pkg_listing.collection.name,
                    'ver': pkg_listing.collection.version})

        # Send a log to people interested in this package as well
        if pkg_log_msg:
            self._send_log_msg(pkg_log_msg, _('%(pkg)s summary updated by'
                ' %(user)s') % { 'pkg': pkg.name,
                    'user': identity.current.user_name},
                identity.current.user, pkg.listings)
        for pkg_listing in pkg_list_log_msgs.keys():
            self._send_log_msg('\n'.join(pkg_list_log_msgs[pkg_listing]),
                    _('%(pkg)s (%(collctn)s, %(ver)s) updated by %(user)s') % {
                        'pkg': pkg.name, 'collctn': pkg_listing.collection.name,
                        'ver': pkg_listing.collection.version,
                        'user': identity.current.user_name},
                    identity.current.user, (pkg_listing,))
        return dict(status=True)

    @expose(allow_json=True)
    # Check that we have a tg.identity, otherwise you can't set any acls.
    @identity.require(identity.in_group(admin_grp))
    def clone_branch(self, pkg, branch, master, email_log=True):
        '''Make `branch` permissions mirror `master`, creating if necessary.

        Note: Branch names are short names like 'F-10', 'devel', 'EL-5'

        This is a Layer 2 API

        :arg pkg: Name of the package to clone
        :arg branch: Name of branch to create
        :arg master: Name of branch to take permissions from
        :kwarg email_log: If False, do not email a log message
        :type email_log: Boolean
        :returns: The cloned branch
        :rtype: PackageListing
        '''
        error_args  = {'package': pkg, 'master': master, 'branch': branch}

        # Retrieve the packagelisting for the master branch
        try:
            master_branch = PackageListing.query.join('package'
                    ).join('collection').options(lazyload('status')).filter(
                        and_(Package.name==pkg, Branch.branchname==master)
                        ).one()
        except InvalidRequestError:
            session.rollback()
            flash(_('"%(package)s" does not exist on branch "%(master)s"') %
                    error_args)
            return dict(exc='InvalidBranch')

        try:
            clone_branch = master_branch.clone(branch, identity.current.user_name)
        except InvalidRequestError, e:
            # Not a valid collection
            session.rollback()
            flash(_('"%(branch)s" is not a valid branch name') %
                {'branch': branch})
            return dict(exc='InvalidBranch')
        except Exception, e:
            session.rollback()
            error_args['msg'] = str(e)
            flash(_('Unable to clone "%(package)s %(master)s" to'
                ' "%(package)s %(branch)s": %(msg)s') % error_args)
            return dict(exc='CannotClone')

        try:
            session.flush()
        except SQLError, e:
            session.rollback()
            error_args['error'] = str(e)
            flash(_('Unable to save clone of %(package)s %(master)s for'
                ' %(branch)s to the database: %(error)s') % error_args)
            return dict(exc='DatabaseError')

        if email_log:
            log_params = {'user': identity.current.user_name,
                'pkg': pkg, 'branch': branch, 'master': master}
            msg = _('%(user)s cloned %(pkg)s %(branch)s from %(master)s') % \
                    log_params
            subject = _('%(pkg)s %(branch)s cloned from %(master)s') % \
                    log_params
            self._send_log_msg(msg, subject,
                identity.current.user, [clone_branch])

        return dict(pkglisting=clone_branch)

    @expose(allow_json=True)
    # Check that the requestor is in a group that could potentially set ACLs.
    @identity.require(identity.not_anonymous())
    def remove_user(self, username, pkg_name, collectn_list=None):
        '''Remove users from a package.

        :arg username: Name of user to remove from the package
        :arg pkg_name: Name of the package
        :kwarg collectn_list: list of collections like 'F-10', 'devel'.
          If collectn_list=None, user removed from all collections associated
          with the package
        '''
        try:
            # pylint: disable-msg=E1101
            pkg = Package.query.filter_by(name=pkg_name).one()
        except InvalidRequestError:
            flash(_('Package %(pkg)s does not exist') % {'pkg': pkg_name})
            return dict(exc='NoPackageError')

        #Check that the current user is allowed to change acl statuses
        if not identity.in_group(admin_grp):
            flash(_('%(user)s is not in admin_grp') % {
                'user': identity.current.user_name})
            return dict(exc='NoAllowError')

        log_msgs = []
        package_listings = []

        if collectn_list:
            if not isinstance(collectn_list,(tuple,list)):
                collectn_list = [collectn_list]
            for simple_name in collectn_list:
                try:
                    collectn = Collection.by_simple_name(simple_name)
                except InvalidRequestError:
                    flash(_('Collection %(collctn)s does not exist') % {
                        'collctn': simple_name})
                    return dict(exc='NoCollectionError')

                pkg_listing = PackageListing.query.filter_by(packageid=pkg.id,
                                  collectionid=collectn.id).one()
                package_listings.append(pkg_listing)

        else:
            package_listings = pkg.listings

        for pkg_listing in package_listings:
            acls = PersonPackageListingAcl.query.filter(and_(
                       PersonPackageListingAcl.c.personpackagelistingid
                           == PersonPackageListing.c.id,
                       PersonPackageListing.c.packagelistingid == pkg_listing.id,
                       PersonPackageListing.c.username == username)).all()

            for acl in acls:
                person_acl = self._create_or_modify_acl(pkg_listing, username,
                        acl.acl, STATUS['Obsolete'])

                log_msg = u'%s has set the %s acl on %s (%s %s) to Obsolete' \
                        ' for %s' % (
                                identity.current.user_name, acl, pkg.name,
                                pkg_listing.collection.name,
                                pkg_listing.collection.version, username)
                log = PersonPackageListingAclLog(identity.current.user.id,
                        STATUS['Obsolete'].statuscodeid, log_msg)
                log.acl = person_acl # pylint: disable-msg=W0201
                log_msgs.append(log_msg)

        try:
            session.flush()
        except SQLError, e:
            # An error was generated
            flash(_('Unable to save changes to the database: %(err)s') % {
                'err': e})
            return dict(exc='DatabaseError')


        user_email = username + '@fedoraproject.org'
        # Send a log to people interested in this package as well
        self._send_log_msg('\n'.join(log_msgs), _('%(pkg)s had acl change'
            ' status') % {'pkg': pkg.name}, identity.current.user,
            package_listings, other_email=(user_email,))

        return dict(status=True)
