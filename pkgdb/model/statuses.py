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
Mapping of database tables related to Statuses to python classes
'''

from sqlalchemy import Table, Column, Integer, String, Text
from sqlalchemy import PassiveDefault, ForeignKeyConstraint, DDL
from sqlalchemy import text, Index
from sqlalchemy.orm import relation, backref
from sqlalchemy.orm.collections import attribute_mapped_collection
from turbogears.database import metadata, mapper, get_engine

from fedora.tg.json import SABase

from pkgdb.model.packages import Package, PackageListing
from pkgdb.model.acls import PersonPackageListingAcl, GroupPackageListingAcl
from pkgdb.lib.db import Grant_RW, initial_data

get_engine()

# status codes constants
SC_ACTIVE = 1
SC_ADDED = 2
SC_APPROVED = 3
SC_AWAITING_BRANCH = 4
SC_AWAITING_DEVELOPMENT = 5
SC_AWAITING_QA = 6
SC_AWAITING_PUBLISH = 7
SC_AWAITING_REVIEW = 8
SC_EOL = 9
SC_DENIED = 10
SC_MAINTENENCE = 11
SC_MODIFIED = 12
SC_OBSOLETE = 13
SC_ORPHANED = 14
SC_OWNED = 15
SC_REJECTED = 16
SC_REMOVED = 17
SC_UNDER_DEVELOPMENT = 18
SC_UNDER_REVIEW = 19
SC_DEPRECATED = 20

#
# Mapped Tables
#

# These are a bit convoluted as we have a 1:1:N relation between
# SpecificStatusTable:StatusCodeTable:StatusTranslationTable

# I'd like to merely override the pylint regex for this particular section of
# code as # these variables are special.  They chould be treated more like
# class definitions than constants.  Oh well.
# pylint: disable-msg=C0103

# statuscode
statuscode = Table('statuscode', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
)
initial_data(statuscode,
    ['id'],
    *[[id] for id in range(1, 21)])
Grant_RW(statuscode)


# statuscodetranslation
StatusTranslationTable = Table('statuscodetranslation', metadata,
    Column('statuscodeid', Integer(), primary_key=True, autoincrement=False, nullable=False),
    Column('language', String(32), server_default=text("'C'"), primary_key=True, nullable=False),
    Column('statusname', Text(), nullable=False),
    Column('description', Text()),
    ForeignKeyConstraint(['statuscodeid'], ['statuscode.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)
initial_data(StatusTranslationTable, 
    ('statuscodeid', 'language', 'statusname', 'description'), 
	(SC_ACTIVE, 'C', 'Active', ''),
	(SC_ADDED, 'C', 'Added', ''),
	(SC_APPROVED, 'C', 'Approved', ''),
	(SC_AWAITING_BRANCH, 'C', 'Awaiting Branch', ''),
	(SC_AWAITING_DEVELOPMENT, 'C', 'Awaiting Development', ''),
	(SC_AWAITING_QA, 'C', 'Awaiting QA', ''),
	(SC_AWAITING_PUBLISH, 'C', 'Awaiting Publish', ''),
	(SC_AWAITING_REVIEW, 'C', 'Awaiting Review', ''),
	(SC_EOL, 'C', 'EOL', ''),
	(SC_DENIED, 'C', 'Denied', ''),
	(SC_MAINTENENCE, 'C', 'Maintenence', ''),
	(SC_MODIFIED, 'C', 'Modified', ''),
	(SC_OBSOLETE, 'C', 'Obsolete', ''),
	(SC_ORPHANED, 'C', 'Orphaned', ''),
	(SC_OWNED, 'C', 'Owned', ''),
	(SC_REJECTED, 'C', 'Rejected', ''),
	(SC_REMOVED, 'C', 'Removed', ''),
	(SC_UNDER_DEVELOPMENT, 'C', 'Under Development', ''),
	(SC_UNDER_REVIEW, 'C', 'Under Review', ''),
	(SC_DEPRECATED, 'C', 'Deprecated', ''))
Index('statuscodetranslation_statusname_idx', StatusTranslationTable.c.statusname)
Grant_RW(StatusTranslationTable)


CollectionStatusTable = Table('collectionstatuscode', metadata,
    Column('statuscodeid', Integer(), primary_key=True, autoincrement=False, nullable=False),
    ForeignKeyConstraint(['statuscodeid'], ['statuscode.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)
initial_data(CollectionStatusTable,
    ['statuscodeid'],
    [SC_ACTIVE], [SC_EOL], [SC_REJECTED], [SC_UNDER_DEVELOPMENT])
Grant_RW(CollectionStatusTable)

add_status_to_log_pgfunc = """
    CREATE OR REPLACE FUNCTION add_status_to_log() RETURNS trigger
        AS $_$
    DECLARE
      cmd text;
      tableName text;
    BEGIN
      -- 8.2 uses a different name:
      -- tableName := regexp_replace(TG_TABLE_NAME, 'statuscode$', 'logstatuscode');
      tableName := regexp_replace(TG_RELNAME, 'statuscode$', 'logstatuscode');
      if (TG_OP = 'INSERT') then
        cmd := 'insert into ' || tableName || ' values (' || NEW.statusCodeId ||')';
        execute cmd;
        return NEW;
      elsif (TG_OP = 'DELETE') then
        cmd := 'delete from ' || tableName || ' where statusCodeId = ' || OLD.statusCodeId;
        execute cmd;
        return OLD;
      elsif (TG_OP = 'UPDATE') then
        cmd := 'update ' || tableName || ' set statusCodeId = ' || NEW.statusCodeId || ' where statusCodeId = ' || OLD.statusCodeId;
        execute cmd;
        return NEW;
      end if;
      return NULL;
    END;
    $_$
        LANGUAGE plpgsql;
    """
DDL(add_status_to_log_pgfunc, on='postgres')\
    .execute_at('before-create', CollectionStatusTable)
# DROP is not necessary as we drop plpgsql with CASCADE

# FIXME: This trigger is created just in postgres. If it is needed in other DB
# (in sqlite for testing) it has to be added manually
DDL('CREATE TRIGGER add_status_to_action AFTER INSERT OR DELETE OR UPDATE ON collectionstatuscode '
        'FOR EACH ROW EXECUTE PROCEDURE add_status_to_log()', on='postgres')\
    .execute_at('after-create', CollectionStatusTable)


# Package Listing Status Table.  Like the other status tables, this one has to
# connect translations to the statuses particular to the PackageListing.  This
# make it somewhat more convoluted but all the status tables follow the same
# pattern.
PackageListingStatusTable = Table('packagelistingstatuscode', metadata,
    Column('statuscodeid', Integer(), primary_key=True, autoincrement=False, nullable=False),
    ForeignKeyConstraint(['statuscodeid'], ['statuscode.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)
initial_data(PackageListingStatusTable,
    ['statuscodeid'],
    [SC_APPROVED], [SC_AWAITING_BRANCH], [SC_AWAITING_REVIEW], [SC_DENIED], 
    [SC_OBSOLETE], [SC_ORPHANED], [SC_REMOVED], [SC_DEPRECATED])
# FIXME: This trigger is created just in postgres. If it is needed in other DB
# (in sqlite for testing) it has to be added manually
DDL(add_status_to_log_pgfunc, on='postgres')\
    .execute_at('before-create', PackageListingStatusTable)
# DROP is not necessary as we drop plpgsql with CASCADE
DDL('CREATE TRIGGER add_status_to_action AFTER INSERT OR DELETE OR UPDATE ON packagelistingstatuscode '
        'FOR EACH ROW EXECUTE PROCEDURE add_status_to_log()', on='postgres')\
    .execute_at('after-create', PackageListingStatusTable)
Grant_RW(PackageListingStatusTable)


# Package Status Table.
PackageStatusTable = Table('packagestatuscode', metadata,
    Column('statuscodeid', Integer(), primary_key=True, autoincrement=False, nullable=False),
    ForeignKeyConstraint(['statuscodeid'], ['statuscode.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)
initial_data(PackageStatusTable,
    ['statuscodeid'],
    [SC_APPROVED], [SC_AWAITING_REVIEW], [SC_DENIED], [SC_REMOVED], [SC_UNDER_REVIEW])
# FIXME: This trigger is created just in postgres. If it is needed in other DB
# (in sqlite for testing) it has to be added manually
DDL(add_status_to_log_pgfunc, on='postgres')\
    .execute_at('before-create', PackageStatusTable)
# DROP is not necessary as we drop plpgsql with CASCADE

DDL('CREATE TRIGGER add_status_to_action AFTER INSERT OR DELETE OR UPDATE ON packagestatuscode '
        'FOR EACH ROW EXECUTE PROCEDURE add_status_to_log()', on='postgres')\
    .execute_at('after-create', PackageStatusTable)
Grant_RW(PackageStatusTable)



# Package Acl Status Table
PackageAclStatusTable = Table('packageaclstatuscode', metadata,
    Column('statuscodeid', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    ForeignKeyConstraint(['statuscodeid'], ['statuscode.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)
initial_data(PackageAclStatusTable,
    ['statuscodeid'],
    [SC_APPROVED], [SC_AWAITING_REVIEW], [SC_DENIED], [SC_OBSOLETE])
DDL(add_status_to_log_pgfunc, on='postgres')\
    .execute_at('before-create', PackageAclStatusTable)
# DROP is not necessary as we drop plpgsql with CASCADE
# FIXME: This trigger is created just in postgres. If it is needed in other DB
# (in sqlite for testing) it has to be added manually
DDL('CREATE TRIGGER add_status_to_action AFTER INSERT OR DELETE OR UPDATE ON packageaclstatuscode '
        'FOR EACH ROW EXECUTE PROCEDURE add_status_to_log()', on='postgres')\
    .execute_at('after-create', PackageAclStatusTable)
Grant_RW(PackageAclStatusTable)


PackageBuildStatusCodeTable = Table('packagebuildstatuscode', metadata,
    Column('statuscodeid', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    ForeignKeyConstraint(['statuscodeid'], ['statuscode.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)
initial_data(PackageBuildStatusCodeTable,
    ['statuscodeid'],
    [SC_APPROVED], [SC_AWAITING_DEVELOPMENT], [SC_AWAITING_QA], [SC_AWAITING_PUBLISH], 
    [SC_AWAITING_REVIEW], [SC_DENIED], [SC_OBSOLETE])
DDL(add_status_to_log_pgfunc, on='postgres')\
    .execute_at('before-create', PackageBuildStatusCodeTable)
# DROP is not necessary as we drop plpgsql with CASCADE
# FIXME: This trigger is created just in postgres. If it is needed in other DB
# (in sqlite for testing) it has to be added manually
DDL('CREATE TRIGGER add_status_to_action AFTER INSERT OR DELETE OR UPDATE ON packagebuildstatuscode '
        'FOR EACH ROW EXECUTE PROCEDURE add_status_to_log()', on='postgres')\
    .execute_at('after-create', PackageBuildStatusCodeTable)
Grant_RW(PackageBuildStatusCodeTable)

#
# Mapped Classes
#

class StatusTranslation(SABase):
    '''Map status codes to status names in various languages.

    Table -- StatusCodeTranslation
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, statuscodeid, statusname, language=None,
            description=None):
        '''
        :statuscodeid: id of the status this translation applies to
        :statusname: translated string
        :language: Languages code that this string is for.  if not given.
            defaults to 'C'
        :description: a description of what this status means.  May be used in
            online help
        '''
        # pylint: disable-msg=R0913
        super(StatusTranslation, self).__init__()
        self.statuscodeid = statuscodeid
        self.statusname = statusname
        self.language = language or None
        self.description = description or None

    def __repr__(self):
        return 'StatusTranslation(%r, %r, language=%r, description=%r)' \
                % (self.statuscodeid, self.statusname, self.language,
                        self.description)

