# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2, or (at your option) any later version.  This
# program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the GNU
# General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA. Any Red Hat trademarks that are incorporated in the source
# code or documentation are not subject to the GNU General Public License and
# may only be used or replicated with the express permission of Red Hat, Inc.
#
# Author(s):
#   Frank Chiulli <fchiulli@fedoraproject.org>
#
'''
Controller to process requests for mass changes to acls.
'''

import itertools

import turbomail

from kitchen.iterutils import iterate

from sqlalchemy import and_, not_, select

from turbogears import controllers, error_handler, expose, identity, config, \
        flash, validators, validate
from turbogears.database import session

from pkgdb.model import Collection, CollectionTable, Package, PackageTable, \
        PackageAclStatus, PackageListing, PackageListingTable, \
        PersonPackageListing, PersonPackageListingAcl
from pkgdb.notifier import EventLogger
from pkgdb.lib.utils import admin_grp, fas, pkger_grp, provenpkger_grp, \
        STATUS, LOG

try:
    from fedora.textutils import to_unicode
except ImportError:
    from pkgdb.lib.utils import to_unicode

MAXSYSTEMUID = 9999

class AclNotAllowedError(Exception):
    '''
    The entity specified is not allowed to hold the requested acl.
    '''
    pass


class MassAcls(controllers.Controller):
    eventLogger = EventLogger()

    # Groups that a person must be in to own a package
    owner_memberships = (admin_grp, pkger_grp, provenpkger_grp)

    def __init__(self):
        controllers.Controller.__init__(self)


    def _send_log_msg(self, msg, subject, author, recipients):
        '''Send a log message to interested parties.

        This takes a message and sends it to the recipients.

        :arg msg: The log message to send
        :arg subject: A textual description or summary of the content of the
            message.
        :arg author: Email address or addresses of the author(s)
        :arg recipients: Email address or address which should receive the
            message (To header)

        All email addresses can be given either as a string or as a tuple
        ('Full Name', 'name@example.com').
        '''

        if config.get('mail.on', False):
            email = turbomail.Message(author, recipients,
                        '[pkgdb] %s' % (subject,))
            email.plain = msg
            turbomail.enqueue(email)
        else:
            LOG.debug(_('Would have sent: %(subject)s') % {
                        'subject': subject.encode('ascii', 'replace')})
            LOG.debug('To: %s' % recipients)
            LOG.debug('From: %s %s' %
                      (author[0].encode('ascii', 'replace'),
                       author[1].encode('ascii', 'replace')))
            LOG.debug('%s' % msg.encode('ascii', 'replace'))

    #
    # Copied from dispatchery.py.
    #
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
                    if acl.acl == 'approveacls'\
                            and acl.statuscode == STATUS['Approved']:
                        return 'comaintainer'
                break
        return False

    #
    # Copied from dispatchery.py.
    #
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
                get_bz().getuser(user.bugzilla_email) #pylint:disable-msg=E1101
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
            except xmlrpclib.ProtocolError, e:
                raise AclNotAllowedError(_('Unable to change ownership of bugs'
                    ' for this package at this time.  Please try again'
                    ' later.'))

        # Anyone can hold watchcommits and watchbugzilla
        if acl in ('watchbugzilla', 'watchcommits'):
            return True

        # For owner and approveacls, the user must be in packager or higher

        if acl in ('owner', 'approveacls'):
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
        # New packagers can hold these acls
        if user:
            # If the person isn't in a known group raise an error
            if [group for group in user['approved_memberships']
                    if group['name'] in self.comaintainer_memberships]:
                return True
            raise AclNotAllowedError(_('%(user)s must be in one of these'
                    'groups: %(groups)s to hold the %(acl)s acl') % 
                    {'user': user['username'],
                     'groups': self.comaintainer_memberships, 'acl': acl})
        elif identity.in_any_group(*self.comaintainer_memberships):
            return True
        raise AclNotAllowedError(_('%(user)s must be in one of these'
            ' groups: %(groups)s to hold the %(acl)s acl') % {
                'user': identity.current.user_name,
                'groups': self.comaintainer_memberships, 'acl': acl})

    #
    # Copied from dispatchery.py.
    #
    def _create_or_modify_acl(self, pkg_listing, person_name, new_acl,
                              statusname):
        '''Create or modify an acl.

        Set an acl for a user.  This takes a packageListing and makes sure
        there's an ACL for them with the given status.  It will create a new
        ACL or modify an existing one depending on what's in the db already.

        :arg pkg_listing: PackageListing on which to set the ACL.
        :arg person_name: PersonName to set the ACL for.
        :arg new_acl: ACL name to set.
        :arg statusname: Status DB Object we're setting the ACL to.
        '''
        # watchbugzilla and watchcommits are autocommit
        if new_acl in ('watchbugzilla', 'watchcommits') and \
                       statusname == 'Awaiting Review':
            statusname = 'Approved'

        change_person = pkg_listing.people2.get(person_name, None)
        if not change_person:
            # Person has no ACLs on this Package yet.  Create a record
            change_person = PersonPackageListing(person_name)
            pkg_listing.people.append(change_person)
            pkg_listing.people2[change_person.username] = change_person
            person_acl = PersonPackageListingAcl(new_acl,
                    STATUS[statusname])
            change_person.acls.append(person_acl) #pylint:disable-msg=E1101
        else:
            # Look for an acl for the person
            person_acl = None
            for acl in change_person.acls:
                if acl.acl == new_acl:
                    # Found the acl, change its status
                    person_acl = acl
                    acl.statuscode = STATUS[statusname]
                    break
            if not person_acl:
                # Acl was not found.  Create one.
                person_acl = PersonPackageListingAcl(new_acl,
                                                     STATUS[statusname])
                change_person.acls.append(person_acl)

            # For now, we specialcase the build acl to reflect the commit
            # this is because we need to remove notifications and UI that
            # depend on any acl being set and for now, the commit acl is being
            # used for build and push
            if new_acl == 'commit':
                self._create_or_modify_acl(pkg_listing, person_name, 'build',
                                           statusname)
        #pylint:disable-msg=E1101
        person_acl.status = session.query(PackageAclStatus).filter(
                PackageAclStatus.statuscodeid==STATUS[statusname]).one()
        #pylint:enable-msg=E1101

        return person_acl

    @expose(allow_json=True)
    @identity.require(identity.not_anonymous())
    def add_comaintainers(self, maintainer, comaintainers, pkg_pattern,
                          collectn_name, collectn_ver=None):
        '''Add comaintainers to all packagelistings that the maintainer either
        is the owner or has approveacls on.  Then email comaintainers/owners
        on those packages that the maintainer has changed the acls.

        :arg maintainer: the maintainer's username
             The current user must be the maintainer or the current user
             must be in the cvsadmin group.
        :arg comaintainers: a list of new comaintainers
        :arg pkg_pattern: a simple pattern for package names
        :arg collectn_name: limit packages to branches for this distribution.
        :kwarg collectn_ver: If given, limit information to this
            particular version of a distribution.

        Returns
            on success, message indicating the number of packages updated.
            on failure, message indicating error and exc set. 

        '''

        #
        # Validate the current user.
        # Either the current user is the maintainer or
        # the current user is in the cvsadmin group.
        #
        if (identity.current.user_name != maintainer):
            admin_grp = config.get('pkgdb.admin_grp', 'cvsadmin')
            if not identity.in_group(admin_grp):
                flash(_('%(user)s must be either the maintainer or in the '
                        'admin group (%(group)s) to add comaintainers' %
                        {'user': identity.current.user_name,
                         'group': admin_grp}))
                return dict(exc='AclNotAllowedError')

        #
        # Validate the list of new comaintainers.
        # Each user must be a valid FAS user.
        #
        nonFASUsers = []
        for comaintainer in list(iterate(comaintainers)):
            try:
                person = fas.cache[comaintainer]
            except KeyError:
                nonFASUsers.append(comaintainer)

        if len(nonFASUsers) != 0:
            userList = ','.join(nonFASUsers)
            flash(_('The following users are not valid FAS '
                    'users: %(users)s') % {'users': userList})
            return dict(exc='NonFASUserError')

        #
        # Validate the list of new comaintainers.
        # Each user must have approveacls.
        #
        nonAcls = []
        for comaintainer in list(iterate(comaintainers)):
            person = fas.cache[comaintainer]
            try:
                self._acl_can_be_held_by_user('approveacls', person)
            except AclNotAllowedError:
                nonAcls.append(comaintainer)

        if len(nonAcls) != 0:
            userList = ','.join(nonAcls)
            flash(_('The following users do not hold approveacls users '
                    '%(comaintainers)s') % userList)
            return dict(exc='AclNotAllowedError')

        #
        # Convert the pattern to a postgresql pattern.
        #
        pattern = to_unicode(pkg_pattern)
        sqlPattern = pattern.translate({ord(u'_'):u'\_',
                                        ord(u'*'):u'%',
                                        ord(u'?'):u'_'})

        #
        # Build a query to get packagelistings owned by the maintainer.
        #
        pkgsOwned_query = select([PackageTable.c.name,
                                  CollectionTable.c.name,
                                  CollectionTable.c.version,
                                  PackageListingTable.c.id],
                                 and_(Package.name.like(sqlPattern),
                                      Package.statuscode == 
                                          STATUS['Approved'],
                                      PackageListing.statuscode == 
                                          STATUS['Approved'],
                                      Collection.name == collectn_name,
                                      Collection.statuscode == 
                                          STATUS['Active'],
                                      Package.id == 
                                          PackageListing.packageid,
                                      PackageListing.collectionid == 
                                          Collection.id,
                                      PackageListing.owner == maintainer))
        if collectn_ver:
            pkgsOwned_query = pkgsOwned_query.where(Collection.version == 
                                                    collectn_ver)

        #
        # Build a query to get packagelistings for which the maintainer has
        # approveacls.
        #
        pkgsAcls_query = select([PackageTable.c.name, CollectionTable.c.name,
                                 CollectionTable.c.version, 
                                 PackageListingTable.c.id],
                                and_(Package.name.like(sqlPattern),
                                     Package.statuscode == STATUS['Approved'],
                                     PackageListing.statuscode == 
                                         STATUS['Approved'],
                                     PackageListing.packageid == Package.id,
                                     PackageListing.collectionid == 
                                         Collection.id,
                                     Collection.statuscode == STATUS['Active'],
                                     PersonPackageListing.username == 
                                         maintainer,
                                     PersonPackageListing.packagelistingid ==
                                         PackageListing.id,
                                     PersonPackageListing.id ==
                                         PersonPackageListingAcl.personpackagelistingid,
                                     PersonPackageListingAcl.acl ==
                                         'approveacls',
                                     PersonPackageListingAcl.statuscode ==
                                         STATUS['Approved']))
        if collectn_ver:
            pkgsAcls_query = pkgsAcls_query.where(Collection.version == 
                                                  collectn_ver)

        #
        # Turn the queries into a python object.
        #
        pkgListings = {}
        for pkglisting in itertools.chain(pkgsOwned_query.execute(),
                                          pkgsAcls_query.execute()):
            pkgListings[pkglisting[PackageListingTable.c.id]] = pkglisting

        #
        # Add Acls.
        #
        for pkglistingid in sorted(pkgListings.iterkeys()):
            pkglisting = PackageListing.query.filter_by(id =
                                                        pkglistingid).one()
            for comaintainer in list(iterate(comaintainers)):
                self._create_or_modify_acl(pkglisting, comaintainer,
                                           'approveacls', 'Approved')

        #
        # Get everyone with approveacls on all the packages.
        #
        email_recipients = {}
        email_recipients[maintainer] = maintainer + "@fedoraproject.org"
        email_recipients[maintainer] = \
            email_recipients[maintainer].encode('ascii', 'replace')
        for pkglistingid in pkgListings.keys():
            comaintainers_query = select((PersonPackageListing.username,),
                                      and_(PackageListing.id == pkglistingid,
                                           PackageListing.id ==
                                               PersonPackageListing.packagelistingid,
                                           PersonPackageListing.id ==
                                               PersonPackageListingAcl.id,
                                           PersonPackageListingAcl.acl ==
                                               'approveacls',
                                           PersonPackageListingAcl.statuscode ==
                                               STATUS['Approved']))
            user_list = comaintainers_query.execute()
            for record in user_list:
                username = record[0]
                email_recipients[username] = username + "@fedoraproject.org"
                email_recipients[username] = \
                    email_recipients[username].encode('ascii', 'replace')

        msg = '%s has added %s as a comaintainer to the following packages. ' \
              ' You are receiving this email because you are also a' \
              ' comaintainer of one or more of the packages.  You do not' \
              ' need to do anything at this time.\n' % \
              (maintainer, comaintainers)
        for pkglisting in pkgListings.values():
            msg += '\n'
            msg += ', '.join(pkglisting[0:3])

        self._send_log_msg(msg, 'Add Comaintainers',
                           ('PackageDB', 'pkgdb@fedoraproject.org'),
                           email_recipients.values())

        msg = '%d packages were updated.' % len(pkgListings)
        return dict(tg_flash=msg)
