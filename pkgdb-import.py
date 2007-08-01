#!/usr/bin/python -tt
'''Import owner and acl information from the cvs repository into the pkgdb.

Caveats:
Assumes that owners.epel.list has a subset of the packages in owners.list.
ATM this is true.

Set CVSROOT=/cvs/pkgs before running

Fill in dbPass and fasPass in the source before running
'''

import sys
import re
import logging
import psycopg2

import owners

CVSMODULEFILE='/home/fedora/toshio/CVSROOT/modules'
OWNERLIST='/home/fedora/toshio/owners/owners.list'
EPELLIST='/home/fedora/toshio/owners/owners.epel.list'
OLPCLIST='/home/fedora/toshio/owners/owners.olpc.list'
dbName='pkgdb'
dbHost='db2'
dbUser='pkgdbadmin'
dbPass=''

fasName='fedorausers'
fasHost='db2'
fasUser='apache'
fasPass=''

class CVSError(Exception):
    pass

class CVSReleases(dict):
    def __init__(self, cvspath=None):
        '''Pull information on releases from the cvs modules file.

        By the end of __init__() we should have an entry for each package that
        contains a list of (prod, release) for each product/release that it is
        a part of.

        Additionally, self.collections will contain an empty entry for each
        (prod, release) pair so we know which ones have been utilized.
        '''
        self.collections = {('Fedora', 'devel') : None}
        # If cvspath does not exist, we'll return 'devel' for any packages
        # on the fly.
        if not cvspath:
            return

        modulesRE = re.compile(r'^RHL-9\s+&common.*-dir')
        branchRE = re.compile(r'^([^ ]+)-(F|FC|RHL|EL|OLPC)-([0-9]+)-dir\s')
        develRE = re.compile(r'^([^ ]+)\srpms/\1 &common$')
        cvsFile = file(cvspath, 'r')
        records = cvsFile.readlines()

        # Check that there are no pending branches
        match = modulesRE.search(records[-1])
        if not match:
            raise CVSError, 'Branches need to be made in CVS module file before continuing'

        for entry in records:
            match = branchRE.search(entry)
            if match:
                # Save the release for the package
                package = match.group(1)
                product = match.group(2)
                release = int(match.group(3))
                if product == 'FC' or product == 'F':
                    product = 'Fedora'
                elif product == 'OLPC':
                    product = 'Fedora OLPC'
                elif product == 'EL':
                    product = 'Fedora EPEL'
                elif product == 'RHL':
                    product = 'Red Hat Linux'
                self[package].append((product, release))

                # Keep track of all the collections we're syncing
                self.collections[(product, release)] = None
            match = develRE.search(entry)
            if match:
                # There was a match for the devel branch
                self[match.group(1)].append(('Fedora', 'devel'))

    def __getitem__(self, key):
        '''Return the item with a default value.

        Return the value for key.  If the value is missing, create a default
        value of a list with the ('Fedora', 'devel') collection inside it.

        Attributes:
        key: The key to assign
        
        Return: The value for the key.
        '''
        if key in self:
            return dict.__getitem__(self, key)
        else:
            dict.__setitem__(self, key, [('Fedora', 'devel')])
            return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        '''Prevent assignments directly to this object's keys.

        '''
        raise CVSError, 'Assignment to CVSReleases not allowed; use' + \
                ' self[pkgname].append(data) instead'

class PackageDBError(Exception):
    pass