class BaseStatus(SABase):
    '''Fields common to all Statuses.'''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, statuscodeid):
        # pylint: disable-msg=R0913
        super(BaseStatus, self).__init__()
        self.statuscodeid = statuscodeid

class CollectionStatus(BaseStatus):
    '''Subset of status codes that are applicable to collections.

    Table -- CollectionStatusCode
    '''
    # pylint: disable-msg=R0902, R0903
    def __repr__(self):
        return 'CollectionStatus(%r)' % self.statuscodeid

class PackageStatus(BaseStatus):
    '''Subset of status codes that apply to packages.

    Table -- PackageStatusCode
    '''
    # pylint: disable-msg=R0902, R0903
    def __repr__(self):
        return 'PackageStatus(%r)' % self.statuscodeid

class PackageListingStatus(BaseStatus):
    '''Subset of status codes that are applicable to package listings.

    Table -- PackageListingStatusCode
    '''
    # pylint: disable-msg=R0902, R0903
    def __repr__(self):
        return 'PackageListingStatus(%r)' % self.statuscodeid

class PackageAclStatus(BaseStatus):
    ''' Subset of status codes that apply to Person and Group Package Acls.

    Table -- PackageAclStatusCode
    '''
    # pylint: disable-msg=R0902, R0903
    def __repr__(self):
        return 'PackageAclStatus(%r)' % self.statuscodeid

