# -*- coding: utf-8 -*-
#
# Copyright © 2007-2008  Red Hat, Inc.
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
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Mapping of acl related database tables
'''
#
# PyLint Explanation
#

# :R0903: Mapped classes will have few methods as SQLAlchemy will monkey patch
#   more methods in later.
# :R0913: The __init__ methods of the mapped classes may need many arguments
#   to fill the database tables.

from sqlalchemy import Table, Column, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy import Integer, Text, Index, DDL
from sqlalchemy import CheckConstraint
from sqlalchemy.orm import relation, backref
from sqlalchemy.orm.collections import attribute_mapped_collection
from turbogears.database import metadata, mapper, get_engine
from pkgdb.lib.db import Grant_RW

from fedora.tg.json import SABase

get_engine()

#
# Mapped Tables
#

# :C0103: Tables and mappers are constants but SQLAlchemy/TurboGears convention
# is not to name them with all uppercase
# pylint: disable-msg=C0103
# Who is interested in this package.
#
# Fields:
# :id: Primary key
# :packageListingId: What package in what collection has this value.
# :username: User id from the account system.
PersonPackageListingTable = Table('personpackagelisting', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('username', Text(),  nullable=False),
    Column('packagelistingid', Integer(),  nullable=False),
    ForeignKeyConstraint(['packagelistingid'],['packagelisting.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
    UniqueConstraint('username', 'packagelistingid',
        name='personpackagelisting_userid_key')
)
Index('personpackagelisting_userid_idx', PersonPackageListingTable.c.username)
Index('personpackagelisting_packagelistingid_idx', PersonPackageListingTable.c.packagelistingid)
DDL('ALTER TABLE personpackagelisting CLUSTER ON personpackagelisting_packagelistingid_idx', on='postgres')\
    .execute_at('after-create', PersonPackageListingTable)
Grant_RW(PersonPackageListingTable)



#
# Group that's interested in the package.
#
# Fields:
# :id: Primary key
# :packageListingId: What package in what collection has this value.
# :groupname: User id from the account system.
GroupPackageListingTable = Table('grouppackagelisting', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('groupname', Text(),  nullable=False),
    Column('packagelistingid', Integer(),  nullable=False),
    ForeignKeyConstraint(['packagelistingid'],['packagelisting.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
    UniqueConstraint('groupname', 'packagelistingid',
        name='grouppackagelisting_groupid_key')
)
Index('grouppackagelisting_packagelistingid_idx', GroupPackageListingTable.c.packagelistingid)
DDL('ALTER TABLE grouppackagelisting CLUSTER ON grouppackagelisting_packagelistingid_idx', on='postgres')\
    .execute_at('after-create', GroupPackageListingTable)
Grant_RW(GroupPackageListingTable)


# List the Acls that belong to a personPkgListing
#
# Fields:
# :id: Primary key
# :personPackageListingId: The person-packagelisting combination that this
#   acl was made for.
# :acl: Permission being granted to this person.
# :statuscode: Status of the acl.  Whether approved or not.
PersonPackageListingAclTable = Table('personpackagelistingacl', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('personpackagelistingid', Integer(),  nullable=False),
    Column('acl', Text(),  nullable=False),
    Column('statuscode', Integer(),  nullable=False),
    UniqueConstraint('personpackagelistingid', 'acl',
        name='personpackagelistingacl_personpackagelistingid_key'),
    ForeignKeyConstraint(['personpackagelistingid'],['personpackagelisting.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
    ForeignKeyConstraint(['statuscode'],['packageaclstatuscode.statuscodeid'], onupdate="CASCADE",
        ondelete="RESTRICT"),
    CheckConstraint("acl = 'commit' OR acl = 'watchbugzilla' OR acl = 'watchcommits'"
        " OR acl = 'approveacls' OR acl = 'checkout'", name='personpackagelistingacl_acl_check')
)
# FIXME: This trigger is created just in postgres. If it is needed in other DB
# (in sqlite for testing) it has to be added manually

# Make the acl field non-updatable.  This prevents people from getting a
# permission and then changing the type of permission to a different one.
# 20 January 2007 Tested:
# [x] Was unable to update an acl field
# [x] Was able to update packagelistingid
no_acl_update_pgfunc = """
    CREATE OR REPLACE FUNCTION no_acl_update() RETURNS trigger
        AS $$
    BEGIN
      if (NEW.acl = OLD.acl) then
        return NEW;
      else
        raise exception 'Cannot update acl field';
      end if;
      return NULL;
    END;
    $$
        LANGUAGE plpgsql;
    """
DDL(no_acl_update_pgfunc, on='postgres').execute_at('before-create', PersonPackageListingAclTable)
# DROP is not necessary as we drop plpgsql with CASCADE
DDL('CREATE TRIGGER no_person_acl_update_trigger BEFORE UPDATE ON personpackagelistingacl'
        ' FOR EACH ROW EXECUTE PROCEDURE no_acl_update()', on='postgres')\
    .execute_at('after-create', PersonPackageListingAclTable)
Index('personpackagelistingacl_personpackagelistingid_idx', PersonPackageListingAclTable.c.personpackagelistingid)
DDL('ALTER TABLE personpackagelistingacl CLUSTER ON personpackagelistingacl_personpackagelistingid_idx', on='postgres')\
    .execute_at('after-create', PersonPackageListingAclTable)
Grant_RW(PersonPackageListingAclTable)



# List the Acls that belong to a groupPkgListing.
# Fields:
# :id: Primary key
# :groupPackageListingId: The person-packagelisting combination that this
#   acl was made for.
# :acl: Permission being granted to this person.
# :statuscode: Status of the acl.  Whether approved or not.
GroupPackageListingAclTable = Table('grouppackagelistingacl', metadata,
    Column('id', Integer(),  primary_key=True, nullable=False),
    Column('grouppackagelistingid', Integer(),  nullable=False),
    Column('acl', Text(length=None, convert_unicode=False, assert_unicode=None),  nullable=False),
    Column('statuscode', Integer(),  nullable=False),
    UniqueConstraint('grouppackagelistingid', 'acl',
        name='grouppackagelistingacl_grouppackagelistingid_key'),
    ForeignKeyConstraint(['grouppackagelistingid'],['grouppackagelisting.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
    ForeignKeyConstraint(['statuscode'],['packageaclstatuscode.statuscodeid'], onupdate="CASCADE",
        ondelete="RESTRICT"),
    CheckConstraint("acl = 'commit' OR acl = 'watchbugzilla' OR acl = 'watchcommits'"
        " OR acl = 'approveacls' OR acl = 'checkout'", name='grouppackagelistingacl_acl_check')
)
Index('grouppackagelistingacl_grouppackagelistingid_idx', GroupPackageListingAclTable.c.grouppackagelistingid)
DDL('ALTER TABLE grouppackagelistingacl CLUSTER ON grouppackagelistingacl_grouppackagelistingid_idx', on='postgres')\
    .execute_at('after-create', GroupPackageListingAclTable)
# FIXME: This trigger is created just in postgres. If it is needed in other DB
# (in sqlite for testing) it has to be added manually
DDL(no_acl_update_pgfunc, on='postgres').execute_at('before-create', GroupPackageListingAclTable)
DDL('CREATE TRIGGER no_group_acl_update_trigger BEFORE UPDATE ON grouppackagelistingacl'
        ' FOR EACH ROW EXECUTE PROCEDURE no_acl_update()', on='postgres')\
    .execute_at('after-create', GroupPackageListingAclTable)
Grant_RW(GroupPackageListingAclTable)
# pylint: enable-msg=C0103

#
# Mapped Classes
#

class PersonPackageListing(SABase):
    '''Associate a person with a PackageListing.

    People who are watching or can modify a packagelisting.

    Table -- PersonPackageListing
    '''
    # pylint: disable-msg=R0903
    def __init__(self, username, packagelistingid=None):
        # pylint: disable-msg=R0913
        super(PersonPackageListing, self).__init__()
        self.username = username
        self.packagelistingid = packagelistingid

    def __repr__(self):
        return 'PersonPackageListing(%r, %r)' % (self.username,
                self.packagelistingid)

class GroupPackageListing(SABase):
    '''Associate a group with a PackageListing.

    Table -- GroupPackageListing
    '''
    # pylint: disable-msg=R0903
    def __init__(self, groupname, packagelistingid=None):
        # pylint: disable-msg=R0913
        super(GroupPackageListing, self).__init__()
        self.groupname = groupname
        self.packagelistingid = packagelistingid

    def __repr__(self):
        return 'GroupPackageListing(%r, %r)' % (self.groupname,
                self.packagelistingid)

class PersonPackageListingAcl(SABase):
    '''Acl on a package that a person owns.

    Table -- PersonPackageListingAcl
    '''
    # pylint: disable-msg=R0903
    def __init__(self, acl, statuscode=None, personpackagelistingid=None):
        # pylint: disable-msg=R0913
        super(PersonPackageListingAcl, self).__init__()
        self.personpackagelistingid = personpackagelistingid
        self.acl = acl
        self.statuscode = statuscode

    def __repr__(self):
        return 'PersonPackageListingAcl(%r, %r, personpackagelistingid=%r)' \
                % (self.acl, self.statuscode, self.personpackagelistingid)

class GroupPackageListingAcl(SABase):
    '''Acl on a package that a group owns.

    Table -- GroupPackageListingAcl
    '''
    # pylint: disable-msg=R0903
    def __init__(self, acl, statuscode=None, grouppackagelistingid=None):
        # pylint: disable-msg=R0913
        super(GroupPackageListingAcl, self).__init__()
        self.grouppackagelistingid = grouppackagelistingid
        self.acl = acl
        self.statuscode = statuscode

    def __repr__(self):
        return 'GroupPackageListingAcl(%r, %r, grouppackagelistingid=%r)' % (
                self.acl, self.statuscode, self.grouppackagelistingid)

#
# Mappers
#

mapper(PersonPackageListing, PersonPackageListingTable, properties={
    'acls': relation(PersonPackageListingAcl),
    'acls2': relation(PersonPackageListingAcl,
        backref=backref('personpackagelisting'),
        collection_class=attribute_mapped_collection('acl'))
    })
mapper(GroupPackageListing, GroupPackageListingTable, properties={
    'acls': relation(GroupPackageListingAcl),
    'acls2': relation(GroupPackageListingAcl,
        backref=backref('grouppackagelisting'),
        collection_class=attribute_mapped_collection('acl'))
    })
mapper(PersonPackageListingAcl, PersonPackageListingAclTable)
mapper(GroupPackageListingAcl, GroupPackageListingAclTable)
