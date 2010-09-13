# -*- coding: utf-8 -*-
#
# Copyright © 2007-2010  Red Hat, Inc.
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
#                    Martin Bacovsky <mbacovsk@redhat.com>
# Fedora Project Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#
'''
Mapping of package related database tables to python classes.

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
# :W0201: some attributes are added to the model by SQLAlchemy so they don't
#   appear in __init__
# :R0913: The __init__ methods of the mapped classes may need many arguments
#   to fill the database tables.
# :C0103: Tables and mappers are constants but SQLAlchemy/TurboGears convention
#   is not to name them with all uppercase
import logging

from sqlalchemy import Column, ForeignKeyConstraint, Integer, Table, Text
from sqlalchemy import Boolean, DateTime, func, UniqueConstraint
from sqlalchemy import text, DDL, Index
from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import backref, eagerload, relation
from sqlalchemy.orm.collections import attribute_mapped_collection,\
        mapped_collection
from sqlalchemy.sql import and_
from turbogears.database import get_engine, metadata, mapper, session

from fedora.tg.json import SABase
from pkgdb.model.acls import GroupPackageListing, GroupPackageListingAcl,\
        PersonPackageListing, PersonPackageListingAcl
from pkgdb.model.prcof import RpmConflicts, RpmFiles, RpmObsoletes,\
        RpmProvides, RpmRequires
from pkgdb.lib.db import Grant_RW

error_log = logging.getLogger('pkgdb.model.packages')

get_engine()

DEFAULT_GROUPS = {'provenpackager': {'commit': True, 'build': True,
    'checkout': True}}

#
# Tables
#

# Package and PackageListing are straightforward translations.  Look at these
# if you're looking for a straightforward example.

# :C0103: Tables and mappers are constants but SQLAlchemy/TurboGears convention
# is not to name them with all uppercase
#pylint:disable-msg=C0103
PackageTable = Table('package', metadata,
    Column('id', Integer(), primary_key=True, autoincrement=True, nullable=False),
    Column('name', Text(), nullable=False),
    Column('summary', Text(), nullable=False),
    Column('description', Text()),
    Column('reviewurl', Text()),
    Column('statuscode', Integer(), nullable=False),
    Column('shouldopen', Boolean(), nullable=False, server_default=text('true')),
    Column('upstreamurl', Text()),
    UniqueConstraint('name', name='package_name_key'),
    ForeignKeyConstraint(['statuscode'],['packagestatuscode.statuscodeid'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
)
DDL('ALTER TABLE package CLUSTER ON package_name_key', on='postgres')\
    .execute_at('after-create', PackageTable)
Grant_RW(PackageTable)


PackageListingTable = Table('packagelisting', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('packageid', Integer(), nullable=False),
    Column('collectionid', Integer(),  nullable=False),
    Column('owner', Text(),  nullable=False),
    Column('qacontact', Text()),
    Column('statuscode', Integer(),  nullable=False),
    Column('statuschange', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('specfile', Text()),
    Column('critpath', Boolean(), nullable=False, server_default=text('false')),
    ForeignKeyConstraint(['statuscode'],['packagelistingstatuscode.statuscodeid'], 
        onupdate="CASCADE", ondelete="RESTRICT"),
    ForeignKeyConstraint(['packageid'],['package.id'], 
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['collectionid'],['collection.id'], 
        onupdate="CASCADE", ondelete="CASCADE"),
    UniqueConstraint('packageid', 'collectionid',
        name='packagelisting_packageid_key')
)
Grant_RW(PackageListingTable)
Index('packagelisting_collectionid_idx', PackageListingTable.c.collectionid)
Index('packagelisting_packageid_idx', PackageListingTable.c.packageid)
Index('packagelisting_statuscode_idx', PackageListingTable.c.statuscode)
DDL('ALTER TABLE packagelisting CLUSTER ON packagelisting_packageid_idx', on='postgres')\
    .execute_at('after-create', PackageListingTable)
package_build_agreement_pgfunc = """
    CREATE OR REPLACE FUNCTION package_build_agreement() RETURNS trigger
        AS $$
    DECLARE
      pkgList_pid integer;
      pkgBuild_pid integer;
    BEGIN
      -- if (TG_TABLE_NAME = 'PackageBuildListing') then
      if (TG_RELNAME = 'packagebuildlisting') then
        -- Upon entering a new relationship between a Build and Listing, make sure
        -- they reference the same package.
        pkgList_pid := packageId from packageListing where id = NEW.packageListingId;
        pkgBuild_pid := packageId from packageBuild where id = NEW.packageBuildId;
        if (pkgList_pid != pkgBuild_pid) then
          raise exception 'PackageBuild %% and PackageListing %% have to reference the same package', NEW.packageBuildId, NEW.packageListingId;
        end if;
      -- elsif (TG_TABLE_NAME = 'PackageBuild') then
      elsif (TG_RELNAME = 'packagebuild') then
        -- Disallow updating the packageId field of PackageBuild if it is
        -- associated with a PackageListing
        if (NEW.packageId != OLD.packageId) then
          select * from PackageBuildListing where PackageBuildId = NEW.id;
          if (FOUND) then
            raise exception 'Cannot update packageId when PackageBuild is referenced by a PackageListing';
          end if;
        end if;
      -- elsif (TG_TABLE_NAME = 'PackageListing') then
      elsif (TG_RELNAME = 'packagelisting') then
        -- Disallow updating the packageId field of PackageListing if it is
        -- associated with a PackageBuild
        if (NEW.packageId != OLD.packageId) then
          select * from PackageBuildListing where PackageListingId = NEW.id;
          if (FOUND) then
            raise exception 'Cannot update packageId when PackageListing is referenced by a PackageBuild';
          end if;
        end if;
      else
        -- raise exception 'Triggering table %% is not one of PackageBuild, PackageListing, or PackageBuildListing', TG_TABLE_NAME;
        raise exception 'Triggering table %% is not one of PackageBuild, PackageListing, or PackageBuildListing', TG_RELNAME;
      end if;
      return NEW;
    END;
    $$
        LANGUAGE plpgsql;
    """
DDL(package_build_agreement_pgfunc, on='postgres')\
    .execute_at('before-create', PackageListingTable)
# DROP is not necessary as we drop plpgsql with CASCADE
DDL('CREATE TRIGGER package_build_agreement_trigger BEFORE UPDATE ON packagelisting'\
        ' FOR EACH ROW EXECUTE PROCEDURE package_build_agreement()', on='postgres')\
    .execute_at('after-create', PackageListingTable)

packgelisting_statuschange_pgfunc = """
    CREATE OR REPLACE FUNCTION packagelisting_statuschange() RETURNS trigger
        AS $$
        BEGIN
            -- Check that the status changed --
            IF NEW.statuscode IS DISTINCT FROM OLD.statuscode THEN
                NEW.statuschange := current_timestamp;
            END IF;

            RETURN NEW;
        END;
    $$
        LANGUAGE plpgsql;
    """
DDL(packgelisting_statuschange_pgfunc, on='postgres')\
    .execute_at('before-create', PackageListingTable)
# DROP is not necessary as we drop plpgsql with CASCADE
DDL('CREATE TRIGGER packagelisting_statuschange BEFORE UPDATE ON packagelisting'\
        ' FOR EACH ROW EXECUTE PROCEDURE packagelisting_statuschange()', on='postgres')\
    .execute_at('after-create', PackageListingTable)



BinaryPackagesTable = Table('binarypackages', metadata,
    Column('name', Text,  nullable=False, primary_key=True),
    useexisting=True
)
Grant_RW(BinaryPackagesTable)


PackageBuildTable = Table('packagebuild', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('packageid', Integer(), nullable=False),
    Column('epoch', Text()),
    Column('version', Text(),  nullable=False),
    Column('release', Text(),  nullable=False),
    Column('name', Text(),  nullable=False),
    Column('license', Text(),  nullable=False),
    Column('architecture', Text(),  nullable=False),
    Column('size', Integer(),  nullable=False),
    Column('changelog', Text(),  nullable=False),
    Column('committime', DateTime(timezone=True),  nullable=False),
    Column('committer', Text(),  nullable=False),
    Column('imported', DateTime(timezone=True), server_default=func.now(), nullable=False),
    ForeignKeyConstraint(['name'],['binarypackages.name']),
    ForeignKeyConstraint(['packageid'],['package.id'], 
        onupdate='CASCADE', ondelete='RESTRICT'),
)
Grant_RW(PackageBuildTable)
DDL(package_build_agreement_pgfunc, on='postgres')\
    .execute_at('before-create', PackageBuildTable)
# DROP is not necessary as we drop plpgsql with CASCADE
DDL('CREATE TRIGGER package_build_agreement_trigger BEFORE UPDATE ON packagebuild'\
        ' FOR EACH ROW EXECUTE PROCEDURE package_build_agreement()', on='postgres')\
    .execute_at('after-create', PackageBuildTable)


PackageBuildDependsTable = Table('packagebuilddepends', metadata,
    Column('packagebuildid', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('packagebuildname', Text(),  primary_key=True, nullable=False),
    ForeignKeyConstraint(['packagebuildid'], ['packagebuild.id'], ondelete="CASCADE"),
)
Grant_RW(PackageBuildDependsTable)


PackageBuildReposTable = Table('packagebuildrepos', metadata,
    Column('repoid', Integer, primary_key=True, autoincrement=False, nullable=False),
    Column('packagebuildid', Integer, primary_key=True, autoincrement=False, nullable=False),
    ForeignKeyConstraint(['repoid'], ['repos.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['packagebuildid'], ['packagebuild.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)
Grant_RW(PackageBuildReposTable)
remove_orphaned_builds_pgfunc = """
    CREATE OR REPLACE FUNCTION remove_orphaned_builds() RETURNS trigger
        AS $$
        BEGIN
            DELETE FROM packagebuild USING (
                SELECT OLD.packagebuildid as id, count(*) as count
                FROM packagebuildrepos p
                WHERE p.packagebuildid = OLD.packagebuildid
            ) pbr
            WHERE pbr.id = packagebuild.id AND pbr.count = 0;

            RETURN OLD;
        END;
    $$
        LANGUAGE plpgsql;

    """
DDL(remove_orphaned_builds_pgfunc, on='postgres')\
    .execute_at('before-create', PackageBuildReposTable)
# DROP is not necessary as we drop plpgsql with CASCADE
# FIXME: This trigger is created just in postgres. If it is needed in other DB
# (in sqlite for testing) it has to be added manually
DDL('CREATE TRIGGER remove_orphaned_builds AFTER DELETE ON packagebuildrepos '\
        ' FOR EACH ROW EXECUTE PROCEDURE remove_orphaned_builds()', on='postgres')\
    .execute_at('after-create', PackageBuildReposTable)


#pylint:enable-msg=C0103
#
# Mapped Classes
#

class Package(SABase):
    '''Software we are packaging.

    This is equal to the software in one of our revision control directories.
    It is unversioned and not associated with a particular collection.

    Table -- Package
    '''
    def __init__(self, name, summary, statuscode, description=None,
            reviewurl=None, shouldopen=None, upstreamurl=None):
        #pylint:disable-msg=R0913
        super(Package, self).__init__()
        self.name = name
        self.summary = summary
        self.statuscode = statuscode
        self.description = description
        self.reviewurl = reviewurl
        self.shouldopen = shouldopen
        self.upstreamurl = upstreamurl

    def __repr__(self):
        return 'Package(%r, %r, %r, description=%r, ' \
               'upstreamurl=%r, reviewurl=%r, shouldopen=%r)' % (
                self.name, self.summary, self.statuscode, self.description,
                self.upstreamurl, self.reviewurl, self.shouldopen)

    def create_listing(self, collection, owner, statusname,
            qacontact=None, author_name=None):
        '''Create a new PackageListing branch on this Package.

        :arg collection: Collection that the new PackageListing lives on
        :arg owner: The owner of the PackageListing
        :arg statusname: Status to set the PackageListing to
        :kwarg qacontact: QAContact for this PackageListing in bugzilla.
        :kwarg author_name: Author of the change.  Note: will remove when
            logging is made generic
        :returns: The new PackageListing object.

        This creates a new PackageListing for this Package.  The PackageListing
        has default values set for group acls.
        '''
        from pkgdb.lib.utils import STATUS
        from pkgdb.model.logs import PackageListingLog
        pkg_listing = PackageListing(owner, STATUS[statusname],
                collectionid=collection.id,
                qacontact=qacontact)
        pkg_listing.packageid = self.id
        for group in DEFAULT_GROUPS:
            new_group = GroupPackageListing(group)
            #pylint:disable-msg=E1101
            pkg_listing.groups2[group] = new_group
            #pylint:enable-msg=E1101
            for acl, status in DEFAULT_GROUPS[group].iteritems():
                if status:
                    acl_statuscode = STATUS['Approved']
                else:
                    acl_statuscode = STATUS['Denied']
                group_acl = GroupPackageListingAcl(acl, acl_statuscode)
                # :W0201: grouppackagelisting is added to the model by
                #   SQLAlchemy so it doesn't appear in __init__
                #pylint:disable-msg=W0201
                group_acl.grouppackagelisting = new_group
                #pylint:enable-msg=W0201

        # Create a log message
        log = PackageListingLog(author_name, STATUS['Added'],
                '%(user)s added a %(branch)s to %(pkg)s' %
                {'user': author_name, 'branch': collection,
                    'pkg': self.name})
        log.listing = pkg_listing

        return pkg_listing


class BinaryPackage(SABase):

    def __init__(self, name):
        super(BinaryPackage, self).__init__()
        self.name = name


    def __repr__(self):
        return 'BinaryPackage(%r)' % self.name



class PackageListing(SABase):
    '''This associates a package with a particular collection.

    Table -- PackageListing
    '''
    def __init__(self, owner, statuscode, packageid=None, collectionid=None,
            qacontact=None, specfile=None):
        #pylint:disable-msg=R0913
        super(PackageListing, self).__init__()
        self.packageid = packageid
        self.collectionid = collectionid
        self.owner = owner
        self.qacontact = qacontact
        self.statuscode = statuscode
        self.specfile = specfile

    packagename = association_proxy('package', 'name')

    def __repr__(self):
        return 'PackageListing(%r, %r, packageid=%r, collectionid=%r,' \
               ' qacontact=%r, specfile=%r)' % (self.owner, self.statuscode,
                        self.packageid, self.collectionid, self.qacontact,
                        self.specfile)

    def clone(self, branch, author_name):
        '''Clone the permissions on this PackageListing to another `Branch`.

        :arg branch: `branchname` to make a new clone for
        :arg author_name: Author of the change.  Note, will remove when logs
            are made generic
        :raises sqlalchemy.exceptions.InvalidRequestError: when a request
            does something that violates the SQL integrity of the database
            somehow.
        :returns: new branch
        :rtype: PackageListing
        '''
        from pkgdb.model.collections import Branch
        from pkgdb.model.logs import GroupPackageListingAclLog, \
                PersonPackageListingAclLog
        # Retrieve the PackageListing for the to clone branch
        try:
            #pylint:disable-msg=E1101
            clone_branch = PackageListing.query.join('package'
                    ).join('collection').filter(
                        and_(Package.name==self.package.name,
                            Branch.branchname==branch)).one()
            #pylint:enable-msg=E1101
        except InvalidRequestError:
            ### Create a new package listing for this release ###

            # Retrieve the collection to make the branch for
            #pylint:disable-msg=E1101
            clone_collection = Branch.query.filter_by(branchname=branch).one()
            #pylint:enable-msg=E1101
            # Create the new PackageListing
            clone_branch = self.package.create_listing(clone_collection,
                    self.owner, 'Approved', qacontact=self.qacontact,
                    author_name=author_name)

        log_params = {'user': author_name,
                'pkg': self.package.name, 'branch': branch}
        # Iterate through the acls in the master_branch
        #pylint:disable-msg=E1101
        for group_name, group in self.groups2.iteritems():
        #pylint:enable-msg=E1101
            log_params['group'] = group_name
            if group_name not in clone_branch.groups2:
                # Associate the group with the packagelisting
                #pylint:disable-msg=E1101
                clone_branch.groups2[group_name] = \
                        GroupPackageListing(group_name)
                #pylint:enable-msg=E1101
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
                log = GroupPackageListingAclLog(author_name,
                        acl.statuscode, log_msg)
                log.acl = clone_group.acls2[acl_name]

        #pylint:disable-msg=E1101
        for person_name, person in self.people2.iteritems():
        #pylint:enable-msg=E1101
            log_params['person'] = person_name
            if person_name not in clone_branch.people2:
                # Associate the person with the packagelisting
                #pylint:disable-msg=E1101
                clone_branch.people2[person_name] = \
                        PersonPackageListing(person_name)
                #pylint:enable-msg=E1101
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
                log = PersonPackageListingAclLog(author_name,
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
    return pkg_listing.collection.simple_name

class PackageBuildDepends(SABase):
    '''PackageBuild Dependencies to one another.

    Table(junction) -- PackageBuildDepends
    '''
    def __init__(self, packagebuildname, packagebuildid=None):
        super(PackageBuildDepends, self).__init__()
        self.packagebuildid = packagebuildid
        self.packagebuildname = packagebuildname

    def __repr__(self):
        return 'PackageBuildDepends(%r, %r)' % (
            self.packagebuildid, self.packagebuildname)


class PackageBuildRepo(SABase):
    '''PackageBuild Repo association.

    Table -- PackageBuildRepo
    '''
    def __init__(self, packagebuildid, repoid):
        super(PackageBuildRepo, self).__init__()
        self.packagebuildid = packagebuildid
        self.repoid = repoid

    def __repr__(self):
        return 'PackageBuildRepo(%r, %r)' % (
            self.packagebuildid, self.repoid)



class PackageBuild(SABase):
    '''Package Builds - Actual rpms

    This is a very specific unitary package with version, release and everything.

    Table -- PackageBuild
    '''
    def __init__(self, name, packageid, epoch, version, release, architecture,
                 size, license, changelog, committime, committer):
        super(PackageBuild, self).__init__()
        self.name = name
        self.packageid = packageid
        self.epoch = epoch
        self.version = version
        self.release = release
        self.architecture = architecture
        self.size = size
        self.license = license
        self.changelog = changelog
        self.committime = committime
        self.committer = committer

    repo = property(lambda self:self.repos[0])

    def __repr__(self):
        return 'PackageBuild(%r, epoch=%r, version=%r,' \
               ' release=%r, architecture=%r, size=%r, license=%r,' \
               ' changelog=%r, committime=%r, committer=%r, packageid=%r,' \
               ' repoid=%r, imported=%r)' % (
            self.name, self.epoch, self.version,
            self.release, self.architecture, self.size,
            self.license, self.changelog, self.committime, self.committer,
            self.packageid, self.repo.id, self.imported)

    def __str__(self):
        return "%s-%s-%s.%s" % (self.name, self.version,
                self.release, self.architecture)


    def download_path(self, reponame=None):
        """Find download path of the build

        :args reponame: prefered repo from where the build should be downloaded
        :returns: URI of the build

        Find download URI of the build. If build is available in <reponame> repo,
        path to that repo is used. Path to first available repo is returned otherwise.
        """

        repo = self.repo # default

        #find repo
        for r in self.repos:
            if r.shortname == reponame:
                repo = r
                break

        # format path
        return "%s%s%s%s.rpm" % (repo.mirror, repo.url,
                ('','Packages/')[repo.url.endswith('os/')], self)


    def scores(self):
        '''Return a dictionary of tagname: score for a given packegebuild
        '''

        scores = {}
        for app in self.applications: #pylint:disable-msg=E1101
            tags = app.scores
            for tag, score in tags.iteritems():
                sc = scores.get(tag, None)
                if sc is None or sc < score:
                    scores[tag] = score

        return scores


    @classmethod
    def most_fresh(self, limit=5):
        """Query that returns last pkgbuild imports

        :arg limit: top <limit> apps

        Excerpt from changelog is returned as well
        """
        #pylint:disable-msg=E1101
        fresh = session.query(PackageBuild)\
                .options(eagerload(PackageBuild.repos))\
                .order_by(PackageBuild.committime.desc())
        #pylint:enable-msg=E1101
        if limit > 0:
            fresh = fresh.limit(limit)
        return fresh

#
# Mappers
#

mapper(Package, PackageTable, properties={
    # listings is here for compatibility.  Will be removed in 0.4.x
    'listings': relation(PackageListing),
    'listings2': relation(PackageListing,
        backref=backref('package'),
        collection_class=mapped_collection(collection_alias)),
    'builds': relation(PackageBuild,
        backref=backref('package'),
        collection_class=attribute_mapped_collection('name'))
    })

mapper(PackageListing, PackageListingTable, properties={
    'people': relation(PersonPackageListing),
    'people2': relation(PersonPackageListing, backref=backref('packagelisting'),
        collection_class = attribute_mapped_collection('username')),
    'groups': relation(GroupPackageListing),
    'groups2': relation(GroupPackageListing, backref=backref('packagelisting'),
        collection_class = attribute_mapped_collection('groupname')),
    })

mapper(PackageBuildDepends, PackageBuildDependsTable)

mapper(PackageBuildRepo, PackageBuildReposTable)

mapper(PackageBuild, PackageBuildTable, properties={
    'conflicts': relation(RpmConflicts, backref=backref('build'),
        collection_class = attribute_mapped_collection('name'),
        cascade='all, delete-orphan'),
    'requires': relation(RpmRequires, backref=backref('build'),
        collection_class = attribute_mapped_collection('name'),
        cascade='all, delete-orphan'),
    'provides': relation(RpmProvides, backref=backref('build'),
        collection_class = attribute_mapped_collection('name'),
        cascade='all, delete-orphan'),
    'obsoletes': relation(RpmObsoletes, backref=backref('build'),
        collection_class = attribute_mapped_collection('name'),
        cascade='all, delete-orphan'),
    'files': relation(RpmFiles, backref=backref('build'),
        collection_class = attribute_mapped_collection('name'),
        cascade='all, delete-orphan'),
    'depends': relation(PackageBuildDepends, backref=backref('build'),
        collection_class = attribute_mapped_collection('packagebuildname'),
        cascade='all, delete-orphan'),
    })


mapper(BinaryPackage, BinaryPackagesTable,
    properties={
        'packagebuilds': relation(PackageBuild, cascade='all'),
    })


