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
    from fedora.tg.util import request_format
    import cherrypy
    def jsonify_validation_errors():
        # Check for validation errors
        errors = getattr(cherrypy.request, 'validation_errors', None)
        if not errors:
            return None

        # Set the message for both html and json output
        format = request_format()
        if format == 'html':
            separator = u'<br />'
        else:
            separator = u'\n'
        message = separator.join([u'%s: %s' % (param, msg) for param, msg in
            errors.items()])
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

class Acls(controllers.Controller):
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
        self.appTitle = appTitle

    def _add_to_bugzilla_acl_list(self, packageAcls, pkgName,
            collectionName, identity, group=None):
        '''Add the given acl to the list of acls for bugzilla.

        Arguments:
        :packageAcls: The data structure to fill
        :pkgName: Name of the package we're setting the acl on
        :collectionName: Name of the bugzilla collection on which we're
            setting the acl.
        :identity: The id of the user or group for whom the acl is being set.
        :group: If set, we're dealing with a group instead of a person.
        '''
        # Lookup the collection
        try:
            collection = packageAcls[collectionName]
        except KeyError:
            collection = {}
            packageAcls[collectionName] = collection
        # Then the package
        try:
            package = collection[pkgName]
        except KeyError:
            package = BugzillaInfo()
            collection[pkgName] = package
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

    def _add_to_vcs_acl_list(self, packageAcls, acl, pkgName, branchName,
            identity, group=None):
        '''Add the given acl to the list of acls for the vcs.

        Arguments:
        :packageAcls: The data structure to fill
        :acl: The acl to create
        :pkgName: Name of the package we're setting the acl on
        :branchName: Name of the branch for which hte acl is being set
        :identity: The id of the user or group for whom the acl is being set.
        :group: If set, we're dealing with a group instead of a person.
        '''
        # Key by package name
        try:
            pkg = packageAcls[pkgName]
        except KeyError:
            pkg = {}
            packageAcls[pkgName] = pkg

        # Then by branch name
        try:
            branch = pkg[branchName]
        except KeyError:
            branch = {}
            pkg[branchName] = branch

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
        packageAcls = {}

        # Get the vcs group acls from the db

        groupAcls = select((
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
        for record in groupAcls.execute():
            if not record[2] in groups:
                groups[record[2]] = self.fas.group_by_id(record[2])['name']
            self._add_to_vcs_acl_list(packageAcls, 'commit',
                    record[0], record[1],
                    groups[record[2]], group=True)
        del groupAcls

        # Get the package owners from the db
        # Exclude the orphan user from that.
        ownerAcls = select((
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
        userList = self.fas.user_id()

        # Save them into a python data structure
        for record in ownerAcls.execute():
            username = userList[record[2]]
            self._add_to_vcs_acl_list(packageAcls, 'commit',
                    record[0], record[1],
                    username, group=False)
        del ownerAcls

        # Get the vcs user acls from the db
        personAcls = select((
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
        for record in personAcls.execute():
            username = userList[record[2]]
            self._add_to_vcs_acl_list(packageAcls, 'commit',
                    record[0], record[1],
                    username, group=False)

        return dict(title=self.appTitle + ' -- VCS ACLs',
                packageAcls=packageAcls)

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
        bugzillaAcls = {}
        username = None

        # select all packages that are active in an active release
        packageInfo = select((
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
        userList = self.fas.user_id()

        # List of packages that need more processing to decide who the owner
        # should be.
        undupeOwners = []

        for pkg in packageInfo.execute():
            # Lookup the collection
            collectionName = pkg[0]
            try:
                collection = bugzillaAcls[collectionName]
            except KeyError:
                collection = {}
                bugzillaAcls[collectionName] = collection
            # Then the package
            packageName = pkg[1]
            try:
                package = collection[packageName]
            except KeyError:
                package = BugzillaInfo()
                collection[packageName] = package

            # Save the package information in the data structure to return
            if not package.owner:
                package.owner = userList[pkg[2]]
            elif userList[pkg[2]] != package.owner:
                # There are multiple owners for this package.
                undupeOwners.append(packageName)
            if pkg[3]:
                package.qacontact = userList[pkg[3]]
            package.summary = pkg[4]

        if undupeOwners:
            # These are packages that have different owners in different
            # branches.  Need to find one to be the owner of the bugzilla
            # component
            packageInfo = select((Collection.name,
                Collection.version,
                Package.name, PackageListing.owner),
                and_(
                    Collection.id==PackageListing.collectionid,
                    Package.id==PackageListing.packageid,
                    Package.statuscode==self.approvedStatus,
                    PackageListing.statuscode==self.approvedStatus,
                    Collection.statuscode.in_((self.activeStatus,
                        self.develStatus)),
                    Package.name.in_(undupeOwners),
                    ),
                order_by=(Collection.name, Collection.version),
                distinct=True)

            # Organize the results so that we have:
            # [packagename][collectionname][collectionversion] = owner
            byPkg = {}
            for pkg in packageInfo.execute():
                # Order results by package
                try:
                    package = byPkg[pkg[2]]
                except KeyError:
                    package = {}
                    byPkg[pkg[2]] = package

                # Then collection
                try:
                    collection = package[pkg[0]]
                except KeyError:
                    collection = {}
                    package[pkg[0]] = collection

                # Then collection version == owner
                collection[pkg[1]] = pkg[3]

            # Find the proper owner
            for pkg in byPkg:
                for collection in byPkg[pkg]:
                    if collection == 'Fedora':
                        # If devel exists, use its owner
                        # We can safely ignore orphan because we already know
                        # this is a dupe and thus a non-orphan exists.
                        if 'devel' in byPkg[pkg][collection]:
                            if byPkg[pkg][collection]['devel'] == ORPHAN_ID \
                                    and len(byPkg[pkg][collection]) > 1:
                                # If there are other owners, try to use them
                                # instead of orphan
                                del byPkg[pkg][collection]['devel']
                            else:
                                # Prefer devel above all others
                                bugzillaAcls[collection][pkg].owner = \
                                    userList[byPkg[pkg][collection]['devel']]
                                continue

                    # For any collection except Fedora or Fedora if the devel
                    # version does not exist, treat releases as numbers and
                    # take the results from the latest number
                    releases = [int(r) for r in byPkg[pkg][collection] \
                            if byPkg[pkg][collection][r] != ORPHAN_ID]
                    if not releases:
                        # Every release was an orphan
                        bugzillaAcls[collection][pkg].owner = \
                                userList[ORPHAN_ID]
                    else:
                        releases.sort()
                        bugzillaAcls[collection][pkg].owner = \
                                userList[byPkg[pkg][collection][ \
                                    unicode(releases[-1])]]

        # Retrieve the user acls

        personAcls = select((
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
        for record in personAcls.execute():
            username = userList[record[2]]
            self._add_to_bugzilla_acl_list(bugzillaAcls, record[0], record[1],
                    username, group=False)

        ### TODO: No group acls at the moment
        # There are no group acls to take advantage of this.
        return dict(title=self.appTitle + ' -- Bugzilla ACLs',
                bugzillaAcls=bugzillaAcls)

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

        # Retrieve Packages, owners, and people on watch* acls
        query = select((Package.name, PackageListing.owner,
            PersonPackageListing.userid),
            from_obj=(PackageTable.join(PackageListing).outerjoin(
                PersonPackageListing).outerjoin(PersonPackageListingAcl),
                CollectionTable)
            ).where(or_(PersonPackageListingAcl.acl.in_(
                ('watchbugzilla', 'watchcommits')),
                PersonPackageListingAcl.acl==None)
                ).where(Collection.id==PackageListing.collectionid
                        ).distinct().order_by('name')
        if not eol:
            # Filter out eol distributions
            query = query.where(Collection.statuscode.in_(
                (self.activeStatus, self.develStatus)))

        # Only grab from certain collections
        if name:
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
                except KeyError:
                    # We get here when we have a Null in the data (perhaps
                    # there was no one on the CC list.)
                    pass
            try:
                pkgs[pkg[0]].update(additions)
            except KeyError:
                pkgs[pkg[0]] = set(additions)

        # Retrieve list of collection information for generating the
        # collection form
        collectionList = Collection.query.order_by('name').order_by('version')
        collections = {}
        for collection in collections:
            try:
                collections[collection.name].append(collection.version)
            except KeyError:
                collections[collection.name] = [collection.version]

        # Return the data
        return dict(title='%s -- Notification List' % self.appTitle,
                packages=pkgs, collections=collections, name=name,
                version=version, eol=eol)