#
# Mappers
#

mapper(StatusTranslation, StatusTranslationTable)
mapper(CollectionStatus, CollectionStatusTable, properties={
    'translations': relation(StatusTranslation,
        order_by=StatusTranslationTable.c.language,
        primaryjoin=StatusTranslationTable.c.statuscodeid \
                == CollectionStatusTable.c.statuscodeid,
        foreign_keys=[StatusTranslationTable.c.statuscodeid]),
    'locale': relation(StatusTranslation,
        primaryjoin=StatusTranslationTable.c.statuscodeid \
                == CollectionStatusTable.c.statuscodeid,
        foreign_keys=[StatusTranslationTable.c.statuscodeid],
        collection_class=attribute_mapped_collection('language'),
        backref=backref('cstatuscode',
            foreign_keys=[StatusTranslationTable.c.statuscodeid],
            primaryjoin=StatusTranslationTable.c.statuscodeid \
                    == CollectionStatusTable.c.statuscodeid)),
    })

mapper(PackageListingStatus, PackageListingStatusTable, properties={
    'listings': relation(PackageListing, backref=backref('status')),
    'translations': relation(StatusTranslation,
        order_by=StatusTranslationTable.c.language,
        primaryjoin=StatusTranslationTable.c.statuscodeid \
                == PackageListingStatusTable.c.statuscodeid,
        foreign_keys=[StatusTranslationTable.c.statuscodeid]),
    'locale': relation(StatusTranslation,
        order_by=StatusTranslationTable.c.language,
        primaryjoin=StatusTranslationTable.c.statuscodeid \
                == PackageListingStatusTable.c.statuscodeid,
        foreign_keys=[StatusTranslationTable.c.statuscodeid],
        collection_class=attribute_mapped_collection('language'),
        backref=backref('plstatuscode',
            foreign_keys=[StatusTranslationTable.c.statuscodeid],
            primaryjoin=StatusTranslationTable.c.statuscodeid \
                    == PackageListingStatusTable.c.statuscodeid))
    })

