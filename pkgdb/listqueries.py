# -*- coding: utf-8 -*-
#
# Copyright © 2007-2009  Red Hat, Inc.
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
Send acl information to third party tools.
'''
#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.
# :W0232: no __init__ method: This only applies to a validator schema.  Those
#   don't have methods, just attributes so it's expected.
# :R0903: Too few public methods: This only applies to the validator schema
#   and two classes that we're using as data structures that can return json.
#   So this is fine.
# :C0322: Disable space around operator checking in multiline decorators

import itertools

from sqlalchemy import select, and_, create_engine
from sqlalchemy.orm import sessionmaker

from turbogears import expose, validate, error_handler
from turbogears import controllers, validators

from turbogears.database import get_engine

from pkgdb.model import Package, Branch, GroupPackageListing, Collection, \
     GroupPackageListingAcl, PackageListing, PersonPackageListing, \
     PersonPackageListingAcl, Repo, PackageBuild
from pkgdb.model import PackageTable, CollectionTable, ReposTable, TagsTable, \
     ApplicationsTagsTable, ApplicationTag
from pkgdb.model import YumTagsTable, YumReposTable, \
    YumPackageBuildTable, YumPackageBuildNamesTable, \
    YumPackageBuildNamesTagsTable
from pkgdb.model.yumdb import yummeta, sqliteconn, dbfile
from pkgdb.utils import STATUS
from pkgdb import _

from pkgdb.validators import BooleanValue, CollectionNameVersion

from fedora.tg.util import jsonify_validation_errors


#
# Validators
#

class NotifyList(validators.Schema):
    '''Validator schema for the notify method.'''
    # validator schemas don't have methods (R0903, W0232)
    #pylint:disable-msg=R0903,W0232

    # We don't use a more specific validator for collection or version because
    # the chained validator does it for us and we don't want to hit the
    # database multiple times
    name = validators.UnicodeString(not_empty=False, strip=True)
    version = validators.UnicodeString(not_empty=False, strip=True)
    eol = BooleanValue
    chained_validators = (CollectionNameVersion(),)

#
# Supporting Objects
#

class AclList(object):
    '''List of people and groups who hold this acl.
    '''
    # This class is just a data structure that can convert itself to json so
    # there's no need for a lot of methods.
    #pylint:disable-msg=R0903

    ### FIXME: Reevaluate whether we need this data structure at all.  Once
    # jsonified, it is transformed into a dict of lists so it might not be
    # good to do it this way.
    def __init__(self, people=None, groups=None):
        self.people = people or []
        self.groups = groups or []

    def __json__(self):
        return {'people' : self.people,
                'groups' : self.groups
                }

class BugzillaInfo(object):
    '''Information necessary to construct a bugzilla record for a package.
    '''
    # This class is just a data structure that can convert itself to json so
    # there's no need for a lot of methods.
    #pylint:disable-msg=R0903

    ### FIXME: Reevaluate whether we need this data structure at all.  Once
    # jsonified, it is transformed into a dict of lists so it might not be
    # good to do it this way.
    def __init__(self, owner=None, summary=None, cclist=None, qacontact=None):
        self.owner = owner
        self.summary = summary
        self.cclist = cclist or AclList()
        self.qacontact = qacontact

    def __json__(self):
        return {'owner' : self.owner,
                'summary' : self.summary,
                'cclist' : self.cclist,
                'qacontact' : self.qacontact
                }

#
# Controllers
#

class ListQueries(controllers.Controller):
    '''Controller for lists of acl/owner information needed by external tools.

    Although these methods can return web pages, the main feature is the json
    and plain text that they return as the main usage of this is for external
    tools to take data for their use.
    '''
    def __init__(self, app_title=None):
        self.app_title = app_title

    def _add_to_bugzilla_acl_list(self, package_acls, pkg_name,
            collection_name, identity, group=None):
        '''Add the given acl to the list of acls for bugzilla.

        :arg package_acls: Data structure to fill
        :arg pkg_name: Name of the package we're setting the acl on
        :arg collection_name: Name of the bugzilla collection on which we're
            setting the acl.
        :arg identity: Id of the user or group for whom the acl is being set.
        :kwarg group: If set, we're dealing with a group instead of a person.
        '''
        # Lookup the collection
        try:
            collection = package_acls[collection_name]
        except KeyError:
            collection = {}
            package_acls[collection_name] = collection
        # Then the package
        try:
            package = collection[pkg_name]
        except KeyError:
            package = BugzillaInfo()
            collection[pkg_name] = package
        # Then add the acl
        if group:
            try:
                package.cclist.groups.append(identity)
            except KeyError:
                package.cclist = AclList(groups=[identity])
        else:
            try:
                package.cclist.people.append(identity)
            except KeyError:
                package.cclist = AclList(people=[identity])

    def _add_to_vcs_acl_list(self, package_acls, acl, pkg_name, branch_name,
            identity, group=None):
        '''Add the given acl to the list of acls for the vcs.

        :arg package_acls: Data structure to fill
        :arg acl: Acl to create
        :arg pkg_name: Name of the package we're setting the acl on
        :arg branch_name: Name of the branch for which the acl is being set
        :arg identity: id of the user or group for whom the acl is being set.
        :kwarg group: If set, we're dealing with a group instead of a person.
        '''
        # Key by package name
        try:
            pkg = package_acls[pkg_name]
        except KeyError:
            pkg = {}
            package_acls[pkg_name] = pkg

        # Then by branch name
        try:
            branch = pkg[branch_name]
        except KeyError:
            branch = {}
            pkg[branch_name] = branch

        # Add these acls to the group acls
        if group:
            try:
                branch[acl].groups.append(identity)
            except KeyError:
                branch[acl] = AclList(groups=[identity])
        else:
            try:
                branch[acl].people.append(identity)
            except KeyError:
                branch[acl] = AclList(people=[identity])

    @expose(template='genshi-text:pkgdb.templates.plain.vcsacls',
            as_format='plain', accept_format='text/plain',
            content_type='text/plain; charset=utf-8', #pylint:disable-msg=C0322
            format='text') #pylint:disable-msg=C0322
    @expose(template='pkgdb.templates.vcsacls', allow_json=True)
    def vcs(self):
        '''Return ACLs for the version control system.

        The format of the returned data is this:
        packageAcls['pkg']['branch']['acl'].'type' = (list of users/groups)
        For instance:
          packageAcls['bzr']['FC-6']['commit'].group = (cvsextras,)
          packageAcls['bzr']['FC-6']['commit'].people = (shahms, toshio)

        This method can display a long list of users but most people will want
        to access it as JSON data with the ?tg_format=json query parameter.
        '''
        # Store our acls in a dict
        package_acls = {}

        # Get the vcs group acls from the db

        group_acls = select((
            #pylint:disable-msg=E1101
            Package.name,
            Branch.branchname,
            GroupPackageListing.groupname), and_(
                GroupPackageListingAcl.acl == 'commit',
                GroupPackageListingAcl.statuscode \
                        == STATUS['Approved'].statuscodeid,
                GroupPackageListingAcl.grouppackagelistingid \
                        == GroupPackageListing.id,
                GroupPackageListing.packagelistingid \
                        == PackageListing.id,
                PackageListing.packageid == Package.id,
                PackageListing.collectionid == Collection.id,
                Branch.collectionid == Collection.id,
                PackageListing.statuscode != STATUS['Removed'].statuscodeid,
                Package.statuscode != STATUS['Removed'].statuscodeid
                )
            )

        groups = {}

        # Save them into a python data structure
        for record in group_acls.execute():
            if not record[2] in groups:
                groups[record[2]] = record[2]
            self._add_to_vcs_acl_list(package_acls, 'commit',
                    record[0], record[1],
                    groups[record[2]], group=True)
        del group_acls

        # Get the package owners from the db
        # Exclude the orphan user from that.
        owner_acls = select((
            #pylint:disable-msg=E1101
            Package.name,
            Branch.branchname, PackageListing.owner),
            and_(
                PackageListing.packageid==Package.id,
                PackageListing.collectionid==Collection.id,
                PackageListing.owner!='orphan',
                Collection.id==Branch.collectionid,
                PackageListing.statuscode != STATUS['Removed'].statuscodeid,
                Package.statuscode != STATUS['Removed'].statuscodeid
                ),
            order_by=(PackageListing.owner,)
            )

        # Save them into a python data structure
        for record in owner_acls.execute():
            username = record[2]
            self._add_to_vcs_acl_list(package_acls, 'commit',
                    record[0], record[1],
                    username, group=False)
        del owner_acls

        # Get the vcs user acls from the db
        person_acls = select((
            #pylint:disable-msg=E1101
            Package.name,
            Branch.branchname, PersonPackageListing.username),
            and_(
                PersonPackageListingAcl.acl=='commit',
                PersonPackageListingAcl.statuscode \
                        == STATUS['Approved'].statuscodeid,
                PersonPackageListingAcl.personpackagelistingid \
                        == PersonPackageListing.id,
                PersonPackageListing.packagelistingid \
                        == PackageListing.id,
                PackageListing.packageid == Package.id,
                PackageListing.collectionid == Collection.id,
                Branch.collectionid == Collection.id,
                PackageListing.statuscode != STATUS['Removed'].statuscodeid,
                Package.statuscode != STATUS['Removed'].statuscodeid
                ),
            order_by=(PersonPackageListing.username,)
            )
        # Save them into a python data structure
        for record in person_acls.execute():
            username = record[2]
            self._add_to_vcs_acl_list(package_acls, 'commit',
                    record[0], record[1],
                    username, group=False)

        return dict(title=_('%(app)s -- VCS ACLs') % {'app': self.app_title},
                packageAcls=package_acls)

    @expose(template='pkgdb.templates.buildtags', as_format='xml',
            accept_format='application/xml', #pylint:disable-msg=C0322
            allow_json=True) #pylint:disable-msg=E1101
    def buildtags(self, repos):
        '''Return an XML object with all the PackageBuild tags and their scores.
        The PackageBuild tags are tags binded to applications belonging to 
        the packagebuild. When there are more apps with same tag within one 
        packaebuild, the maximum score is taken.

        :arg repoName: A repo shortname to lookup packagebuilds into
        for tags

        Returns:
        :buildtags: a dictionary of buildaname : tagdict, where tagdict is a
        dictionary of tag : score key-value pairs. 
        '''
        if repos.__class__ != [].__class__:
            repos = [repos]

        buildtags = {}
        for repo in repos:
            buildtags[repo] = {}

            #pylint:disable-msg=E1101
            repoid = Repo.query.filter_by(shortname=repo).one().id
            builds = PackageBuild.query.filter_by(repoid=repoid)
            #pylint:enable-msg=E1101

            for build in builds:
                buildtags[repo][build.name] = build.scores()

        return dict(buildtags=buildtags, repos=repos)

    @expose(content_type='application/sqlite')
    def sqlitebuildtags(self, repos):
        '''Return a sqlite database of packagebuilds and tags.

        The database returned will contain copies or subsets of tables in the
        pkgdb.

        :kwarg repos: A list of repository shortnames (e.g. 'F-11-i386')

        '''

        if repos.__class__ != [].__class__:
            repos = [repos]

        # initialize/clear database
        open(dbfile, 'w').close()
        
        yummeta.create_all()

        # since we're using two databases, we'll need a new session
        default_engine = get_engine()
        lite_session = sessionmaker(create_engine(sqliteconn))()
        
        # copy the repo
        s = select([ReposTable.c.id, ReposTable.c.name, ReposTable.c.shortname],
                   ReposTable.c.shortname.in_(repos))
        e = default_engine.execute(s)
        fetchedrepos = e.fetchall()
        e.close()
        lite_session.execute(YumReposTable.insert(), fetchedrepos)

        #pylint:disable-msg=E1101
        packagebuilds = PackageBuild.query.join('repos').filter(
                    ReposTable.c.shortname.in_(repos))
        #pylint:enable-msg=E1101

        unique_tags = {}

        for packagebuild in packagebuilds:
            build = [(packagebuild.id, packagebuild.name, packagebuild.repoid)]
            lite_session.execute(YumPackageBuildTable.insert(), build)
            name = [(packagebuild.name)]
            lite_session.execute(YumPackageBuildNamesTable.insert(), name)

            build_tags = {}

            # collect tags
            for app in build.applications: #pylint:disable-msg=E1101
                #pylint:disable-msg=E1101
                tags = ApplicationTag.query.join('tag').filter(ApplicationsTagsTable.c.applicationid==app.id)
                #pylint:enable-msg=E1101
                for tag in tags:
                    sc = build_tags.get(tag.tag.name, None)
                    if sc is None or sc < tag.score:
                        build_tags[tag.tag.name] = tag.score

            # write tags
            for tag, score in build_tags.iteritems():
                tag_id = unique_tags.get(tag, None)
                if not tag_id:
                    #pylint:disable-msg=E1103
                    tag_id = YumTagsTable.query.insert().values(
                        name=tag 
                        ).execute().last_inserted_ids()[-1]
                    #pylint:enable-msg=E1103
                    unique_tags[tag] = tag_id

                #pylint:disable-msg=E1101
                YumPackageBuildNamesTagsTable.query.insert().values(
                    packagebuildname=packagebuild.name, 
                    tagid=tag_id, score=score
                    ).execute()
                #pylint:enable-msg=E1101

        lite_session.commit()

        f = open(dbfile, 'r')
        dump = f.read()
        f.close()
        return dump
        
    @expose(template="genshi-text:pkgdb.templates.plain.bugzillaacls",
            as_format="plain", accept_format="text/plain",
            content_type="text/plain; charset=utf-8", #pylint:disable-msg=C0322
            format='text') #pylint:disable-msg=C0322
    @expose(template="pkgdb.templates.bugzillaacls", allow_json=True)
    def bugzilla(self):
        '''Return the package attributes used by bugzilla.

        Note: The data returned by this function is for the way the current
        Fedora bugzilla is setup as of (2007/6/25).  In the future, bugzilla
        may change to have separate products for each collection-version.
        When that happens we'll have to change what this function returns.

        The returned data looks like this:

        bugzillaAcls[collection][package].attribute
        attribute is one of:
            :owner: FAS username for the owner
            :qacontact: if the package has a special qacontact, their userid
                is listed here
            :summary: Short description of the package
            :cclist: list of FAS userids that are watching the package
        '''
        bugzilla_acls = {}
        username = None

        # select all packages that are in an active release
        package_info = select((
            #pylint:disable-msg=E1101
            Collection.name, Package.name,
            PackageListing.owner, PackageListing.qacontact,
            Package.summary),
            and_(
                Collection.id==PackageListing.collectionid,
                Package.id==PackageListing.packageid,
                Package.statuscode!=STATUS['Removed'].statuscodeid,
                PackageListing.statuscode!=STATUS['Removed'].statuscodeid,
                Collection.statuscode.in_(STATUS['Active'].statuscodeid,
                    STATUS['Under Development'].statuscodeid),
                ),
            order_by=(Collection.name,), distinct=True)

        # List of packages that need more processing to decide who the owner
        # should be.
        undupe_owners = []

        for pkg in package_info.execute():
            # Lookup the collection
            collection_name = pkg[0]
            try:
                collection = bugzilla_acls[collection_name]
            except KeyError:
                collection = {}
                bugzilla_acls[collection_name] = collection
            # Then the package
            package_name = pkg[1]
            try:
                package = collection[package_name]
            except KeyError:
                package = BugzillaInfo()
                collection[package_name] = package

            # Save the package information in the data structure to return
            if not package.owner:
                package.owner = pkg[2]
            elif pkg[2] != package.owner:
                # There are multiple owners for this package.
                undupe_owners.append(package_name)
            if pkg[3]:
                package.qacontact = pkg[3]
            package.summary = pkg[4]

        if undupe_owners:
            # These are packages that have different owners in different
            # branches.  Need to find one to be the owner of the bugzilla
            # component
            #pylint:disable-msg=E1101
            package_info = select((Collection.name,
                Collection.version,
                Package.name, PackageListing.owner),
                and_(
                    Collection.id==PackageListing.collectionid,
                    Package.id==PackageListing.packageid,
                    Package.statuscode!=STATUS['Removed'].statuscodeid,
                    PackageListing.statuscode!=STATUS['Removed'].statuscodeid,
                    Collection.statuscode.in_((STATUS['Active'].statuscodeid,
                        STATUS['Under Development'].statuscodeid)),
                    Package.name.in_(undupe_owners),
                    ),
                order_by=(Collection.name, Collection.version),
                distinct=True)
            #pylint:enable-msg=E1101

            # Organize the results so that we have:
            # [packagename][collectionname][collectionversion] = owner
            by_pkg = {}
            for pkg in package_info.execute():
                # Order results by package
                try:
                    package = by_pkg[pkg[2]]
                except KeyError:
                    package = {}
                    by_pkg[pkg[2]] = package

                # Then collection
                try:
                    collection = package[pkg[0]]
                except KeyError:
                    collection = {}
                    package[pkg[0]] = collection

                # Then collection version == owner
                collection[pkg[1]] = pkg[3]

            # Find the proper owner
            for pkg in by_pkg:
                for collection in by_pkg[pkg]:
                    if collection == 'Fedora':
                        # If devel exists, use its owner
                        # We can safely ignore orphan because we already know
                        # this is a dupe and thus a non-orphan exists.
                        if 'devel' in by_pkg[pkg][collection]:
                            if by_pkg[pkg][collection]['devel'] == 'orphan'\
                                    and len(by_pkg[pkg][collection]) > 1:
                                # If there are other owners, try to use them
                                # instead of orphan
                                del by_pkg[pkg][collection]['devel']
                            else:
                                # Prefer devel above all others
                                bugzilla_acls[collection][pkg].owner = \
                                        by_pkg[pkg][collection]['devel']
                                continue

                    # For any collection except Fedora or Fedora if the devel
                    # version does not exist, treat releases as numbers and
                    # take the results from the latest number
                    releases = [int(r) for r in by_pkg[pkg][collection] \
                            if by_pkg[pkg][collection][r] != 'orphan']
                    if not releases:
                        # Every release was an orphan
                        bugzilla_acls[collection][pkg].owner = 'orphan'
                    else:
                        releases.sort()
                        bugzilla_acls[collection][pkg].owner = \
                                by_pkg[pkg][collection][unicode(releases[-1])]

        # Retrieve the user acls

        person_acls = select((
            #pylint:disable-msg=E1101
            Package.name,
            Collection.name, PersonPackageListing.username),
            and_(
                PersonPackageListingAcl.acl == 'watchbugzilla',
                PersonPackageListingAcl.statuscode == \
                        STATUS['Approved'].statuscodeid,
                PersonPackageListingAcl.personpackagelistingid == \
                        PersonPackageListing.id,
                PersonPackageListing.packagelistingid == \
                        PackageListing.id,
                PackageListing.packageid == Package.id,
                PackageListing.collectionid == Collection.id,
                Package.statuscode!=STATUS['Removed'].statuscodeid,
                PackageListing.statuscode!=STATUS['Removed'].statuscodeid,
                Collection.statuscode.in_((STATUS['Active'].statuscodeid,
                    STATUS['Under Development'].statuscodeid)),
                ),
            order_by=(PersonPackageListing.username,), distinct=True
            )

        # Save them into a python data structure
        for record in person_acls.execute():
            username = record[2]
            self._add_to_bugzilla_acl_list(bugzilla_acls, record[0], record[1],
                    username, group=False)

        ### TODO: No group acls at the moment
        # There are no group acls to take advantage of this.
        return dict(title=_('%(app)s -- Bugzilla ACLs') % {
            'app': self.app_title}, bugzillaAcls=bugzilla_acls)

    @validate(validators=NotifyList())
    @error_handler()
    @expose(template='genshi-text:pkgdb.templates.plain.notify',
            as_format='plain', accept_format='text/plain',
            content_type='text/plain; charset=utf-8', #pylint:disable-msg=C0322
            format='text') #pylint:disable-msg=C0322
    @expose(template='pkgdb.templates.notify', allow_json=True)
    def notify(self, name=None, version=None, eol=False):
        '''List of usernames that should be notified of changes to a package.

        For the collections specified we want to retrieve all of the owners,
        watchbugzilla, and watchcommits accounts.

        :kwarg name: Set to a collection name to filter the results for that
        :kwarg version: Set to a collection version to further filter results
            for a single version
        :kwarg eol: Set to True if you want to include end of life
            distributions
        '''
        # Check for validation errors requesting this form
        errors = jsonify_validation_errors()
        if errors:
            return errors

        # Retrieve Packages, owners, and people on watch* acls
        #pylint:disable-msg=E1101
        owner_query = select((Package.name, PackageListing.owner),
                from_obj=(PackageTable.join(PackageListing).join(
                    CollectionTable))).where(and_(
                        Package.statuscode == STATUS['Approved'].statuscodeid,
                        PackageListing.statuscode == \
                                STATUS['Approved'].statuscodeid)
                        ).distinct().order_by('name')
        watcher_query = select((Package.name, PersonPackageListing.username),
                from_obj=(PackageTable.join(PackageListing).join(
                    Collection).join(PersonPackageListing).join(
                        PersonPackageListingAcl))).where(and_(
                            Package.statuscode == \
                                    STATUS['Approved'].statuscodeid,
                            PackageListing.statuscode == \
                                    STATUS['Approved'].statuscodeid,
                            PersonPackageListingAcl.acl.in_(
                                ('watchbugzilla', 'watchcommits')),
                            PersonPackageListingAcl.statuscode ==
                                STATUS['Approved'].statuscodeid
                        )).distinct().order_by('name')
        #pylint:enable-msg=E1101

        if not eol:
            # Filter out eol distributions
            #pylint:disable-msg=E1101
            owner_query = owner_query.where(Collection.statuscode.in_(
                (STATUS['Active'].statuscodeid,
                    STATUS['Under Development'].statuscodeid)))
            watcher_query = watcher_query.where(Collection.statuscode.in_(
                (STATUS['Active'].statuscodeid,
                    STATUS['Under Development'].statuscodeid)))
            #pylint:enable-msg=E1101

        # Only grab from certain collections
        if name:
            #pylint:disable-msg=E1101
            owner_query = owner_query.where(Collection.name==name)
            watcher_query = watcher_query.where(Collection.name==name)
            #pylint:enable-msg=E1101
            if version:
                # Limit the versions of those collections
                #pylint:disable-msg=E1101
                owner_query = owner_query.where(Collection.version==version)
                watcher_query = watcher_query.where(Collection.version==version)
                #pylint:enable-msg=E1101

        pkgs = {}
        # turn the query into a python object
        for pkg in itertools.chain(owner_query.execute(),
                watcher_query.execute()):
            additions = []
            additions.append(pkg[1])
            pkgs.setdefault(pkg[0], set()).update(
                    (pkg[1],))

        # Retrieve list of collection information for generating the
        # collection form
        #pylint:disable-msg=E1101
        collection_list = Collection.query.order_by('name').order_by('version')
        #pylint:enable-msg=E1101
        collections = {}
        for collection in collection_list:
            try:
                collections[collection.name].append(collection.version)
            except KeyError:
                collections[collection.name] = [collection.version]

        # Return the data
        return dict(title=_('%(app)s -- Notification List') % {
            'app': self.app_title}, packages=pkgs, collections=collections,
            name=name, version=version, eol=eol)
