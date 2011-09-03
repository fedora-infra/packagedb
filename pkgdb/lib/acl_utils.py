# -*- coding: utf-8 -*-
#
# Copyright (C) 2011  Red Hat, Inc.
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
# Author(s):         Frank Chiulli <fchiulli@fedoraproject.org>
#
'''
Utilities for all classes to use
'''

import xmlrpclib

from turbogears import identity

from pkgdb.lib.utils import comaintainer_memberships, fas, get_bz, \
        owner_memberships, STATUS
from pkgdb.model import PackageAclStatus, PersonPackageListing, \
        PersonPackageListingAcl

MAXSYSTEMUID = 9999


class AclNotAllowedError(Exception):
    '''The entity specified is not allowed to hold the requested acl.
    '''
    pass


def _acl_can_be_held_by_user(acl, user=None):
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
            # identity doesn't come with bugzilla_email, get it from the cache
            user.bugzilla_email = fas.cache[user.username]['bugzilla_email']
        try:
            get_bz().getuser(user.bugzilla_email) #pylint:disable-msg=E1101
        except xmlrpclib.Fault, e:
            if e.faultCode == 51:
                # No such user
                raise AclNotAllowedError(_('Email address %(bugzilla_email)s'
                        ' is not a valid bugzilla email address.  Either make'
                        ' a bugzilla account with that email address or change'
                        ' your email address in the Fedora Account System'
                        ' https://admin.fedoraproject.org/accounts/ to a valid'
                        ' bugzilla email address and try again.') % user)
            raise
        except xmlrpclib.ProtocolError, e:
            raise AclNotAllowedError(_('Unable to change ownership of bugs for'
                    ' this package at this time.  Please try again later.'))

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
                      if group['name'] in owner_memberships]:
                # If the user is in a knwon group they are allowed
                return True
            raise AclNotAllowedError(_('%(user)s must be in one of these'
                    ' groups: %(groups)s to own a package') %
                    {'user': user['username'],
                     'groups': owner_memberships})
        # Anyone in a known group can potentially own the package
        elif identity.in_any_group(*owner_memberships):
            return True
        raise AclNotAllowedError(_('%(user)s must be in one of these groups:'
                    ' %(groups)s to own a package') %
                    {'user': identity.current.user_name,
                     'groups': owner_memberships})

    # For any other acl, check whether the person is in an allowed group
    # New packagers can hold these acls
    if user:
        # If the person isn't in a known group raise an error
        if [group for group in user['approved_memberships']
                if group['name'] in comaintainer_memberships]:
            return True
        raise AclNotAllowedError(_('%(user)s must be in one of these groups:'
                    ' %(groups)s to hold the %(acl)s acl') %
                    {'user': user['username'],
                     'groups': comaintainer_memberships, 'acl': acl})
    elif identity.in_any_group(*comaintainer_memberships):
        return True

    raise AclNotAllowedError(_('%(user)s must be in one of these groups:'
            ' %(groups)s to hold the %(acl)s acl') %
            {'user': identity.current.user_name,
             'groups': comaintainer_memberships, 'acl': acl})

def _create_or_modify_acl(self, pkg_listing, person_name, new_acl, statusname):
    '''Create or modify an acl.

    Set an acl for a user.  This takes a packageListing and makes sure there's
    an ACL for them with the given status.  It will create a new ACL or modify
    an existing one depending on what's in the db already.

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
        person_acl = PersonPackageListingAcl(new_acl, STATUS[statusname])
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
            person_acl = PersonPackageListingAcl(new_acl, STATUS[statusname])
            change_person.acls.append(person_acl)

        # For now, we specialcase the build acl to reflect the commit this is
        # because we need to remove notifications and UI that depend on any
        # acl being set and for now, the commit acl is being used for build
        # and push.
        if new_acl == 'commit':
            _create_or_modify_acl(pkg_listing, person_name, 'build',
                                  statusname)
    #pylint:disable-msg=E1101
    person_acl.status = session.query(PackageAclStatus).filter(
            PackageAclStatus.statuscodeid==STATUS[statusname]).one()
    #pylint:enable-msg=E1101

    return person_acl

