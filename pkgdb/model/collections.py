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

from sqlalchemy import Table, Column, Integer, Text, String
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, text
from sqlalchemy import select, not_, Boolean, PassiveDefault, func
from sqlalchemy import PrimaryKeyConstraint, DDL, Index
from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy.orm import polymorphic_union, relation, backref
from sqlalchemy.orm.collections import attribute_mapped_collection
from turbogears.database import metadata, mapper, get_engine

from fedora.tg.json import SABase

from pkgdb.model.packages import PackageBuild, PackageBuildReposTable
from pkgdb.model.packages import PackageListing, PackageListingTable
from pkgdb.model import CollectionStatus
from pkgdb.lib.db import View, Grant_RW

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
    UniqueConstraint('name', 'version', name='collection_name_key'),
    ForeignKeyConstraint(['statuscode'],['collectionstatuscode.statuscodeid'], 
        use_alter=True, name='collection_statuscode_fkey', 
        onupdate="CASCADE", ondelete="RESTRICT"),
)
Index('collection_status_idx', CollectionTable.c.statuscode)
DDL('ALTER TABLE collection CLUSTER ON collection_name_key', on='postgres')\
    .execute_at('after-create', CollectionTable)
Grant_RW(CollectionTable)


# Associate the packages in one collection with another collection.
#
# This table is used to allow one `Collection` to be based on another with
# certain packages that are overridden or not available in the `base`
# `Collection`.  For instance, a `Collection` may be used to experiment with
# a major version upgrade of python and all the dependent packages that need
# to be rebuilt against it.  In this scenario, the base might be
# "Fedora Core - devel".  The overlay "FC devel python3".  The overlay will
# contain python packages that override what is present in the base.  Any
# package that is not present in the overlay will also be searched for in
# the base collection.
# Once we're ready to commit to using the upgraded set of packages, we want
# to merge them into devel.  To do this, we will actually move the packages
# from the overlay into the base collection.  Probably, at this time, we
# will also mark the overlay as obsolete.
#
# Keeping things consistent is a bit problematic because we have to search for
# for packages in the collection plus all the bases (an overlay can have
# multiple bases) and any bases that they're overlays for.  SQL doesn't do
# recursion -- in and of itself so we have to work around it in one of these
# ways:
# 1) Do the searching for packages in code; either a trigger on the server or
#    in any application code which looks at the database.
# 2) Use a check constraint to only have one level of super/subset.  So if
#    devel contains python-2.5, devel cannot be a subset and python-2.5 cannot
#    be a superset to any other collection.  Have an insert trigger that
#    checks for this.
# 3) Copy the packages.  When we make one collection a subset of another, add
#    all its packages including subset's packages to the superset.  Have an
#    insert trigger on packageList and packageListVer that check whether this
#    collection is a subset and copies the package to other collections.
# Option 1, in application code may be the simplest to implement.  However,
# option 3 has the benefit of running during insert rather than select.  As
# always, doing something within the database rather than application logic
# allows us to keep better control over the information.
#
# * Note: Do not have an ondelete trigger as there may be overlap between the
# packages in the parent and child collection.
#
# Fields:
# :overlay: The `Collection` which overrides packages in the base.
# :base: The `Collection` which provides packages not explicitly listed in
#    `overlay`.
# :priority: When searching for a package within a collection, first check the
#    `overlay`.  If not found check the lowest priority `base` collection and
#    any `base` Collections that belong to it.  Then check the next lowest
#    priority `base` until we find the package or run out. `base`s of the same
#    `overlay` with the same `priority` are searched in an undefined order.
CollectionSetTable = Table('collectionset', metadata,
    Column('overlay', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('base', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('priority', Integer(), PassiveDefault(text('0'))),
    ForeignKeyConstraint(['overlay'],['collection.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['base'],['collection.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)
Grant_RW(CollectionSetTable)


# `Collection`s with their own branch in the VCS have extra information.
#
# Fields:
# :collectionId: `Collection` this branch provides information for.
# :branchName: Name of the branch in the VCS ("FC-3", "devel")
# :distTag: DistTag used in the buildsystem (".fc3", ".fc6")
# :parent: Many collections are branches of other collections.  This field
#    records the parent collection to branch from.
BranchTable = Table('branch', metadata,
    Column('collectionid', Integer(), autoincrement=False, nullable=False),
    Column('branchname', String(32), unique=True, nullable=False),
    Column('gitbranchname', Text(), nullable=False),
    Column('disttag', String(32),  nullable=False),
    Column('parentid', Integer()),
    PrimaryKeyConstraint('collectionid', name='branch_pkey'),
    ForeignKeyConstraint(['collectionid'],['collection.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['parentid'],['collection.id'],
        onupdate="CASCADE", ondelete="SET NULL"),
)
DDL('ALTER TABLE branch CLUSTER ON branch_pkey', on='postgres')\
    .execute_at('after-create', BranchTable)
Grant_RW(BranchTable)    


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


CollectionJoin = polymorphic_union (
        {'b' : select((CollectionTable.join(
            BranchTable, CollectionTable.c.id == BranchTable.c.collectionid),)),
         'c' : select((CollectionTable,),
             not_(CollectionTable.c.id.in_(select(
                 (CollectionTable.c.id,),
                 CollectionTable.c.id == BranchTable.c.collectionid)
             )))
         },
        'kind', 'CollectionJoin'
        )



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
    def __init__(self, name, version, statuscode, owner,
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

    def __repr__(self):
        return 'Collection(%r, %r, %r, %r, publishurltemplate=%r,' \
                ' pendingurltemplate=%r, summary=%r, description=%r)' % (
                self.name, self.version, self.statuscode, self.owner,
                self.publishurltemplate, self.pendingurltemplate,
                self.summary, self.description)

    @property
    def simple_name(self):
        '''Return a simple name for the Collection
        '''
        try:
            # :E1101: If Collection is actually a branch, it will have a
            # branchname attribute given it by SQLAlchemy
            # pylint: disable-msg=E1101
            simple_name = self.branchname
        except AttributeError:
            simple_name = '-'.join((self.name, self.version))
        return simple_name

    @classmethod
    def by_simple_name(cls, simple_name):
        '''Return the Collection that matches the simple name

        :arg simple_name: simple name for a Collection
        :returns: The Collection that matches the name
        :raises sqlalchemy.InvalidRequestError: if the simple name is not found

        simple_name will be looked up first as the Branch name.  Then as the
        Collection name joined by a hyphen with the version.  ie:
        'Fedora EPEL-5'.
        '''
        # :E1101: SQLAlchemy adds many methods to the Branch and Collection
        # classes
        # pylint: disable-msg=E1101
        try:
            collection = Branch.query.filter_by(branchname=simple_name).one()
        except InvalidRequestError:
            name, version = simple_name.rsplit('-')
            collection = Collection.query.filter_by(name=name,
                    version=version).one()
        return collection

class Branch(Collection):
    '''Collection that has a physical existence.

    Some Collections are only present as a name and collection of packages.  The
    Collections that have a branch record are also present in our VCS and
    download repositories.

    Table -- Branch
    '''
    # pylint: disable-msg=R0902, R0903
    def __init__(self, branchname, disttag, parentid,
                 gitbranchname=None, *args):
        # pylint: disable-msg=R0913
        branch_mapping = {'F-13': 'f13', 'F-12': 'f12', 'F-11': 'f11',
                          'F-10': 'f10', 'F-9': 'f9', 'F-8': 'f8',
                          'F-7': 'f7', 'FC-6': 'fc6', 'EL-6': 'el6',
                          'EL-5': 'el5', 'EL-4':'el4', 'OLPC-3': 'olpc3'}

        super(Branch, self).__init__(*args)
        self.branchname = branchname
        self.disttag = disttag
        self.parentid = parentid

        if (not gitbranchname):
            if (branchname in branch_mapping):
                self.gitbranchname = branch_mapping[branchname]

    def __repr__(self):
        # pylint: disable-msg=E1101
        return 'Branch(%r, %r, %r, %r, %r, %r, %r, %r,' \
                ' publishurltemplate=%r, pendingurltemplate=%r,' \
                ' summary=%r, description=%r, gitbranchname=%r)' % \
                (self.collectionid, self.branchname, self.disttag,
                 self.parentid, self.name, self.version, self.statuscode,
                 self.owner, self.publishurltemplate, self.pendingurltemplate,
                 self.summary, self.description, self.gitbranchname)

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
        polymorphic_on=CollectionJoin.c.kind,
        polymorphic_identity='c',
        with_polymorphic=('*', CollectionJoin),
        properties={
            # listings is deprecated.  It will go away in 0.4.x
            'listings': relation(PackageListing),
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

mapper(Branch, BranchTable, inherits=Collection,
        inherit_condition=CollectionJoin.c.id==BranchTable.c.collectionid,
        inherit_foreign_keys=ForeignKeyConstraint(['collectionid'], ['collection.id']),
        polymorphic_identity='b',
        )

mapper(CollectionPackage, CollectionPackageTable,
        properties={
            'status': relation(CollectionStatus, backref=backref('collectionPackages')),
        })
mapper(Repo, ReposTable, properties={
    'builds': relation(PackageBuild, backref=backref('repos'),
        secondary=PackageBuildReposTable, cascade='all'),
    })
