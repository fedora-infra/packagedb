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
Mapping of collection and repo related database tables to python classes
'''

import re
import warnings
from sqlalchemy import Table, Column, Integer, Text, String
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, text
from sqlalchemy import select, not_, Boolean, PassiveDefault, func
from sqlalchemy import PrimaryKeyConstraint, DDL, Index
from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy.orm import polymorphic_union, relation, backref
from sqlalchemy.orm.collections import attribute_mapped_collection
from turbogears.database import metadata, mapper, get_engine, session

from fedora.tg.json import SABase
from pkgdb import _

from pkgdb.model.packages import PackageBuild, PackageBuildReposTable
from pkgdb.model.packages import PackageListing, PackageListingTable
from pkgdb.model import CollectionStatus
from pkgdb.lib.db import View, Grant_RW

try:
    from fedora.textutils import to_unicode
except ImportError:
    from pkgdb.lib.utils import to_unicode

get_engine()

#
# Mapped Tables
#
# Collection of packages.
# 
# Collections are a set of packages.  They can represent the packages in a
# distro, in a SIG, or on a CD.
#
# Fields:
# :name: "Fedora Core", "Fedora Extras", "Python", "GNOME" or whatever
#   names-for-groupings you want.  If this is for a grouping that a SIG is
#   interested in, the name should make this apparent.  If it is for one
#   of the distributions it should be the name for the Product that will
#   be used in Bugzilla as well.
# :version: The release of the `Collection`.  If the `Collection` doesn't
#   have releases (for instance, SIGs), version should be 0.
# :statuscode: Is the collection being worked on or is it inactive.
# :owner: Creator, QA Contact, or other account that is in charge of the
#   collection.  This is a foreign key to an account id number.  (Since the
#   accounts live in a separate db we can't have the db enforce validity.)
# :publishURLTemplate: URL to packages built for this collection with
#   [ARCH] and [PACKAGE] as special symbols that can be substituted from the
#   specific package built.
# :pendingURLTemplate: URL to packages built but not yet in the repository
#   with [ARCH] and [PACKAGE] as special symbols that can be substituted from
#   the specific package built.
# :summary: Brief description of the collection.
# :description: Longer description of the collection.
# :branchName: Name of the branch in the VCS ("FC-3", "devel")
# :distTag: DistTag used in the buildsystem (".fc3", ".fc6")
# :parent: Many collections are branches of other collections.  This field
#    records the parent collection to branch from.

# Collections and Branches have an inheritance relationship.  ie: Branches are
# just Collections that have additional data.

# :C0103: Tables and mappers are constants but SQLAlchemy/TurboGears convention
# is not to name them with all uppercase
# pylint: disable-msg=C0103
CollectionTable = Table('collection', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('name', Text(),  nullable=False),
    Column('version', Text(),  nullable=False),
    Column('statuscode', Integer(), nullable=False),
    Column('owner', Text(),  nullable=False),
    Column('publishurltemplate', Text()),
    Column('pendingurltemplate', Text()),
    Column('summary', Text()),
    Column('description', Text()),
    Column('koji_name', Text(), unique=True),
    Column('branchname', Text(), unique=True, nullable=False),
    Column('disttag', Text(),  nullable=False),
    UniqueConstraint('name', 'version', name='collection_name_key'),
    ForeignKeyConstraint(['statuscode'],['collectionstatuscode.statuscodeid'], 
        use_alter=True, name='collection_statuscode_fkey', 
        onupdate="CASCADE", ondelete="RESTRICT"),
)
Index('collection_status_idx', CollectionTable.c.statuscode)
DDL('ALTER TABLE collection CLUSTER ON collection_name_key', on='postgres')\
    .execute_at('after-create', CollectionTable)
Grant_RW(CollectionTable)


ReposTable = Table('repos', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('shortname', Text(),  nullable=False),
    Column('name', Text(),  nullable=False),
    Column('url', Text(),  nullable=False),
    Column('mirror', Text(),  nullable=False),
    Column('active', Boolean(), PassiveDefault('True'), nullable=False),
    Column('collectionid', Integer()),
    UniqueConstraint('url', name='repos_url'),
    UniqueConstraint('name', name='repos_name'),
    UniqueConstraint('shortname', name='repos_shortname'),
    ForeignKeyConstraint(['collectionid'],['collection.id'],
        ondelete="CASCADE"),
)
Grant_RW(ReposTable)


# This is view
# Show how many active `Packages` are present in each `Collection`
#
# Fields:
# :id: Id of the `Collection`.
# :name: Name of the `Collection`.
# :version: Version of the `Collection`.
# :statuscode: Code telling whether the `Collection` is active.
# :numpkgs: Number of Approved `Package`s in the `Collection`.
#
#  SELECT c.id, c.name, c.version, c.statuscode, count(*) AS numpkgs
#  FROM packagelisting pl, collection c
#  WHERE pl.collectionid = c.id AND pl.statuscode = 3
#  GROUP BY c.name, c.version, c.id, c.statuscode
#  ORDER BY c.name, c.version;
#
CollectionPackageTable = View('collectionpackage', metadata,
        select([
            CollectionTable.c.id.label('id'),
            CollectionTable.c.name.label('name'),
            CollectionTable.c.version.label('version'),
            CollectionTable.c.statuscode.label('statuscode'),
            func.count().label('numpkgs')]).\
        select_from(PackageListingTable.join(CollectionTable)).\
        where(PackageListingTable.c.statuscode==text('3')).\
        group_by(
            CollectionTable.c.name,
            CollectionTable.c.version,
            CollectionTable.c.id,
            CollectionTable.c.statuscode).
        order_by(
            CollectionTable.c.name,
            CollectionTable.c.version))
Grant_RW(CollectionPackageTable)
        

#
# Mapped Classes
#

class Collection(SABase):
    '''A Collection of packages.

    Table -- Collection
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, name, version, statuscode, owner, branchname, disttag, 
            publishurltemplate=None, pendingurltemplate=None, summary=None,
            description=None):
        # pylint: disable-msg=R0913
        super(Collection, self).__init__()
        self.name = name
        self.version = version
        self.statuscode = statuscode
        self.owner = owner
        self.publishurltemplate = publishurltemplate
        self.pendingurltemplate = pendingurltemplate
        self.summary = summary
        self.description = description
        self.branchname = branchname
        self.disttag = disttag


    @classmethod
    def unify_branchnames(cls, branchnames):
        if isinstance(branchnames, basestring):
            branchnames = [branchnames]
        if isinstance(branchnames, (tuple, list)):
            return [cls.unify_branchname(bn) for bn in branchnames]
        else:
            raise TypeError('Only arg of type str or list is supported')



    @classmethod
    def unify_branchname(cls, branchname):
        if branchname == 'devel':
            return u'master'
        else:
            return to_unicode(branchname.lower().replace('-', ''))


    @property
    def short_name(self):
        if self.branchname == 'master':
            return 'devel'
        else:
            return re.sub(r'(\d+)$', r'-\1', self.branchname.upper())

    def __repr__(self):
        return 'Collection(%r, %r, %r, %r, %r, %r, publishurltemplate=%r,' \
                ' pendingurltemplate=%r, summary=%r, description=%r)' % (
                self.name, self.version, self.statuscode, self.owner, 
                self.branchname, self.disttag,
                self.publishurltemplate, self.pendingurltemplate,
                self.summary, self.description)


