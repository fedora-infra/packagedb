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

import sqlalchemy
from turbogears import controllers, expose
from pkgdb import model

CVSEXTRAS_ID = 100300
ORPHAN_ID = 9900

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

class Acls(controllers.Controller):
    '''Controller for lists of acl/owner information needed by external tools.

    Although these methods can return web pages, the main feature is the json
    and plain text that they return as the main usage of this is for external
    tools to take data for their use.
    '''
    # pylint: disable-msg=E1101
    approvedStatus = model.StatusTranslation.query.filter_by(
            statusname='Approved', language='C').one().statuscodeid
    removedStatus = model.StatusTranslation.query.filter_by(
            statusname='Removed', language='C').one().statuscodeid
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
    
        groupAcls = sqlalchemy.select((
            # pylint: disable-msg=E1101
            model.Package.c.name,
            model.Branch.c.branchname), sqlalchemy.and_(
                model.GroupPackageListing.c.groupid == CVSEXTRAS_ID,
                model.GroupPackageListingAcl.c.acl == 'commit',
                model.GroupPackageListingAcl.c.statuscode \
                        == self.approvedStatus,
                model.GroupPackageListingAcl.c.grouppackagelistingid \
                        == model.GroupPackageListing.c.id,
                model.GroupPackageListing.c.packagelistingid \
                        == model.PackageListing.c.id,
                model.PackageListing.c.packageid == model.Package.c.id,
                model.PackageListing.c.collectionid == model.Collection.c.id,
                model.Branch.c.collectionid == model.Collection.c.id,
                model.PackageListing.c.statuscode != self.removedStatus,
                model.Package.c.statuscode != self.removedStatus
                )
            )

        # Save them into a python data structure
        for record in groupAcls.execute():
            self._add_to_vcs_acl_list(packageAcls, 'commit',
                    record[0], record[1],
                    'cvsextras', group=True)
        del groupAcls

        # Get the package owners from the db
        # Exclude the orphan user from that.
        ownerAcls = sqlalchemy.select((
            # pylint: disable-msg=E1101
            model.Package.c.name,
            model.Branch.c.branchname, model.PackageListing.c.owner),
            sqlalchemy.and_(
                model.PackageListing.c.packageid==model.Package.c.id,
                model.PackageListing.c.collectionid==model.Collection.c.id,
                model.PackageListing.c.owner!=ORPHAN_ID,
                model.Collection.c.id==model.Branch.c.collectionid,
                model.PackageListing.c.statuscode != self.removedStatus,
                model.Package.c.statuscode != self.removedStatus
                ),
            order_by=(model.PackageListing.c.owner,)
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
        personAcls = sqlalchemy.select((
            # pylint: disable-msg=E1101
            model.Package.c.name,
            model.Branch.c.branchname, model.PersonPackageListing.c.userid),
            sqlalchemy.and_(
                model.PersonPackageListingAcl.c.acl=='commit',
                model.PersonPackageListingAcl.c.statuscode \
                        == model.StatusTranslation.c.statuscodeid,
                model.StatusTranslation.c.statusname=='Approved',
                model.PersonPackageListingAcl.c.personpackagelistingid \
                        == model.PersonPackageListing.c.id,
                model.PersonPackageListing.c.packagelistingid \
                        == model.PackageListing.c.id,
                model.PackageListing.c.packageid == model.Package.c.id,
                model.PackageListing.c.collectionid == model.Collection.c.id,
                model.Branch.c.collectionid == model.Collection.c.id,
                model.PackageListing.c.statuscode != self.removedStatus,
                model.Package.c.statuscode != self.removedStatus
                ),
            order_by=(model.PersonPackageListing.c.userid,)
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

        # select all packages that are active
        packageInfo = sqlalchemy.select((
            # pylint: disable-msg=E1101
            model.Collection.c.name, model.Package.c.name,
            model.PackageListing.c.owner, model.PackageListing.c.qacontact,
            model.Package.c.summary),
            sqlalchemy.and_(
                model.Collection.c.id==model.PackageListing.c.collectionid,
                model.Package.c.id==model.PackageListing.c.packageid,
                model.Package.c.statuscode==self.approvedStatus,
                model.PackageListing.c.statuscode==self.approvedStatus
                ),
            order_by=(model.PackageListing.c.owner,), distinct=True)

        # Cache the userId/username pairs so we don't have to call the
        # fas for every package.
        userList = self.fas.user_id()

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
            package.owner = userList[pkg[2]]
            if pkg[3]:
                package.qacontact = userList[pkg[3]]
            package.summary = pkg[4]

        # Retrieve the user acls

        personAcls = sqlalchemy.select((
            # pylint: disable-msg=E1101
            model.Package.c.name,
            model.Collection.c.name, model.PersonPackageListing.c.userid),
            sqlalchemy.and_(
                model.PersonPackageListingAcl.c.acl == 'watchbugzilla',
                model.PersonPackageListingAcl.c.statuscode \
                        == self.approvedStatus,
                model.PersonPackageListingAcl.c.personpackagelistingid \
                        == model.PersonPackageListing.c.id,
                model.PersonPackageListing.c.packagelistingid \
                        == model.PackageListing.c.id,
                model.PackageListing.c.packageid == model.Package.c.id,
                model.PackageListing.c.collectionid == model.Collection.c.id,
                model.Package.c.statuscode==self.approvedStatus,
                model.PackageListing.c.statuscode==self.approvedStatus
                ),
            order_by=(model.PersonPackageListing.c.userid,), distinct=True
            )
        
        # Save them into a python data structure
        for record in personAcls.execute():
            username = userList[record[2]]
            self._add_to_bugzilla_acl_list(bugzillaAcls, record[1],
                    username, group=False)

        ### TODO: No group acls at the moment
        # There are no group acls to take advantage of this.
        return dict(title=self.appTitle + ' -- Bugzilla ACLs',
                bugzillaAcls=bugzillaAcls)
