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
Mapping of package related database tables to python classes.

.. data:: GROUP_MAP
    Map groupids to group names and back.  It only has the groups that the
    packagedb uses.
.. data:: DEFAULT_GROUPS
    Groups that get acls on the Package Database by default (in 0.3.x, the
    groups have to be listed here in order for them to show up in the Package
    Database at all.
'''
#
# PyLint Explanation
#

# :E1101: SQLAlchemy monkey patches the db fields into the class mappers so we
#   have to disable this check wherever we use the mapper classes.
# :R0903: Mapped classes will have few methods as SQLAlchemy will monkey patch
#   more methods in later.
# :R0913: The __init__ methods of the mapped classes may need many arguments
#   to fill the database tables.

from sqlalchemy import Table
from sqlalchemy.orm import relation, backref
from sqlalchemy.orm.collections import mapped_collection, \
        attribute_mapped_collection
from sqlalchemy.ext.associationproxy import association_proxy

from turbogears.database import metadata, mapper, get_engine
# Not the way we want to do this.  We need to genericize the logs
from turbogears import identity

from fedora.tg.json import SABase

from pkgdb.model.acls import PersonPackageListing, GroupPackageListing, \
        GroupPackageListingAcl

get_engine()

GROUP_MAP = {101197: 'cvsadmin',
    107427: 'uberpackager',
    'cvsadmin': 101197,
    'uberpackager': 107427}
DEFAULT_GROUPS = {'uberpackager': {'commit': True, 'build': True,
    'checkout': True}}

#
# Tables
#

# Package and PackageListing are straightforward translations.  Look at these
# if you're looking for a straightforward example.

# :C0103: Tables and mappers are constants but SQLAlchemy/TurboGears convention
# is not to name them with all uppercase
# pylint: disable-msg=C0103
PackageTable = Table('package', metadata, autoload=True)
PackageListingTable = Table('packagelisting', metadata, autoload=True)
# pylint: enable-msg=C0103

#
# Mapped Classes
#

class Package(SABase):
    '''Software we are packaging.

    This is equal to the software in one of our revision control directories.
    It is unversioned and not associated with a particular collection.

    Table -- Package
    '''

    # pylint: disable-msg=R0903,R0913
    def __init__(self, name, summary, statuscode, description=None,
            reviewurl=None, shouldopen=None):
        super(Package, self).__init__()
        self.name = name
        self.summary = summary
        self.statuscode = statuscode
        self.description = description
        self.reviewurl = reviewurl
        self.shouldopen = shouldopen

    def __repr__(self):
        return 'Package(%r, %r, %r, description=%r, reviewurl=%r, ' \
               'shouldopen=%r)' % (
                self.name, self.summary, self.statuscode, self.description,
                self.reviewurl, self.shouldopen)

    def create_listing(self, collection, owner, status,
            qacontact=None):
        '''Create a new PackageListing branch on this Package.

        :arg collection: Collection that the new PackageListing lives on
        :arg owner: The owner of the PackageListing
        :arg status: Status to set the PackageListing to
        :kwarg qacontact: QAContact for this PackageListing in bugzilla.
        :returns: The new PackageListing object.

        This creates a new PackageListing for this Package.  The PackageListing
        has default values set for group acls.
        '''
        from pkgdb.utils import STATUS

        # pylint: disable-msg=E1101
        from pkgdb.model.logs import PackageListingLog

        pkg_listing = PackageListing(owner, status.statuscodeid,
                packageid=self.id, collectionid=collection.id,
                qacontact=qacontact)
        for group in DEFAULT_GROUPS:
            new_group = GroupPackageListing(GROUP_MAP[group])
            pkg_listing.groups.append(new_group)
            for acl, status in DEFAULT_GROUPS[group].iteritems():
                if status:
                    acl_status = self.approvedStatus
                else:
                    acl_status = self.deniedStatus
                group_acl = GroupPackageListingAcl(acl, acl_status)
                # :W0201: grouppackagelisting is added to the model by
                #   SQLAlchemy so it doesn't appear in __init__
                # pylint: disable-msg=W0201
                group_acl.grouppackagelisting = new_group
                # pylint: enable-msg=W0201

        # Create a log message
        log = PackageListingLog(identity.current.user.id,
                STATUS['Added'].statuscodeid,
                '%(user)s added a %(branch)s to %(pkg)s' %
                {'user': identity.current.user_name, 'branch': collection,
                    'pkg': self.name})
        log.listing = pkg_listing

    def __init__(self, userid, action, description=None, changetime=None,
            packagelistingid=None):
        # pylint: enable-msg=E1101
        return pkg_listing

class PackageListing(SABase):
    '''This associates a package with a particular collection.

    Table -- PackageListing
    '''
    # pylint: disable-msg=R0903
    def __init__(self, owner, statuscode, packageid=None, collectionid=None,
            qacontact=None):
        # pylint: disable-msg=R0913
        super(PackageListing, self).__init__()
        self.packageid = packageid
        self.collectionid = collectionid
        self.owner = owner
        self.qacontact = qacontact
        self.statuscode = statuscode

    packagename = association_proxy('package', 'name')

    def __repr__(self):
        return 'PackageListing(%r, %r, packageid=%r, collectionid=%r,' \
                ' qacontact=%r)' % (self.owner, self.statuscode,
                        self.packageid, self.collectionid, self.qacontact)

    def clone(self, branch):
        '''Clone the permissions on this PackageListing to another `Branch`.

        :arg branch: `branchname` to make a new clone for
        :raises sqlalchemy.exceptions.InvalidRequestError: when a request
            does something that violates the SQL integrity of the database
            somehow.
        :returns: new branch
        :rtype: PackageListing
        '''
        from pkgdb.utils import STATUS
        # Retrieve the PackageListing for the to clone branch
        try:
            clone_branch = PackageListing.query.join('package'
                    ).join('collection').filter(
                        and_(Package.name==self.package.name, Branch.branchname==branch)
                        ).one()
        except InvalidRequestError:
            ### Create a new package listing for this release ###

            # Retrieve the collection to make the branch for
            clone_collection = Branch.query.filter_by(branchname=branch).one()

            # Create the new PackageListing
            clone_branch = self.package.create_listing(
                clone_collection, self.owner,
                STATUS['Approved'].statuscodeid,
                qacontact=self.qacontact)

        log_params = {'user': identity.current.user_name,
                'pkg': self.package.name, 'branch': branch}
        # Iterate through the acls in the master_branch
        for group_name, group in self.groups2.iteritems():
            log_params['group'] = group_name
            if group_name not in clone_branch.groups2:
                # Associate the group with the packagelisting
                clone_branch.groups2[group_name] = \
                        GroupPackageListing(group_name)
            clone_group = clone_branch.groups2[group_name]
            for acl_name, acl in group.acls2.iteritems():
                if acl_name not in clone_group.acls2:
                    clone_group.acls2[acl_name] = \
                            GroupPackageListingAcl(acl_name, acl.statuscode)
                else:
                    # Set the acl to have the correct status
                    if acl.statuscode != clone_group.acls2[acl_name].statuscode:
                        clone_group.acls2[acl_name].statuscode = acl.statuscode

                # Create a log message for this acl
                log_params['acl'] = acl.acl
                log_params['status'] = acl.status.locale['C'].statusname
                log_msg = '%(user)s set %(acl)s status for %(group)s to' \
                        ' %(status)s on (%(pkg)s %(branch)s)' % log_params
                log = GroupPackageListingAclLog(identity.current.user.id,
                        acl.statuscode, log_msg)
                log.acl = clone_group.acls2[acl_name]

        for person_name, person in self.people2:
            log_params['person'] = person_name
            if person_name not in clone_branch.people2:
                # Associate the person with the packagelisting
                clone_branch.people2[person_name] = \
                        PersonPackageListing(person_name)
            clone_person = clone_branch.people2[person_name]
            for acl_name, acl in person.acls2.iteritems():
                if acl_name not in clone_person.acls2:
                    clone_person.acls2[acl_name] = \
                            PersonPackageListingAcl(acl_name, acl.statuscode)
                else:
                    # Set the acl to have the correct status
                    if clone_person.acls2[acl_name].statuscode \
                            != acl.statuscode:
                        clone_person.acls2[acl_name].statuscode = acl.statuscode

                # Create a log message for this acl
                log_params['acl'] = acl.acl
                log_params['status'] = acl.status.locale['C'].statusname
                log_msg = '%(user)s set %(acl)s status for %(person)s to' \
                        ' %(status)s on (%(pkg)s %(branch)s)' % log_params
                log = PersonPackageListingAclLog(identity.current.user.id,
                        acl.statuscode, log_msg)
                log.acl = clone_person.acls2[acl_name]

        return clone_branch

def collection_alias(pkg_listing):
    '''Return the collection_alias that a package listing belongs to.

    :arg pkg_listing: PackageListing to find the Collection for.
    :returns: Collection Alias.  This is either the branchname or a combination
        of the collection name and version.

    This is used to make Branch keys for the dictionary mapping of pkg listings
    into packages.
    '''
    return pkg_listing.collection.simple_name()

#
# Mappers
#
mapper(Package, PackageTable, properties={
    # listings is here for compatibility.  Will be removed in 0.4.x
    'listings': relation(PackageListing),
    'listings2': relation(PackageListing, lazy=False,
        backref=backref('package', lazy=False),
        collection_class=mapped_collection(collection_alias))
    })
mapper(PackageListing, PackageListingTable, properties={
    'people': relation(PersonPackageListing),
    'people2': relation(PersonPackageListing, lazy=False,
        backref=backref('packagelisting'),
        collection_class = attribute_mapped_collection('userid')),
    'groups': relation(GroupPackageListing),
    'groups2': relation(GroupPackageListing, lazy=False,
        backref=backref('packagelisting'),
        collection_class = attribute_mapped_collection('groupid')),
    })