class Repo(SABase):
    '''Repos are actual yum repositories.

    Table -- Repos
    '''
    def __init__(self, name, shortname, url, mirror, active, collectionid):
        super(Repo, self).__init__()
        self.name  = name
        self.shortname = shortname
        self.url = url
        self.mirror = mirror
        self.active = active
        self.collectionid = collectionid

    def __repr__(self):
        return 'Repo(%r, %r, url=%r, mirror=%r, active=%r, collectionid=%r)' % (
            self.name, self.shortname, self.url, self.mirror, self.active,
            self.collectionid)

class CollectionPackage(SABase):
    '''Information about how many `Packages` are in a `Collection`

    View -- CollectionPackage
    '''
    # pylint: disable-msg=R0902, R0903
    def __repr__(self):
        # pylint: disable-msg=E1101
        return 'CollectionPackage(id=%r, name=%r, version=%r,' \
            ' statuscode=%r, numpkgs=%r,' % (
            self.id, self.name, self.version, self.statuscode, self.numpkgs)

#
# Mappers
#

mapper(Collection, CollectionTable,
        properties={
            # listings is deprecated.  It will go away in 0.4.x
            'listings': relation(PackageListing,
                backref=backref('collection_')),
            # listings2 is slower than listings.  It has a front-end cost to
            # load the data into the dict.  However, if we're using listings
            # to search for multiple packages, this will likely be faster.
            # Have to look at how it's being used in production and decide
            # what to do.
            'listings2': relation(PackageListing,
                backref=backref('collection'),
                collection_class=attribute_mapped_collection('packagename')),
            'repos': relation(Repo, backref=backref('collection')),
            'status': relation(CollectionStatus, backref=backref('collections')),
        })


mapper(CollectionPackage, CollectionPackageTable,
        properties={
            'status': relation(CollectionStatus, backref=backref('collectionPackages')),
        })
mapper(Repo, ReposTable, properties={
    'builds': relation(PackageBuild, backref=backref('repos'),
        secondary=PackageBuildReposTable, cascade='all'),
    })
