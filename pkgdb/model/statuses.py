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
Mapping of database tables related to Statuses to python classes
'''

from sqlalchemy import Table
from sqlalchemy.orm import relation, backref
from sqlalchemy.orm.collections import attribute_mapped_collection
from turbogears.database import metadata, mapper, get_engine

from fedora.tg.json import SABase

from pkgdb.model.packages import Package, PackageListing
from pkgdb.model.collections import CollectionPackage, Collection
from pkgdb.model.acls import PersonPackageListingAcl, GroupPackageListingAcl

get_engine()

#
# Mapped Tables
#

# These are a bit convoluted as we have a 1:1:N relation between
# SpecificStatusTable:StatusCodeTable:StatusTranslationTable

# I'd like to merely override the pylint regex for this particular section of
# code as # these variables are special.  They chould be treated more like
# class definitions than constants.  Oh well.
# pylint: disable-msg=C0103
StatusTranslationTable = Table('statuscodetranslation', metadata, autoload=True)

CollectionStatusTable = Table('collectionstatuscode', metadata, autoload=True)

# Package Listing Status Table.  Like the other status tables, this one has to
# connect translations to the statuses particular to the PackageListing.  This
# make it somewhat more convoluted but all the status tables follow the same
# pattern.
PackageListingStatusTable = Table('packagelistingstatuscode', metadata,
        autoload=True)

# Package Status Table.
PackageStatusTable = Table('packagestatuscode', metadata, autoload=True)

# Package Acl Status Table
PackageAclStatusTable = Table('packageaclstatuscode', metadata, autoload=True)


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
    'collections': relation(Collection, backref=backref('status')),
    'collectionPackages': relation(CollectionPackage,
        backref=backref('status')),
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
            foreign_keys=[CollectionStatusTable.c.statuscodeid],
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
            foreign_keys=[PackageListingStatusTable.c.statuscodeid],
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
            foreign_keys=[PackageStatusTable.c.statuscodeid],
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
            foreign_keys=[PackageAclStatusTable.c.statuscodeid],
            primaryjoin=StatusTranslationTable.c.statuscodeid \
                    == PackageAclStatusTable.c.statuscodeid))
    })
