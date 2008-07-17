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
Send acl information to third party tools.
'''

from sqlalchemy import select, and_, or_
from turbogears import expose, validate, error_handler
from turbogears import controllers, validators

from pkgdb.model import (Package, Branch, GroupPackageListing, Collection,
        StatusTranslation, GroupPackageListingAcl, PackageListing,
        PersonPackageListing, PersonPackageListingAcl,)
from pkgdb.model import PackageTable, CollectionTable

ORPHAN_ID = 9900

from pkgdb.validators import BooleanValue, CollectionNameVersion

try:
    from fedora.tg.util import jsonify_validation_errors
except ImportError:
    # Not a recent enough version of python-fedora.  This is only a
    # temporary workaround
    from fedora.tg.util import request_format
    from turbogears import flash
    import cherrypy
    def jsonify_validation_errors():
        '''Turn tg_errors into a flash message and a json exception.'''
        # Check for validation errors
        errors = getattr(cherrypy.request, 'validation_errors', None)
        if not errors:
            return None

        # Set the message for both html and json output
        message = u'\n'.join([u'%s: %s' % (param, msg) for param, msg in
            errors.items()])
        format = request_format()
        if format == 'html':
            message.translate({ord('\n'): u'<br />\n'})
        flash(message)

        # If json, return additional information to make this an exception
        if format == 'json':
            # Note: explicit setting of tg_template is needed in TG < 1.0.4.4
            # A fix has been applied for TG-1.0.4.5
            return dict(exc='Invalid', tg_template='json')
        return None

#
# Validators
#

class NotifyList(validators.Schema):
    '''Validator schema for the notify method.'''
    # validator schemas don't have methods (R0903, W0232)
    # pylint: disable-msg=R0903,W0232

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
    # pylint: disable-msg=R0903

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
    # pylint: disable-msg=R0903

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
    # pylint: disable-msg=E1101
    approvedStatus = StatusTranslation.query.filter_by(
            statusname='Approved', language='C').one().statuscodeid
    removedStatus = StatusTranslation.query.filter_by(
            statusname='Removed', language='C').one().statuscodeid
    activeStatus = StatusTranslation.query.filter_by(
            statusname='Active', language='C').one().statuscodeid
    develStatus = StatusTranslation.query.filter_by(
            statusname='Under Development', language='C').one().statuscodeid
    # pylint: enable-msg=E1101

    def __init__(self, fas=None, appTitle=None):
        self.fas = fas
        self.app_title = appTitle

    def _add_to_bugzilla_acl_list(self, package_acls, pkg_name,
            collection_name, identity, group=None):
        '''Add the given acl to the list of acls for bugzilla.

        Arguments:
        :package_acls: The data structure to fill
        :pkg_name: Name of the package we're setting the acl on
        :collection_name: Name of the bugzilla collection on which we're
            setting the acl.
        :identity: The id of the user or group for whom the acl is being set.
        :group: If set, we're dealing with a group instead of a person.
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

        Arguments:
        :package_acls: The data structure to fill
        :acl: The acl to create
        :pkg_name: Name of the package we're setting the acl on
        :branch_name: Name of the branch for which the acl is being set
        :identity: The id of the user or group for whom the acl is being set.
        :group: If set, we're dealing with a group instead of a person.
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

    @expose(template="genshi-text:pkgdb.templates.plain.vcsacls",
            as_format="plain", accept_format="text/plain",
            content_type="text/plain; charset=utf-8", format='text')
    @expose(template="pkgdb.templates.vcsacls", allow_json=True)
    def vcs(self):
        '''Return ACLs for the version control system.

        The format of the returned data is this:
        packageAcls['pkg']['branch']['acl'].'type' = (list of users/groups)
        For instance:
          packageAcls['bzr']['FC-6']['commit'].group = (cvsextras,)
          packageAcls['bzr']['FC-6']['commit'].people = (shahms, toshio)

        This method can display a long list of users but most people will want
        to access it as JSON data with the ?tg_format=json query parameter.

        Caveat: The group handling in this code is special cased for cvsextras
        rather than generic.  When we get groups figured out we can change
        this.
        '''
        # Store our acls in a dict
        package_acls = {}

        # Get the vcs group acls from the db

        group_acls = select((
            # pylint: disable-msg=E1101
            Package.name,
            Branch.branchname,
            GroupPackageListing.groupid), and_(
                GroupPackageListingAcl.acl == 'commit',
                GroupPackageListingAcl.statuscode \
                        == self.approvedStatus,
                GroupPackageListingAcl.grouppackagelistingid \
                        == GroupPackageListing.id,
                GroupPackageListing.packagelistingid \
                        == PackageListing.id,
                PackageListing.packageid == Package.id,
                PackageListing.collectionid == Collection.id,
                Branch.collectionid == Collection.id,
                PackageListing.statuscode != self.removedStatus,
                Package.statuscode != self.removedStatus
                )
            )

        groups = {}

        # Save them into a python data structure
        for record in group_acls.execute():
            if not record[2] in groups:
                groups[record[2]] = self.fas.group_by_id(record[2])['name']
            self._add_to_vcs_acl_list(package_acls, 'commit',
                    record[0], record[1],
                    groups[record[2]], group=True)
        del group_acls

        # Get the package owners from the db
        # Exclude the orphan user from that.
        owner_acls = select((
            # pylint: disable-msg=E1101
            Package.name,
            Branch.branchname, PackageListing.owner),
            and_(
                PackageListing.packageid==Package.id,
                PackageListing.collectionid==Collection.id,
                PackageListing.owner!=ORPHAN_ID,
                Collection.id==Branch.collectionid,
                PackageListing.statuscode != self.removedStatus,
                Package.statuscode != self.removedStatus
                ),
            order_by=(PackageListing.owner,)
            )

        # Cache the userId/username pairs so we don't have to call the fas for
        # every package.
        user_list = self.fas.user_id()

        # Save them into a python data structure
        for record in owner_acls.execute():
            username = user_list[record[2]]
            self._add_to_vcs_acl_list(package_acls, 'commit',
                    record[0], record[1],
                    username, group=False)
        del owner_acls

        # Get the vcs user acls from the db
        person_acls = select((
            # pylint: disable-msg=E1101
            Package.name,
            Branch.branchname, PersonPackageListing.userid),
            and_(
                PersonPackageListingAcl.acl=='commit',
                PersonPackageListingAcl.statuscode \
                        == self.approvedStatus,
                PersonPackageListingAcl.personpackagelistingid \
                        == PersonPackageListing.id,
                PersonPackageListing.packagelistingid \
                        == PackageListing.id,
                PackageListing.packageid == Package.id,
                PackageListing.collectionid == Collection.id,
                Branch.collectionid == Collection.id,
                PackageListing.statuscode != self.removedStatus,
                Package.statuscode != self.removedStatus
                ),
            order_by=(PersonPackageListing.userid,)
            )
        # Save them into a python data structure
        for record in person_acls.execute():
            username = user_list[record[2]]
            self._add_to_vcs_acl_list(package_acls, 'commit',
                    record[0], record[1],
                    username, group=False)

        return dict(title=self.app_title + ' -- VCS ACLs',
                packageAcls=package_acls)

    @expose(template="genshi-text:pkgdb.templates.plain.bugzillaacls",
            as_format="plain", accept_format="text/plain",
            content_type="text/plain; charset=utf-8", format='text')
    @expose(template="pkgdb.templates.bugzillaacls", allow_json=True)
    def bugzilla(self):
        '''Return the package attributes used by bugzilla.

        Note: The data returned by this function is for the way the current
        Fedora bugzilla is setup as of (2007/6/25).  In the future, bugzilla
        will change to have separate products for each collection-version.
        When that happens we'll have to change what this function returns.

        The returned data looks like this:

        bugzillaAcls[collection][package].attribute
        attribute is one of:
        :owner: FAS username for the owner
        :qacontact: if the package has a special qacontact, their userid is
          listed here
        :summary: Short description of the package
        :cclist: list of FAS userids that are watching the package
        '''
        bugzilla_acls = {}
        username = None

        # select all packages that are active in an active release
        package_info = select((
            # pylint: disable-msg=E1101
            Collection.name, Package.name,
            PackageListing.owner, PackageListing.qacontact,
            Package.summary),
            and_(
                Collection.id==PackageListing.collectionid,
                Package.id==PackageListing.packageid,
                Package.statuscode==self.approvedStatus,
                PackageListing.statuscode==self.approvedStatus,
                Collection.statuscode.in_((self.activeStatus,
                    self.develStatus)),
                ),
            order_by=(Collection.name,), distinct=True)

        # Cache the userId/username pairs so we don't have to call the
        # fas for every package.
        user_list = self.fas.user_id()

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
                package.owner = user_list[pkg[2]]
            elif user_list[pkg[2]] != package.owner:
                # There are multiple owners for this package.
                undupe_owners.append(package_name)
            if pkg[3]:
                package.qacontact = user_list[pkg[3]]
            package.summary = pkg[4]

        if undupe_owners:
            # These are packages that have different owners in different
            # branches.  Need to find one to be the owner of the bugzilla
            # component
            # SQLAlchemy mapped classes are monkey patched
            # pylint: disable-msg=E1101
            package_info = select((Collection.name,
                Collection.version,
                Package.name, PackageListing.owner),
                and_(
                    Collection.id==PackageListing.collectionid,
                    Package.id==PackageListing.packageid,
                    Package.statuscode==self.approvedStatus,
                    PackageListing.statuscode==self.approvedStatus,
                    Collection.statuscode.in_((self.activeStatus,
                        self.develStatus)),
                    Package.name.in_(undupe_owners),
                    ),
                order_by=(Collection.name, Collection.version),
                distinct=True)
            # pylint: enable-msg=E1101

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
                            if by_pkg[pkg][collection]['devel'] == ORPHAN_ID \
                                    and len(by_pkg[pkg][collection]) > 1:
                                # If there are other owners, try to use them
                                # instead of orphan
                                del by_pkg[pkg][collection]['devel']
                            else:
                                # Prefer devel above all others
                                bugzilla_acls[collection][pkg].owner = \
                                    user_list[by_pkg[pkg][collection]['devel']]
                                continue

                    # For any collection except Fedora or Fedora if the devel
                    # version does not exist, treat releases as numbers and
                    # take the results from the latest number
                    releases = [int(r) for r in by_pkg[pkg][collection] \
                            if by_pkg[pkg][collection][r] != ORPHAN_ID]
                    if not releases:
                        # Every release was an orphan
                        bugzilla_acls[collection][pkg].owner = \
                                user_list[ORPHAN_ID]
                    else:
                        releases.sort()
                        bugzilla_acls[collection][pkg].owner = \
                                user_list[by_pkg[pkg][collection][ \
                                    unicode(releases[-1])]]

        # Retrieve the user acls

        person_acls = select((
            # pylint: disable-msg=E1101
            Package.name,
            Collection.name, PersonPackageListing.userid),
            and_(
                PersonPackageListingAcl.acl == 'watchbugzilla',
                PersonPackageListingAcl.statuscode == \
                        self.approvedStatus,
                PersonPackageListingAcl.personpackagelistingid == \
                        PersonPackageListing.id,
                PersonPackageListing.packagelistingid == \
                        PackageListing.id,
                PackageListing.packageid == Package.id,
                PackageListing.collectionid == Collection.id,
                Package.statuscode==self.approvedStatus,
                PackageListing.statuscode==self.approvedStatus,
                Collection.statuscode.in_((self.activeStatus,
                    self.develStatus)),
                ),
            order_by=(PersonPackageListing.userid,), distinct=True
            )

        # Save them into a python data structure
        for record in person_acls.execute():
            username = user_list[record[2]]
            self._add_to_bugzilla_acl_list(bugzilla_acls, record[0], record[1],
                    username, group=False)

        ### TODO: No group acls at the moment
        # There are no group acls to take advantage of this.
        return dict(title=self.app_title + ' -- Bugzilla ACLs',
                bugzillaAcls=bugzilla_acls)

    @validate(validators=NotifyList())
    @error_handler()
    @expose(template='genshi-text:pkgdb.templates.plain.notify',
            as_format='plain', accept_format='text/plain',
            content_type='text/plain; charset=utf-8', format='text')
    @expose(template='pkgdb.templates.notify', allow_json=True)
    def notify(self, name=None, version=None, eol=False):
        '''List of usernames that should be notified of changes to a package.

        For the collections specified we want to retrieve all of the owners,
        watchbugzilla, and watchcommits accounts.

        Keyword Arguments:
        :name: Set to a collection name to filter the results for that
        :version: Set to a collection version to further filter results for a
            single version
        :eol: Set to True if you want to include end of life distributions
        :email: If set to True, this will return email addresses from FAS
            instead of Fedora Project usernames
        '''
        # Check for validation errors requesting this form
        errors = jsonify_validation_errors()
        if errors:
            return errors

        # SQLAlchemy mapped classes are monkey patched
        # pylint: disable-msg=E1101
        # Retrieve Packages, owners, and people on watch* acls
        query = select((Package.name, PackageListing.owner,
            PersonPackageListing.userid),
            from_obj=(PackageTable.join(PackageListing).outerjoin(
                PersonPackageListing).outerjoin(PersonPackageListingAcl),
                CollectionTable)
            ).where(or_(and_(PersonPackageListingAcl.acl.in_(
                ('watchbugzilla', 'watchcommits')),
                PersonPackageListingAcl.statuscode==self.approvedStatus),
                PersonPackageListingAcl.acl==None)
                ).where(Collection.id==PackageListing.collectionid
                        ).distinct().order_by('name')
        # pylint: enable-msg=E1101

        if not eol:
            # Filter out eol distributions
            # SQLAlchemy mapped classes are monkey patched
            # pylint: disable-msg=E1101
            query = query.where(Collection.statuscode.in_(
                (self.activeStatus, self.develStatus)))

        # Only grab from certain collections
        if name:
            # SQLAlchemy mapped classes are monkey patched
            # pylint: disable-msg=E1101
            query = query.where(Collection.name==name)
            if version:
                # Limit the versions of those collections
                query = query.where(Collection.version==version)

        pkgs = {}
        # turn the query into a python object
        for pkg in query.execute():
            additions = []
            for userid in (pkg[1], pkg[2]):
                try:
                    additions.append(self.fas.cache[userid]['username'])
                except KeyError: # pylint: disable-msg=W0704
                    # We get here when we have a Null in the data (perhaps
                    # there was no one on the CC list.)  This is not an error.
                    pass
            try:
                pkgs[pkg[0]].update(additions)
            except KeyError:
                pkgs[pkg[0]] = set(additions)

        # SQLAlchemy mapped classes are monkey patched
        # pylint: disable-msg=E1101
        # Retrieve list of collection information for generating the
        # collection form
        collection_list = Collection.query.order_by('name').order_by('version')
        # pylint: enable-msg=E1101
        collections = {}
        for collection in collection_list:
            try:
                collections[collection.name].append(collection.version)
            except KeyError:
                collections[collection.name] = [collection.version]

        # Return the data
        return dict(title='%s -- Notification List' % self.app_title,
                packages=pkgs, collections=collections, name=name,
                version=version, eol=eol)
