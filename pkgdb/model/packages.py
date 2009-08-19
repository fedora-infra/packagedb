# -*- coding: utf-8 -*-
#
# Copyright © 2007-2009  Red Hat, Inc. All rights reserved.
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
# :R0903: Mapped classes will have few methods as SQLAlchemy will monkey patch
#   more methods in later.
# :R0913: The __init__ methods of the mapped classes may need many arguments
#   to fill the database tables.

from sqlalchemy import Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relation, backref
from sqlalchemy.orm.collections import mapped_collection, \
        attribute_mapped_collection
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy.sql import and_, or_

from turbogears.database import metadata, mapper, get_engine, session

from fedora.tg.json import SABase

from pkgdb.model.acls import PersonPackageListing, PersonPackageListingAcl, \
        GroupPackageListing, GroupPackageListingAcl
from pkgdb.model.prcof import RpmProvides, RpmConflicts, RpmRequires, \
        RpmObsoletes, RpmFiles
from pkgdb.model.tags import Tag, TagsTable
from pkgdb.model.languages import Language
from pkgdb.model.comments import Comment, CommentsTable

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
# pylint: disable-msg=C0103
PackageTable = Table('package', metadata, autoload=True)
PackageListingTable = Table('packagelisting', metadata, autoload=True)
PackageBuildTable = Table('packagebuild', metadata, autoload=True)
PackageBuildNamesTable = Table('packagebuildnames', metadata, autoload=True)
PackageBuildDependsTable = Table('packagebuilddepends', metadata, autoload=True)

# association tables (many-to-many relationships)
PackageBuildListingTable = Table('packagebuildlisting', metadata,
        Column('packagelistingid', Integer, ForeignKey('packagelisting.id')),
        Column('packagebuildid', Integer, ForeignKey('packagebuild.id'))
        )
PackageBuildNamesTagsTable = Table('packagebuildnamestags', metadata,
        Column('packagebuildname', String,
               ForeignKey('packagebuildnames.name'), primary_key=True),
        Column('tagid', Integer, ForeignKey('tags.id'), primary_key=True),
        Column('score', Integer)
        )
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
            reviewurl=None, shouldopen=None, upstreamurl=None):
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

    def create_listing(self, collection, owner, status,
            qacontact=None, author_name=None):
        '''Create a new PackageListing branch on this Package.

        :arg collection: Collection that the new PackageListing lives on
        :arg owner: The owner of the PackageListing
        :arg status: Status to set the PackageListing to
        :kwarg qacontact: QAContact for this PackageListing in bugzilla.
        :kwarg author_name: Author of the change.  Note: will remove when
            logging is made generic
        :returns: The new PackageListing object.

        This creates a new PackageListing for this Package.  The PackageListing
        has default values set for group acls.
        '''
        # pylint: disable-msg=E1101
        from pkgdb.utils import STATUS
        from pkgdb.model.logs import PackageListingLog
        pkg_listing = PackageListing(owner, status.statuscodeid,
                collectionid=collection.id,
                qacontact=qacontact)
        pkg_listing.package = self
        for group in DEFAULT_GROUPS:
            new_group = GroupPackageListing(group)
            pkg_listing.groups2[group] = new_group
            for acl, status in DEFAULT_GROUPS[group].iteritems():
                if status:
                    acl_status = STATUS['Approved'].statuscodeid
                else:
                    acl_status = STATUS['Denied'].statuscodeid
                group_acl = GroupPackageListingAcl(acl, acl_status)
                # :W0201: grouppackagelisting is added to the model by
                #   SQLAlchemy so it doesn't appear in __init__
                # pylint: disable-msg=W0201
                group_acl.grouppackagelisting = new_group
                # pylint: enable-msg=W0201

        # Create a log message
        log = PackageListingLog(author_name,
                STATUS['Added'].statuscodeid,
                '%(user)s added a %(branch)s to %(pkg)s' %
                {'user': author_name, 'branch': collection,
                    'pkg': self.name})
        log.listing = pkg_listing

        return pkg_listing

