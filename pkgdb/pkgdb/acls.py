# -*- coding: utf-8 -*-
import sqlalchemy
from turbogears import controllers, expose
from pkgdb import model

CVSEXTRAS_ID=100300
ORPHAN_ID=9900

class AclList(object):
    def __init__(self, people=None, groups=None):
        self.people = people or []
        self.groups = groups or []

    def __json__(self):
        return {'people' : self.people,
                'groups' : self.groups
                }

class BugzillaInfo(object):
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
    def __init__(self, fas=None, appTitle=None):
        self.fas = fas
        self.appTitle = appTitle

    def _add_to_bugzilla_acl_list(self, packageAcls, acl, pkgName,
            collectionName, identity, group=None):
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
            except KeyError, e:
                package.cclist = AclList(groups=[identity])
        else:
            try:
                package.cclist.people.append(identity)
            except KeyError, e:
                package.cclist = AclList(people=[identity])

    def _add_to_vcs_acl_list(self, packageAcls, acl, pkgName, branchName,
            identity, group=None):
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
            except KeyError, e:
                branch[acl] = AclList(groups=[identity])
        else:
            try:
                branch[acl].people.append(identity)
            except KeyError, e:
                branch[acl] = AclList(people=[identity])

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
        # Cache the last userId
        userId = None

        # Get the vcs group acls from the db
        groupAcls = sqlalchemy.select((model.Package.c.name,
            model.Branch.c.branchname), sqlalchemy.and_(
                model.GroupPackageListing.c.groupid == CVSEXTRAS_ID,
                model.GroupPackageListingAcl.c.acl=='commit',
                model.GroupPackageListingAcl.c.statuscode == model.StatusTranslation.c.statuscodeid,
                model.StatusTranslation.c.statusname=='Approved',
                model.GroupPackageListingAcl.c.grouppackagelistingid == model.GroupPackageListing.c.id,
                model.GroupPackageListing.c.packagelistingid == model.PackageListing.c.id,
                model.PackageListing.c.packageid == model.Package.c.id,
                model.PackageListing.c.collectionid == model.Collection.c.id,
                model.Branch.c.collectionid == model.Collection.c.id
                )
            )
        # Save them into a python data structure
        for record in groupAcls.execute():
            self._add_to_vcs_acl_list(packageAcls, 'commit',
                    record[0], record[1],
                    'cvsextras', group=True)
        del groupAcls

        # Get the package owners from the db
        ownerAcls = sqlalchemy.select((model.Package.c.name,
            model.Branch.c.branchname, model.PackageListing.c.owner),
            sqlalchemy.and_(
                model.PackageListing.c.packageid==model.Package.c.id,
                model.PackageListing.c.collectionid==model.Collection.c.id,
                model.Collection.c.id==model.Branch.c.collectionid
                ),
            order_by=(model.PackageListing.c.owner,)
            )

        # Save them into a python data structure
        for record in ownerAcls.execute():
            if record[2] == ORPHAN_ID:
                # We don't want the orphan pseudo user to show up in the acls
                continue
            # Cache the userId/username  so we don't have to call the fas
            # for all packages
            if userId != record[2]:
                fasPerson, group = self.fas.get_user_info(record[2])
                username = fasPerson['username']
                userId = record[2]
            self._add_to_vcs_acl_list(packageAcls, 'commit',
                    record[0], record[1],
                    username, group=False)
        del ownerAcls

        # Get the vcs user acls from the db
        personAcls = sqlalchemy.select((model.Package.c.name,
            model.Branch.c.branchname, model.PersonPackageListing.c.userid),
            sqlalchemy.and_(
                model.PersonPackageListingAcl.c.acl=='commit',
                model.PersonPackageListingAcl.c.statuscode == model.StatusTranslation.c.statuscodeid,
                model.StatusTranslation.c.statusname=='Approved',
                model.PersonPackageListingAcl.c.personpackagelistingid == model.PersonPackageListing.c.id,
                model.PersonPackageListing.c.packagelistingid == model.PackageListing.c.id,
                model.PackageListing.c.packageid == model.Package.c.id,
                model.PackageListing.c.collectionid == model.Collection.c.id,
                model.Branch.c.collectionid == model.Collection.c.id
                ),
            order_by=(model.PersonPackageListing.c.userid,)
            )
        # Save them into a python data structure
        for record in personAcls.execute():
            # Cache the userId/username  so we don't have to call the fas
            # for all packages
            if userId != record[2]:
                fasPerson, group = self.fas.get_user_info(record[2])
                username = fasPerson['username']
                userId = record[2]

            self._add_to_vcs_acl_list(packageAcls, 'commit',
                    record[0], record[1],
                    username, group=False)

        return dict(title=self.appTitle + ' -- VCS ACLs', packageAcls=packageAcls)

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
        userId = None

        # select all packages
        packageInfo = sqlalchemy.select((model.Collection.c.name,
            model.Package.c.name, model.PackageListing.c.owner,
            model.PackageListing.c.qacontact, model.Package.c.summary),
            sqlalchemy.and_(
                model.Collection.c.id==model.PackageListing.c.collectionid,
                model.Package.c.id==model.PackageListing.c.packageid
                ),
            order_by=(model.PackageListing.c.owner,), distinct=True)

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
            if userId != pkg[2]:
                fasPerson, group = self.fas.get_user_info(pkg[2])
                username = fasPerson['username']
                userId = pkg[2]
            package.owner = username
            if pkg[3]:
                fasPerson, group = self.fas.get_user_info(pkg[3])
                package.qacontact = fasPerson['username']
            package.summary = pkg[4]

        # Retrieve the user acls
        personAcls = sqlalchemy.select((model.Package.c.name,
            model.Collection.c.name, model.PersonPackageListing.c.userid),
            sqlalchemy.and_(
                model.PersonPackageListingAcl.c.acl == 'watchbugzilla',
                model.PersonPackageListingAcl.c.statuscode == model.StatusTranslation.c.statuscodeid,
                model.StatusTranslation.c.statusname == 'Approved',
                model.PersonPackageListingAcl.c.personpackagelistingid == model.PersonPackageListing.c.id,
                model.PersonPackageListing.c.packagelistingid == model.PackageListing.c.id,
                model.PackageListing.c.packageid == model.Package.c.id,
                model.PackageListing.c.collectionid == model.Collection.c.id
                ),
            order_by=(model.PersonPackageListing.c.userid,), distinct=True
            )
        # Save them into a python data structure
        for record in personAcls.execute():
            # Cache the userId/username  so we don't have to call the fas
            # for all packages
            if userId != record[2]:
                fasPerson, group = self.fas.get_user_info(record[2])
                username = fasPerson['username']
                userId = record[2]

            self._add_to_bugzilla_acl_list(bugzillaAcls, 'watchbugzilla',
                    record[0], record[1], username, group=False)

        ### TODO: No group acls at the moment
        # There are no group acls to take advantage of this.
        return dict(title=self.appTitle + ' -- Bugzilla ACLs', bugzillaAcls=bugzillaAcls)
