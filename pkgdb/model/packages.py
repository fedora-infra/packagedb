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

from sqlalchemy import Table, Column, ForeignKey, Integer
from sqlalchemy import select, literal_column, not_
from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy.orm import polymorphic_union, relation, backref
from sqlalchemy.orm.collections import mapped_collection, \
        attribute_mapped_collection
from sqlalchemy.ext.associationproxy import association_proxy

from turbogears.database import metadata, mapper, get_engine

from fedora.tg.json import SABase

from acls import PersonPackageListing
from acls import GroupPackageListing

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
PackageTable = Table('package', metadata, autoload=True)
PackageListingTable = Table('packagelisting', metadata, autoload=True)

#
# Mapped Classes
#

class Package(SABase):
    '''Software we are packaging.

    This is equal to the software in one of our revision control directories.
    It is unversioned and not associated with a particular collection.

    Table -- Package
    '''

    # pylint: disable-msg=R0902, R0903
    def __init__(self, name, summary, statuscode, description=None,
            reviewurl=None, shouldopen=None):
        # pylint: disable-msg=R0913
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

    def create_listing(self, collection, owner, statuscode,
            qacontact=None):
        '''Create a new PackageListing branch on this Package.

        :arg collection: Collection that the new PackageListing lives on
        :arg owner: The owner of the PackageListing
        :arg statuscode: Status to set the PackageListing to
        :kwarg qacontact: QAContact for this PackageListing in bugzilla.
        :returns: The new PackageListing object.

        This creates a new PackageListing for this Package.  The PackageListing
        has default values set for group acls.
        '''
        pkg_listing = PackageListing(owner, statuscode, packageid=self.id,
            collecitonid=collection.id, qacontact=qacontact)
        for group in DEFAULT_GROUPS:
            new_group = GroupPackageListing(GROUP_MAP[group])
            pkg_listing.groups.append(new_group)
            for acl, status in DEFAULT_GROUPS[group].iteritems():
                if status:
                    acl_status = self.approvedStatus
                else:
                    acl_status = self.deniedStatus
                group_acl = GroupPackageListingAcl(acl, acl_status)
                group_acl.grouppackagelisting = new_group
        return pkg_listing

class PackageListing(SABase):
    '''This associates a package with a particular collection.

    Table -- PackageListing
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, owner, statuscode, packageid=None, collectionid=None,
            qacontact=None):
        # pylint: disable-msg=R0913
        super(PackageListing, self).__init__()
        self.packageid = packageid
        self.collectionid = collectionid
        self.owner = owner
        self.qacontact = qacontact
        self.statuscode = statuscode

    def __repr__(self):
        return 'PackageListing(%r, %r, packageid=%r, collectionid=%r,' \
                ' qacontact=%r)' % (self.owner, self.statuscode,
                        self.packageid, self.collectionid, self.qacontact)
    packagename = association_proxy('package', 'name')

#
# Mappers
#
def collection_alias(pkg_listing):
    '''Return the collection_alias that a package listing belongs to.

    :arg pkg_listing: PackageListing to find the Collection for.
    :returns: Collection Alias.  This is either the branchname or a combination
        of the collection name and version.

    This is used to make Branch keys.
    '''
    return pkg_listing.collection.simple_name()

mapper(Package, PackageTable, properties = {
    # listings is here for compatibility.  Will be removed in 0.4.x
    'listings': relation(PackageListing),
    'listings2': relation(PackageListing, backref='package',
        collection_class = mapped_collection(collection_alias))
    })
mapper(PackageListing, PackageListingTable, properties = {
    'people' : relation(PersonPackageListing),
    'people2' : relation(PersonPackageListing, backref='packagelisting',
        collection_class = attribute_mapped_collection('userid')),
    'groups' : relation(GroupPackageListing),
    'groups2' : relation(GroupPackageListing, backref='packagelisting',
        collection_class = attribute_mapped_collection('groupid')),
    })