class PackageListing(SABase):
    '''This associates a package with a particular collection.

    Table -- PackageListing
    '''
    # pylint: disable-msg=R0903
    def __init__(self, owner, statuscode, packageid=None, collectionid=None,
            qacontact=None, specfile=None):
        # pylint: disable-msg=R0913
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
        from pkgdb.utils import STATUS
        from pkgdb.model.collections import Branch
        from pkgdb.model.logs import GroupPackageListingAclLog, \
                PersonPackageListingAclLog
        # Retrieve the PackageListing for the to clone branch
        try:
            clone_branch = PackageListing.query.join('package'
                    ).join('collection').filter(
                        and_(Package.name==self.package.name,
                            Branch.branchname==branch)).one()
        except InvalidRequestError:
            ### Create a new package listing for this release ###

            # Retrieve the collection to make the branch for
            clone_collection = Branch.query.filter_by(branchname=branch).one()
            # Create the new PackageListing
            clone_branch = self.package.create_listing(clone_collection,
                    self.owner, STATUS['Approved'], qacontact=self.qacontact,
                    author_name=author_name)

        log_params = {'user': author_name,
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
                log = GroupPackageListingAclLog(author_name,
                        acl.statuscode, log_msg)
                log.acl = clone_group.acls2[acl_name]

        for person_name, person in self.people2.iteritems():
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
    return pkg_listing.collection.simple_name()

class PackageBuildDepends(SABase):
    '''PackageBuild Dependencies to one another.

    Table(junction) -- PackageBuildDepends
    '''
    def __init__(self, packagebuildid, packagebuildname):
        super(PackageBuildDepends, self).__init()
        self.packagebuildid = packagebuildid
        self.packagebuildname = packagebuildname

    def __repr__(self):
        return 'PackageBuildDepends(%r, %r)' % (
            self.packagebuildid, self.packagebuildname)

class PackageBuildName(SABase):
    '''Package Build Names

    We use this mainly to have something more generic to tie tags and comments
    to instead of packagebuildid.
    '''
    def __init__(self, name):
        super(PackageBuildName, self).__init__()
        self.name = name
    def __repr__(self):
        return 'PackageBuildName(%r)' % self.name
    
class PackageBuild(SABase):
    '''Package Builds - Actual rpms

    This is a very specific unitary package with version, release and everything.

    Table -- PackageBuild
    '''
    def __init__(self, packageid, epoch, version, release, architecture,
                 desktop, size, license, changelog, committime, committer,
                 repoid):
        super(PackageBuild, self).__init__()
        self.packageid = packageid
        self.epoch = epoch
        self.version = version
        self.release = release
        self.architecture = architecture
        self.desktop = desktop
        self.size = size
        self.license = license
        self.changelog = changelog
        self.committime = committime
        self.committer = committer
        self.repoid = repoid

    def __repr__(self):
        return 'PackageBuild(%r, packageid=%r, epoch=%r, version=%r,' \
               ' release=%r, architecture=%r, desktop=%r, size=%r, license=%r,' \
               ' changelog=%r, committime=%r, committer=%r, repoid=%r)' % (
            self.name, self.packageid, self.epoch, self.version,
            self.release, self.architecture, self.desktop, self.size,
            self.license, self.changelog, self.committime, self.committer,
            self.repoid)
    
    @classmethod
    def tag(cls, builds, tags, language):
        '''Add a set of tags to a list of PackageBuilds.

        This method will tag all packagebuilds with matching name. 
        
        :arg builds: one or more PackageBuild names to add the tags to.
        :arg tags: one or more tags to add to the packages.
        :arg language: name or shortname for the language of the tags.

        Returns two lists (unchanged): tags and builds.
        '''
        lang = Language.find(language)

        # if we got just one argument, make it a list
        if tags.__class__ != [].__class__:
            if tags == '':
                raise Exception('Tag name missing.')
            tags = [tags]
        if builds.__class__ != [].__class__:
            builds = [builds]

        buildnames = PackageBuildName.query.filter(
            PackageBuildName.name.in_(builds))
        for tag in tags:
            # If the tag doesn't exist already, insert it
            try:
                conn = TagsTable.select(and_(
                    TagsTable.c.name==tag, TagsTable.c.language==lang
                    )).execute()
                tagid = conn.fetchone()[0]
                conn.close()
            except:
                tagid = TagsTable.insert().values(name=tag, language=lang
                    ).execute().last_inserted_ids()[-1]

            for build in buildnames:
                # the db knows to increment the score if the
                # packageid - tagid pair is already there.
                PackageBuildNamesTagsTable.insert().values(
                    packagebuildname=build.name, tagid=tagid).execute()
        
    @classmethod
    def search(cls, tags, operator, language):
        '''Retrieve all the builds which have a specified set of tags.

        Can also be used with just one tag.

        :arg tags: One or more tag names to lookup
        :arg operator: Can be one of 'OR' and 'AND', case insensitive, decides
        how the search for tags is done.
        :arg language: A language in short ('en_US') or long ('American English')
        format. Look for them on https://translate.fedoraproject.org/languages/

        Returns:
        :tags: a list of Tag objects, filtered by :language:
        :builds: list of found PackageBuild objects
        '''

        lang = Language.find(language)
        
        if tags.__class__ != [].__class__:
            tags = [tags]
        builds = set()

        # get the actual Tag objects
        object_tags = []
        for tag in tags:
            try:
             object_tags.append(
                    Tag.query.filter_by(name=tag, language=lang).one())
            except:
                raise Exception(tag, language)
        tags = object_tags
                        
        if operator.lower() == 'or':
            for tag in tags:
                pkgs = tag.builds
                for pkg in pkgs:
                    builds.add(pkg)
        elif operator.lower() == 'and':
            builds = set(tags[0].builds)
            if len(tags) > 0:
                # do an intersection between all the taglists to get
                # the common ones
                for tag in tags[1:]:
                    builds = set(tags[0].builds) & set(tag.builds)

        return builds

    def comment(self, author, body, language):
        '''Add a new comment to a packagebuild.

        :arg author: the FAS author
        :arg body: text body of the comment
        :arg language: name or shortname of the comment body`s language
        '''

        lang = Language.find(language)
        
        comment = Comment(author, body, language, published=True,
                          packagebuildname=self.name)

        # self.comments is just an illusion
        buildname = PackageBuildName.query.filter_by(name=self.name).one()
        buildname.comments.append(comment)
        
        session.flush()

    def score(self, tag):
        '''Return the score of a given tag-package combination

        :arg tag: An actual Tag object.

        Returns an integer of the score or -1 otherwise.
        '''
        score = -1
        try:
            if self.buildname in tag.buildnames:
                result = PackageBuildNamesTagsTable.select(and_(
                    PackageBuildNamesTagsTable.c.tagid==tag.id,
                    PackageBuildNamesTagsTable.c.packagebuildname==self.name)
                    ).execute().fetchone()
                score = result[2]
            return score
        except AttributeError:
            print 'This method receives a Tag object as argument!'

    def scores(self, language='en_US'):
        '''Return a dictionary of tagname: score for a given PackageBuild

        :kwarg language (optional): Restrict the search to just one language.
        '''

        lang = Language.find(language)

        tags = Tag.query.join(Tag.buildnames).filter(
            and_(PackageBuildName.name==self.name, Tag.language==lang)).all()
        
        buildtags = {}
        for tag in tags:
            buildtags[tag.name] = self.score(tag)
        return buildtags

    # Link to comments/tags, through PackageBuildName
    comments = association_proxy('buildname', 'comments')
    tags = association_proxy('buildname', 'tags')
        
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
    'listings': relation(PackageListing, backref=backref('builds'),
        secondary = PackageBuildListingTable)
    })
mapper(PackageBuildName, PackageBuildNamesTable, properties={
    'builds': relation(PackageBuild, backref=backref('buildname'),
        cascade='all, delete-orphan'),
    'tags': relation(Tag, backref=backref('buildnames'),
        secondary=PackageBuildNamesTagsTable),
    'comments': relation(Comment, backref=backref('buildnames'),
        cascade='all, delete-orphan')
    })