mapper(PackageStatus, PackageStatusTable, properties={
    'packages': relation(Package, backref=backref('status')),
    'translations': relation(StatusTranslation,
        order_by=StatusTranslationTable.c.language,
        primaryjoin=StatusTranslationTable.c.statuscodeid \
                == PackageStatusTable.c.statuscodeid,
        foreign_keys=[StatusTranslationTable.c.statuscodeid]),
    'locale': relation(StatusTranslation,
        order_by=StatusTranslationTable.c.language,
        primaryjoin=StatusTranslationTable.c.statuscodeid \
                == PackageStatusTable.c.statuscodeid,
        foreign_keys=[StatusTranslationTable.c.statuscodeid],
        collection_class=attribute_mapped_collection('language'),
        backref=backref('pstatuscode',
            foreign_keys=[StatusTranslationTable.c.statuscodeid],
            primaryjoin=StatusTranslationTable.c.statuscodeid \
                    == PackageStatusTable.c.statuscodeid))
    })

mapper(PackageAclStatus, PackageAclStatusTable, properties={
    'pacls': relation(PersonPackageListingAcl,
        backref=backref('status')),
    'gacls': relation(GroupPackageListingAcl,
        backref=backref('status')),
    'translations': relation(StatusTranslation,
        order_by=StatusTranslationTable.c.language,
        primaryjoin=StatusTranslationTable.c.statuscodeid \
                == PackageAclStatusTable.c.statuscodeid,
        foreign_keys=[StatusTranslationTable.c.statuscodeid]),
    'locale': relation(StatusTranslation,
        order_by=StatusTranslationTable.c.language,
        primaryjoin=StatusTranslationTable.c.statuscodeid \
                == PackageAclStatusTable.c.statuscodeid,
        foreign_keys=[StatusTranslationTable.c.statuscodeid],
        collection_class=attribute_mapped_collection('language'),
        backref=backref('pastatuscode',
            foreign_keys=[StatusTranslationTable.c.statuscodeid],
            primaryjoin=StatusTranslationTable.c.statuscodeid \
                    == PackageAclStatusTable.c.statuscodeid))
    })
