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

class Acls(controllers.Controller):
    def __init__(self, fas=None, appTitle=None):
        self.fas = fas
        self.appTitle = appTitle

    def _add_person_to_acl(self, packageAcls, acl, pkgName, branchName,
            username):
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
        try:
            branch[acl].people.append(username)
        except KeyError, e:
            branch[acl] = AclList(people=[username])

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
            # Key by package name
            try:
                pkg = packageAcls[record[0]]
            except KeyError:
                pkg = {}
                packageAcls[record[0]] = pkg

            # Then by branch name
            try:
                branch = pkg[record[1]]
            except KeyError:
                branch = {}
                pkg[record[1]] = branch

            # Add these acls to the group acls
            try:
                branch['commit'].groups.append('cvsextras')
            except KeyError:
                branch['commit'] = AclList(groups=['cvsextras'])
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
            # Cache the userId/username  so we don't have to call the fas
            # for all packages
            if userId == ORPHAN_ID:
                # We don't want the orphan pseudo user to show up in the acls
                continue
            if userId != record[2]:
                fasPerson, group = self.fas.get_user_info(record[2])
                username = fasPerson['username']
                userId = record[2]
            self._add_person_to_acl(packageAcls, 'commit', record[0], record[1],
                    username)
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

            self._add_person_to_acl(packageAcls, 'commit', record[0], record[1],
                    username)

        return dict(title=self.appTitle + ' -- VCS ACLs', packageAcls=packageAcls)