class PackageDB(object):
    '''The PackageDB we're entering information into.'''

    def __init__(self):
        '''Setup the connection to the DB.
        
        '''

        self.db = psycopg2.connect(database=dbName, host=dbHost,
                user=dbUser, password=dbPass)
        self.dbCmd = self.db.cursor()

        # Open a connection to the Fedora Account System
        self.fas = psycopg2.connect(database=fasName, host=fasHost,
                user=fasUser, password=fasPass)
        self.fasCmd = self.fas.cursor()

    def _get_userid(self, username):
        '''Retrieve a userid from the Account System.'''
        if username == 'bnocera':
            username = 'hadess'
        self.fasCmd.execute("select id from person" \
                " where username = %(name)s", {'name' : username})
        user = self.fasCmd.fetchone()
        return user[0]

    def _add_acl(self, pkgAclData):
        '''Add an acl for a packageListing.
        Use the data to set the ACL.

        :pkgAclData: The information on the ACL to set.
          This is a hash that contains: personid, status, pkgListId, and acl.
        '''
        # Get the id for the PersonPackageListing
        self.dbCmd.execute("select id from PersonPackageListing" \
                " where userid = %(personid)s" \
                " and packagelistingid = %(pkgListId)s", pkgAclData)
        personPkgListId = self.dbCmd.fetchone()
        if not personPkgListId:
            # The record does not yet exist, create it
            self.dbCmd.execute("insert into PersonPackageListing" \
                    " (userid, packagelistingid)" \
                    " values(%(personid)s, %(pkgListId)s)", pkgAclData)
            self.dbCmd.execute("select id from PersonPackageListing" \
                    " where userid = %(personid)s" \
                    " and packagelistingid = %(pkgListId)s", pkgAclData)
            personPkgListId = self.dbCmd.fetchone()
        pkgAclData['pplId'] = personPkgListId[0]

        # Get the Acl we're interested in
        self.dbCmd.execute("select id from PersonPackageListingAcl" \
                " where personPackageListingId = %(pplId)s" \
                " and acl = %(acl)s", pkgAclData)
        pplaId = self.dbCmd.fetchone()
        if pplaId:
            # Acl already exists, update.
            pkgAclData['pplaId'] = pplaId[0]
            self.dbCmd.execute("update PersonPackageListingAcl set" \
                    " statuscode = (select pasc.statusCodeId from" \
                    " PackageACLStatusCode as pasc natural join" \
                    " StatusCodeTranslation as sct" \
                    " where sct.language = 'C'" \
                    " and sct.statusName = %(status)s)" \
                    " where id = %(pplaId)s",
                    pkgAclData)
        else:
            # Acl does not exist, create.
            self.dbCmd.execute("insert into PersonPackageListingAcl" \
                    " (personPackageListingId, acl, statuscode)" \
                    " select %(pplId)s, %(acl)s, pasc.statusCodeId from" \
                    " PackageAclStatusCode as pasc natural join" \
                    " StatusCodeTranslation as sct where sct.language = 'C'" \
                    " and sct.statusName = %(status)s", pkgAclData)

    def _add_acls(self, users, pkgs, acls):
        '''Add acls for users to a list of packageListings.
        
        :users: Users to add to the ACLs.
        :pkgs: PackageListings to add the ACLs to.
        :acls: The specific ACLs that we are adding.
        '''
        if not (users and pkgs and acls):
            # If one of these is empty then we have nothing to do
            return
        for user in users:
            # Convert to a userId if necessary
            if type(user) != int:
                user = self._get_userid(user)
            pkgAclData = {'personid' : user,
                    'status' : 'Approved'}
            for pkgListId in pkgs:
                pkgAclData['pkgListId'] = pkgListId
                for acl in acls:
                    pkgAclData['acl'] = acl
                    self._add_acl(pkgAclData)

    def _add_group_acl(self, pkgAclData):
        '''Add an acl for a group.
        
        :pkgAclData: Contains the following fields: groupId, status,
          pkgListId, acl
        '''

        # Get the id for the GroupPackageListing
        self.dbCmd.execute("select gpl.id from" \
                " grouppackagelisting as gpl where" \
                " gpl.groupid = %(groupId)s" \
                " and gpl.packageListingId = %(pkgListId)s", pkgAclData)
        gplId = self.dbCmd.fetchone()
        if not gplId:
            self.dbCmd.execute("insert into GroupPackageListing" \
                    " (groupid, packageListingId)" \
                    " values (%(groupId)s, %(pkgListId)s)", pkgAclData)
            self.dbCmd.execute("select id from grouppackagelisting" \
                    " where groupid = %(groupId)s" \
                    " and packagelistingid = %(pkgListId)s", pkgAclData)
            gplId = self.dbCmd.fetchone()
        pkgAclData['gplId'] = gplId[0]

        # Get the acl we're interested in
        self.dbCmd.execute("select id from GroupPackageListingAcl" \
                " where groupPackageListingId = %(gplId)s" \
                " and acl = %(acl)s", pkgAclData)
        gplaId = self.dbCmd.fetchone()
        if gplaId:
            # Acl already exists, update.
            pkgAclData['gplaId'] = gplaId[0]
            self.dbCmd.execute("update GroupPackageListingAcl set" \
                    " statuscode = (select pasc.statusCodeId from" \
                    " PackageACLStatusCode as pasc natural join" \
                    " StatusCodeTranslation as sct" \
                    " where sct.language = 'C'" \
                    " and sct.statusName = %(status)s)" \
                    " where id = %(gplaId)s",
                    pkgAclData)
        else:
            # Create the acl
            self.dbCmd.execute("insert into GroupPackageListingAcl" \
                    " (groupPackageListingId, acl, statuscode)" \
                    " select %(gplId)s, %(acl)s, pasc.statusCodeId from" \
                    " PackageAclStatusCode as pasc natural join" \
                    " StatusCodeTranslation as sct where sct.language = 'C'" \
                    " and sct.statusName = %(status)s", pkgAclData)

    def _add_group_acls(self, groupIds, pkgListings, acls):
        '''Add acls for a group.
        '''
        if not (groupIds and pkgListings and acls):
            # If one of these is empty we have nothing to do
            return

        for groupId in groupIds:
            pkgAclData = {'groupId' : groupId,
                    'status' : 'Approved'}
            for pkgListId in pkgListings:
                pkgAclData['pkgListId'] = pkgListId
                for acl in acls:
                    pkgAclData['acl'] = acl
                    self._add_group_acl(pkgAclData)

    def import_data(self, fedoraOwners, epelOwners, olpcOwners, cvs, updatedb):
        '''Import data from owners and cvs into the DB.

        :fedoraOwners: The information from owners.list
        :epelOwners: Information from owners.epel.list
        :olpcOwners: Information from owners.olpc.list
        :cvs: Information from the cvs repo.
        :updatedb: If this is True, update the db with our data, otherwise,
            discard any data we have in favor of the data already in the db.
        '''
        # Get the id for any collections we are going to be adding packages
        # to, creating any that do not already exist.
        collectionNumbers = {}
        for collection in cvs.collections.keys():
            product, release = collection
            collectionData = {'collection' : product,
                    'release' : release}
            self.dbCmd.execute("select id from collection" \
                    " where name = %(collection)s" \
                    " and version = %(release)s",
                    collectionData)
            collectionInfo = self.dbCmd.fetchone()
            if not collectionInfo:
                # This collection is not yet known, create it.  At least
                # status and owner should be changed before deployment.
                # (100068 is toshio's account).  Note: Calling
                # set_collection_status() and set_collection_owner()
                # will do this.
                collectionData.update({'status' : 'EOL', 'user' : 100068})
                self.dbCmd.execute("insert into collection" \
                        " (name, version, statuscode, owner)" \
                        " select %(collection)s, %(release)s," \
                        " CollectionStatusCode.statusCodeId, %(user)s" \
                        " from CollectionStatusCode" \
                        " natural join StatusCodeTranslation as sct" \
                        " where sct.language = 'C' " \
                        " and sct.statusName = %(status)s",
                        collectionData)
                self.db.commit()
                logging.warning('Created new collection %(collection)s' \
                        ' %(release)s.  Please update statuscode, and ownership' \
                        ' information for this release.' % collectionData)
                self.dbCmd.execute("select id from collection" \
                        " where name = %(collection)s" \
                        " and version = %(release)s",
                        collectionData)
                collectionInfo = self.dbCmd.fetchone()

            # Save the collection id so we can look it up later
            if not collectionNumbers.has_key(collection):
                collectionNumbers[collection] = {}
            collectionNumbers[collection] = collectionInfo[0]

        # Import each package that was listed in the owners.list file.
        for pkg in fedoraOwners.getPackageList():
            # Skip "buildsystem" as it isn't a real package.  It's in
            # owners.list in order to get a component in bugzilla.
            if pkg in ('buildsystem', 'kadischi', 'general', 'comps'):
                continue
            # Add the packages into the database
            pkgData = {'pkg' : pkg,
                    'summary': fedoraOwners.getPackageSummary(pkg),
                    'status': 'Approved'}
            try:
                self.dbCmd.execute("insert into package" \
                        " (name, summary, statuscode)" \
                        " select %(pkg)s, %(summary)s," \
                        " PackageStatusCode.statusCodeId" \
                        " from PackageStatusCode natural join" \
                        " StatusCodeTranslation as sct where" \
                        " sct.language = 'C' and sct.statusName = %(status)s",
                        pkgData)
            except psycopg2.IntegrityError, e:
                if e.pgcode != '23505':
                    raise e
                self.db.rollback()
                # This package is already in the database.
                # If the user explicitly asked to update the db with new data,
                # do that, otherwise, discard the duplicate packages.
                if updatedb:
                    # User wants to update
                    self.dbCmd.execute("update package" \
                            " set summary = %(summary)s" \
                            " where name = %(pkg)s",
                            pkgData)
           
            self.dbCmd.execute("select id from package" \
                    " where name = %(pkg)s", pkgData)
            pkgId = self.dbCmd.fetchone()[0]

            # Associate the package with one or more collections
            fedoraPkgListNumbers = {}
            epelPkgListNumbers = {}
            olpcPkgListNumbers = {}
            pkgListData = {'pkgId' : pkgId,
                    'status' : 'Approved'}
            # Create a PackageListing entry for each release that the package
            # is available.
            for collection in cvs[pkg]:
                # Get the id for the (prod, release)
                pkgListData['collectId'] = collectionNumbers[collection]

                # Retrieve the owner information.  EPEL branches may have a
                # different owner than the other branches.
                if collection[0] == 'Fedora EPEL':
                    # Get owner information from the owner.epel.list
                    if not epelOwners.getOwnerAccounts(pkg):
                        logging.warning('%s has no legal owner in owners.epel.list' % pkg)
                        continue
                    owner = epelOwners.getOwnerAccounts(pkg)[0]
                elif collection[0] == 'Fedora OLPC':
                    # Get owner information from owner.olpc.list
                    if not olpcOwners.getOwnerAccounts(pkg):
                        logging.warning('%s has no legal owner in owners.olpc.list' % pkg)
                        continue
                    owner = olpcOwners.getOwnerAccounts(pkg)[0]
                else:
                    # Get owner information from owner.list
                    if not fedoraOwners.getOwnerAccounts(pkg):
                        logging.warning('%s has no legal owner in owners.list' % pkg)
                        continue
                    owner = fedoraOwners.getOwnerAccounts(pkg)[0]
                # PackageDB stores things according to fas id so we need to
                # look that up:
                pkgListData['owner'] = self._get_userid(owner)
                if not pkgListData['owner']:
                    # The username wasn't in fas... log an error
                    logging.warning('Unable to retrieve a userid from the fas' \
                            ' for user %s.  Skipping package %s in %s' % (
                                owner, pkg, collection))
                    continue

                # Find out if we already have a listing
                self.dbCmd.execute("select id from PackageListing" \
                        " where packageId = %(pkgId)s and" \
                        " collectionId = %(collectId)s", pkgListData)
                pkgListNum = self.dbCmd.fetchone()
                if not pkgListNum:
                    # No listing, create one
                    self.dbCmd.execute("insert into PackageListing" \
                            " (packageId, collectionId, owner, statuscode)" \
                            " select %(pkgId)s, %(collectId)s, %(owner)s," \
                            " plsc.statusCodeId from" \
                            " PackageListingStatusCode as plsc natural join" \
                            " StatusCodeTranslation as sct" \
                            " where sct.language = 'C' and" \
                            " sct.statusName = %(status)s", pkgListData)
                    self.dbCmd.execute("select id from PackageListing" \
                            " where packageId = %(pkgId)s and" \
                            " collectionId = %(collectId)s", pkgListData)
                    pkgListNum = self.dbCmd.fetchone()
                elif updatedb:
                    # listing exists but want to update to latest info
                    self.dbCmd.execute("update PackageListing" \
                            " set owner = %(owner)s" \
                            " where packageId = %(pkgId)s" \
                            " and collectionId = %(collectId)s", pkgListData)

                pkgListId = pkgListNum[0]
                if collection[0] == 'Fedora EPEL':
                    # Save this as an EPEL Package
                    epelPkgListNumbers[(pkgListData['collectId'], pkg)] = pkgListId
                elif collection[0] == 'Fedora OLPC':
                    # Save this as an OLPC Package
                    olpcPkgListNumbers[(pkgListData['collectId'], pkg)] = pkgListId
                else:
                    # Save this as a Fedora Package
                    fedoraPkgListNumbers[(pkgListData['collectId'], pkg)] = pkgListId
                # Set up Restrictions setup by pkg.acl files

                # Get the users in the acl for this collection
                if collection[0] == 'Fedora EPEL':
                    aclUsers = fedoraOwners.getAclAccounts(pkg,
                            'EL-' + str(collection[1]))
                elif collection[0] == 'Fedora OLPC':
                    aclUsers = fedoraOwners.getAclAccounts(pkg,
                            'OLPC-' + str(collection[1]))
                elif collection[0] == 'Fedora' and collection[1] == '7':
                    # From 7 on, the collection was named Fedora
                    aclUsers = fedoraOwners.getAclAccounts(pkg,
                            'F-' + str(collection[1]))
                elif collection[0] == 'Fedora' and collection[1] == 'devel':
                    # devel is simply devel
                    aclUsers = fedoraOwners.getAclAccounts(pkg,
                            'devel')
                elif collection[0] == 'Fedora':
                    # All other Fedora versions
                    aclUsers = fedoraOwners.getAclAccounts(pkg,
                            'FC-' + str(collection[1]))
                elif collection[0] == 'Red Hat Linux':
                    aclUsers = fedoraOwners.getAclAccounts(pkg,
                            'RHL-' + str(collection[1]))

                if aclUsers == None:
                    # When no acl is specified, cvsextras has full access
                    # cvsextras is id 100300
                    self._add_group_acls((100300,), (pkgListId,),
                            ('commit', 'build', 'checkout'))
                else:
                    # Acl specified -- cvsextras is restricted
                    self._add_group_acls((100300,), (pkgListId,), ('checkout',))

                    fedoraMaintainers = fedoraOwners.getOwnerAccounts(pkg)
                    epelMaintainers = epelOwners.getOwnerAccounts(pkg)
                    olpcMaintainers = olpcOwners.getOwnerAccounts(pkg)
                    # Set up anyone else that is listed in pkg.acl
                    for user in aclUsers:
                        if collection[0] == 'Fedora EPEL':
                            # EPEL branch
                            if user in epelMaintainers:
                                # This acl is for a maintainer.  Skip as we
                                # assign their acls below.
                                continue
                        elif collection[0] == 'Fedora OLPC':
                            # OLPC Branch
                            if user in olpcMaintainers:
                                # This acl is for a maintainer.  Skip as we
                                # assign their acls below.
                                continue
                        else:
                            # Fedora, Fedora Extras, or RHL Branch
                            if user in fedoraMaintainers:
                                # This acl is for a maintainer.  Skip as we
                                # assign their acls below.
                                continue
                        self._add_acls([user], [pkgListId],
                                ('commit', 'watchcommits', 'checkout', 'build'))

            # Set up watchers
            self._add_acls(fedoraOwners.getCCListAccounts(pkg),
                    fedoraPkgListNumbers.values(),
                    ('watchbugzilla', 'watchcommits'))
            self._add_acls(epelOwners.getCCListAccounts(pkg),
                    epelPkgListNumbers.values(),
                    ('watchbugzilla', 'watchcommits'))
            self._add_acls(olpcOwners.getCCListAccounts(pkg),
                    olpcPkgListNumbers.values(),
                    ('watchbugzilla', 'watchcommits'))
            # Set up comaintainers
            if fedoraOwners.getOwnerAccounts(pkg):
                self._add_acls(fedoraOwners.getOwnerAccounts(pkg)[1:],
                        fedoraPkgListNumbers.values(),
                        ('commit', 'build', 'watchcommits', 'watchbugzilla',
                            'approveacls', 'checkout'))
            if epelOwners.getOwnerAccounts(pkg):
                self._add_acls(epelOwners.getOwnerAccounts(pkg)[1:],
                        epelPkgListNumbers.values(),
                        ('commit', 'build', 'watchcommits', 'watchbugzilla',
                            'approveacls', 'checkout'))
            if olpcOwners.getOwnerAccounts(pkg):
                self._add_acls(olpcOwners.getOwnerAccounts(pkg)[1:],
                        olpcPkgListNumbers.values(),
                        ('commit', 'build', 'watchcommits', 'watchbugzilla',
                            'approveacls', 'checkout'))

            self.db.commit()

    def set_collection_status(self):
        '''Set the collection status fields.

        Collections are initialized to EOL.  We want to set certain one to be
        active instead.

        This is not being retrieved from any canonical data source, it's just
        knowledge about certain collections that we know about.
        '''
        self.dbCmd.execute("update collection set statuscode=("
                " select csc.statusCodeId from CollectionStatusCode as csc"
                " natural join StatusCodeTranslation as sct"
                " where sct.language = 'C'"
                " and sct.statusName ='Under Development')"
                " where version='devel'")
        self.dbCmd.execute("update collection set statuscode=("
                " select csc.statusCodeId from CollectionStatusCode as csc"
                " natural join StatusCodeTranslation as sct"
                " where sct.language = 'C'"
                " and sct.statusName ='Active')"
                " where name = 'Fedora'"
                " and version in ('5', '6', '7')")
        self.dbCmd.execute("update collection set statuscode=("
                " select csc.statusCodeId from CollectionStatusCode as csc"
                " natural join StatusCodeTranslation as sct"
                " where sct.language = 'C'"
                " and sct.statusName ='Active')"
                " where name = 'Fedora EPEL'"
                " and version in ('4', '5')")
        self.dbCmd.execute("update collection set statuscode=("
                " select csc.statusCodeId from CollectionStatusCode as csc"
                " natural join StatusCodeTranslation as sct"
                " where sct.language = 'C'"
                " and sct.statusName ='Active')"
                " where name = 'Fedora OLPC'"
                " and version = '2'")
        self.db.commit()

    def set_collection_owner(self):
        '''Set the collection owner.
        
        Currently setting all collections as owned by Jesse Keating
        jkeating@redhat.com 100351
        This information needs to be filled out.
        '''
        self.dbCmd.execute("update collection set owner=100351")
        self.db.commit()

    def set_branch_info(self):
        '''Set the branch information.
       
        All the branches we setup need to have branch information added. 
        '''
        self.dbCmd.execute("select id, name, version from collection")
        collections = {}
        for collection in self.dbCmd.fetchall():
            cid = collection[0]
            collections[cid] = {'id' : cid}
            if collection[1] == 'Fedora' and collection[2] == '7':
                # Fedora 7 onwards use F-#
                collections[cid]['branchname'] = 'F-' + collection[2]
                collections[cid]['disttag'] = '.fc' + collection[2]
            elif collection[1] == 'Fedora' and collection[2] == 'devel':
                # devel is simply devel
                collections[cid]['branchname'] = collection[2]
                collections[cid]['disttag'] = '.fc' + collection[2]
            elif collection[1] == 'Fedora':
                # All other Fedoras
                collections[cid]['branchname'] = 'FC-' + collection[2]
                collections[cid]['disttag'] = '.fc' + collection[2]
            elif collection[1] == 'Red Hat Linux':
                collections[cid]['branchname'] = 'RHL-' + collection[2]
                collections[cid]['disttag'] = '.rhl' + collection[2]
            elif collection[1] == 'Fedora EPEL':
                collections[cid]['branchname'] = 'EL-' + collection[2]
                collections[cid]['disttag'] = '.el' + collection[2]
            elif collection[1] == 'Fedora OLPC':
                collections[cid]['branchname'] = 'OLPC-' + collection[2]
                collections[cid]['disttag'] = '.olpc' + collection[2]
            else:
                logging.warning('%s: %s is not a known collection.  Please set branch information manually' % (collections[cid], cid))
                del (collections[cid])
                continue

            self.dbCmd.execute("insert into branch" \
                    " (collectionid, branchname, disttag)" \
                    " values (%(id)s, %(branchname)s, %(disttag)s)", collections[cid])
        self.db.commit()

    def set_special_owners(self):
        '''Set up special ownership for some packages
        
        anaconda, anaconda-maint-list@redhat.com anaconda-maint 9901
        lvm things - lvm-team
        kernel-xen - xen-maint@redhat.com xen-maint 9902
        kernel - kernel-maint@redhat.com kernel-maint 9903
        xorg-x11-* - xgl-maint@redhat.com xgl-maint 9904
        '''
        specials = {'anaconda': (9901, 'anaconda-maint'),
            'device-mapper': (9905, 'lvm-team'),
            'device-mapper-multipath': (9905, 'lvm-team'),
            'dmraid': (9905, 'lvm-team'),
            'lvm2': (9905, 'lvm-team'),
            'kernel-xen-2.6': (9902, 'xen-maint'),
            'xen' : (9902, 'xen-maint'),
            'kernel': (9903, 'kernel-maint'),
            'xorg-sgml-doctools': (9904, 'xgl-maint'),
            'xorg-x11-apps': (9904, 'xgl-maint'),
            'xorg-x11-docs': (9904, 'xgl-maint'),
            'xorg-x11-drivers': (9904, 'xgl-maint'),
            'xorg-x11-drv-acecad': (9904, 'xgl-maint'),
            'xorg-x11-drv-aiptek': (9904, 'xgl-maint'),
            'xorg-x11-drv-amd': (9904, 'xgl-maint'),
            'xorg-x11-drv-apm': (9904, 'xgl-maint'),
            'xorg-x11-drv-ark': (9904, 'xgl-maint'),
            'xorg-x11-drv-ast': (9904, 'xgl-maint'),
            'xorg-x11-drv-ati': (9904, 'xgl-maint'),
            'xorg-x11-drv-calcomp': (9904, 'xgl-maint'),
            'xorg-x11-drv-chips': (9904, 'xgl-maint'),
            'xorg-x11-drv-cirrus': (9904, 'xgl-maint'),
            'xorg-x11-drv-citron': (9904, 'xgl-maint'),
            'xorg-x11-drv-cyrix': (9904, 'xgl-maint'),
            'xorg-x11-drv-digitaledge': (9904, 'xgl-maint'),
            'xorg-x11-drv-dmc': (9904, 'xgl-maint'),
            'xorg-x11-drv-dummy': (9904, 'xgl-maint'),
            'xorg-x11-drv-dynapro': (9904, 'xgl-maint'),
            'xorg-x11-drv-elographics': (9904, 'xgl-maint'),
            'xorg-x11-drv-evdev': (9904, 'xgl-maint'),
            'xorg-x11-drv-fbdev': (9904, 'xgl-maint'),
            'xorg-x11-drv-fpit': (9904, 'xgl-maint'),
            'xorg-x11-drv-glint': (9904, 'xgl-maint'),
            'xorg-x11-drv-hyperpen': (9904, 'xgl-maint'),
            'xorg-x11-drv-i128': (9904, 'xgl-maint'),
            'xorg-x11-drv-i740': (9904, 'xgl-maint'),
            'xorg-x11-drv-i810': (9904, 'xgl-maint'),
            'xorg-x11-drv-jamstudio': (9904, 'xgl-maint'),
            'xorg-x11-drv-keyboard': (9904, 'xgl-maint'),
            'xorg-x11-drv-magellan': (9904, 'xgl-maint'),
            'xorg-x11-drv-magictouch': (9904, 'xgl-maint'),
            'xorg-x11-drv-mga': (9904, 'xgl-maint'),
            'xorg-x11-drv-microtouch': (9904, 'xgl-maint'),
            'xorg-x11-drv-mouse': (9904, 'xgl-maint'),
            'xorg-x11-drv-mutouch': (9904, 'xgl-maint'),
            'xorg-x11-drv-neomagic': (9904, 'xgl-maint'),
            'xorg-x11-drv-nsc': (9904, 'xgl-maint'),
            'xorg-x11-drv-nv': (9904, 'xgl-maint'),
            'xorg-x11-drv-palmax': (9904, 'xgl-maint'),
            'xorg-x11-drv-penmount': (9904, 'xgl-maint'),
            'xorg-x11-drv-rendition': (9904, 'xgl-maint'),
            'xorg-x11-drv-s3': (9904, 'xgl-maint'),
            'xorg-x11-drv-s3virge': (9904, 'xgl-maint'),
            'xorg-x11-drv-savage': (9904, 'xgl-maint'),
            'xorg-x11-drv-siliconmotion': (9904, 'xgl-maint'),
            'xorg-x11-drv-sis': (9904, 'xgl-maint'),
            'xorg-x11-drv-sisusb': (9904, 'xgl-maint'),
            'xorg-x11-drv-spaceorb': (9904, 'xgl-maint'),
            'xorg-x11-drv-summa': (9904, 'xgl-maint'),
            'xorg-x11-drv-tdfx': (9904, 'xgl-maint'),
            'xorg-x11-drv-tek4957': (9904, 'xgl-maint'),
            'xorg-x11-drv-trident': (9904, 'xgl-maint'),
            'xorg-x11-drv-tseng': (9904, 'xgl-maint'),
            'xorg-x11-drv-ur98': (9904, 'xgl-maint'),
            'xorg-x11-drv-v4l': (9904, 'xgl-maint'),
            'xorg-x11-drv-vermilion': (9904, 'xgl-maint'),
            'xorg-x11-drv-vesa': (9904, 'xgl-maint'),
            'xorg-x11-drv-vga': (9904, 'xgl-maint'),
            'xorg-x11-drv-via': (9904, 'xgl-maint'),
            'xorg-x11-drv-vmmouse': (9904, 'xgl-maint'),
            'xorg-x11-drv-vmware': (9904, 'xgl-maint'),
            'xorg-x11-drv-void': (9904, 'xgl-maint'),
            'xorg-x11-drv-voodoo': (9904, 'xgl-maint'),
            'xorg-x11-filesystem': (9904, 'xgl-maint'),
            'xorg-x11-font-utils': (9904, 'xgl-maint'),
            'xorg-x11-fonts': (9904, 'xgl-maint'),
            'xorg-x11-proto-devel': (9904, 'xgl-maint'),
            'xorg-x11-resutils': (9904, 'xgl-maint'),
            'xorg-x11-server': (9904, 'xgl-maint'),
            'xorg-x11-server-utils': (9904, 'xgl-maint'),
            'xorg-x11-twm': (9904, 'xgl-maint'),
            'xorg-x11-util-macros': (9904, 'xgl-maint'),
            'xorg-x11-utils': (9904, 'xgl-maint'),
            'xorg-x11-xauth': (9904, 'xgl-maint'),
            'xorg-x11-xbitmaps': (9904, 'xgl-maint'),
            'xorg-x11-xdm': (9904, 'xgl-maint'),
            'xorg-x11-xfs': (9904, 'xgl-maint'),
            'xorg-x11-xfwp': (9904, 'xgl-maint'),
            'xorg-x11-xinit': (9904, 'xgl-maint'),
            'xorg-x11-xkb-utils': (9904, 'xgl-maint'),
            'xorg-x11-xsm': (9904, 'xgl-maint'),
            'xorg-x11-xtrans-devel': (9904, 'xgl-maint')
        }

        # Find all affected packageListings
        for pkg in specials.keys():
            pkgInfo = {'pkg': pkg, 'owner': specials[pkg][0]}
            self.dbCmd.execute("select pl.id, pl.owner, c.name from" \
                " PackageListing as pl, Collection as c, Package as p" \
                " where p.name = %(pkg)s and p.id = pl.packageid" \
                " and c.id = pl.collectionid", pkgInfo)
            # Find the branches that are affected
            for pkgListing in self.dbCmd.fetchall():
                # Only do this for branches from owners.list
                if pkgListing[2] == 'Fedora':
                    # Set the owner to the special
                    pkgInfo['listId'] = pkgListing[0]
                    formerOwner = pkgListing[1]
                    self.dbCmd.execute("update packagelisting set" \
                            " owner = %(owner)s where id = %(listId)s",
                            pkgInfo)

                    # Add the former owner as a co-maintainer
                    # Do not list watch* because the owner is a list
                    self._add_acls((formerOwner,),(pkgInfo['listId'],),
                        ('commit', 'build', 'approveacls', 'checkout'))
        self.db.commit()

def exit(code):
    '''Cleanup and exit program.'''
    logging.shutdown()
    sys.exit(code)

if __name__ == '__main__':
    logging.basicConfig()

    # Retrieve information from owners.list
    fedoraOwners = owners.OwnerList(populate_all=1, ownerFile=OWNERLIST)
    epelOwners = owners.OwnerList(populate_all=1, ownerFile=EPELLIST)
    olpcOwners = owners.OwnerList(populate_all=1, ownerFile=OLPCLIST)

    # Read in the modules created for the package
    cvsModules = CVSReleases(CVSMODULEFILE)

    # Import the data into the database
    pkgdb = PackageDB()
    pkgdb.import_data(fedoraOwners, epelOwners, olpcOwners, cvsModules, True)

    # And a few cleanup items.  These are just pieces of information that I
    # know, not things that are stored in any file.  Keeping them in separate
    # functions for that reason.
    pkgdb.set_collection_status()
    pkgdb.set_collection_owner()
    pkgdb.set_branch_info()
    pkgdb.set_special_owners()

    exit(0)
