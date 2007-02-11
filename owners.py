#!/usr/bin/python -t
'''Usage: owners.py [PATH TO owners.list]

This program parses the owners.list file from a cvs checkout and constructs
an sql file expressing package database relations.
'''

__version__ = '0.2'

dbName='pkgdb'
dbHost='localhost'
dbUser='pkgdbadmin'
dbPass='4r3t`3'

import sys
import re
import optparse
import cPickle as pickle
import logging
import psycopg2

sys.path.append('/var/www/repo/fedora-accounts/')
sys.path.append('/srv/bzr/fedora-accounts/')
import website

class AccountsDB(object):
    '''The Accounts System Database.'''

    def __init__(self):
        '''Acquire a connection to the accounts system database.'''
        self.db = website.get_dbh()
        self.dbCmd = self.db.cursor()

    def user_id_from_email(self, email):
        '''Find the user_id in the accountsdb for the given email address.'''
        return website.get_user_id(self.db, email)

def usage():
    print 'Usage: owners.py [PATH TO owners.list]'

class OwnerError(Exception):
    pass

class Owners(dict):
    '''Pull the data from the owners.list.
    '''

    def __init__(self, ownersData):
        '''Pull the data from the file into the data structure.'''
        self.collections = {}
        accountsDB = AccountsDB()
        accounts = self.__preseed_accounts()

        for line in ownersData.splitlines():
            if line.startswith('#'):
                continue
            line = line.strip()
            fields = line.split('|')

            if len(fields) != 6:
                logging.error('owners.list: malformed line: %s' % line)
                continue

            # Normalise spelling of Fedora Extras
            if fields[0] == 'Fedora Extras' or fields[0] == 'Fedora-Extras':
                collection = 'Fedora Extras'
            else:
                collection = fields[0]

            # Lookup the owner id from the account system:
            if fields[3] in accounts:
                ownerID = accounts[fields[3]]
            else:
                ownerID = accountsDB.user_id_from_email(fields[3])
                if not ownerID:
                    logging.error('owners.list: Unknown owner: %s in: %s' %
                            (fields[3], line))
                    continue
                accounts[fields[3]] = ownerID

            # Lookup the qacontact in the accounts system:
            if fields[4] in accounts:
                qacontact = accounts[fields[4]]
            else:
                qacontact = accountsDB.user_id_from_email(fields[4])
                if not qacontact:
                    qacontact = '0'
                    logging.error('owners.list: Unknon QA Contact: %s in %s' %
                            (fields[4], line))
                    logging.warning('Set qacontact for %s to 0' % fields[1])
                    continue
                accounts[fields[4]] = qacontact
            
            # Parse the watchers into an array and check the accounts system
            # to see if they're there.
            watcherIDs = []
            if fields[5]:
                watchers = fields[5].split(',')
                for watcher in watchers:
                    if watcher in accounts:
                        if type(accounts[watcher]) == dict:
                            pass
                            ### FIXME: This one takes special handling.
                            # Currently special handling is just for adding
                            # the watcher as a group instead of a person.
                            #
                            # We would need to get a group id number and tag
                            # it as such.
                        else:
                            watcherIDs.append(accounts[watcher])
                    else:
                        watcherID = accountsDB.user_id_from_email(watcher)
                        if not watcherID:
                            # Having unknown watchers is not a fatal error
                            logging.warning('owners.list: Unknown watcher:' \
                                    ' %s in: %s' % (watcher, line))
                            continue
                        accounts[watcher] = watcherID
                        watcherIDs.append(watcherID)
            self[fields[1]] = { 'collection' : collection,
                'summary' : fields[2],
                'owner' : ownerID,
                'qacontact' : qacontact,
                'watchers' : watcherIDs
            }

            # Record the collections this owners.list uses.  That way we can
            # check that we have all the necessary collections later.
            self.collections[collection] = None

    def __preseed_accounts(self):
        '''Give good values for accounts that are not in the accounts db.
            
        Some of the accounts in owners.list are not in the account system
        database.  We have to take care of these somehow.  Since some of them
        show up so often, we can take care of them manually.
        '''
        
        return {'extras-qa@fedoraproject.org' : None,
                # 100068 is toshio's account.  Use this for now.  Long term,
                # create an extras-orphan account to set this to.
                #'extras-orphan@fedoraproject.org' : 100068,
                'fedora-perl-devel-list@redhat.com' : {'group' : 100002},
                'byte@fedoraproject.org' : 100014,
                'icon@fedoraproject.org': 100029,
                'splinux@fedoraproject.org' : 100406,
                'kevin-redhat-bugzilla@tummy.com' : 100037,
                'jafo-redhat@tummy.com' : 100488,
                # skvidal@linux.duke.edu
                'skvidal@phy.duke.edu' : 100059,
                # Assuming this is Ralf Ertzing: ralf@camperquake.de
                'redhat-bugzilla@camperquake.de' : 100023,
                # dan@berrange.com
                'berrange@redhat.com' : 100447,
                # mike@flyn.org
                'redhat@flyn.org' : 100136,
                # redhat@linuxnetz.de
                'redhat-bugzilla@linuxnetz.de': 100093,
                # New address for sopwith sopwith+fedora@gmail.com
                'sopwith@redhat.com' : 100060,
                # Scott Bakers: muerte bakers@web-ster.com
                'scott@perturb.org' : 100881,
                # karen-peare@uiowa.edu
                'meme@daughtersoftiresias.org' : 100281,
                # DavidHart@TQMcube.com
                'davidhart@tqmcube.com' : 100211,
                # Typo: rvokal@redhat.com
                'rvokal@eredhat.com' : 100088
                }

class CVSError(Exception):
    pass

class CVSReleases(dict):
    def __init__(self, cvspath=None):
        '''Pull information on releases from the cvs modules file.
        '''
        self.releases = {'devel' : None}
        # If cvspath does not exist, we'll return 'devel' for any packages
        # on the fly.
        if not cvspath:
            return

        ### FIXME: Need to pull in information for RHL and EPEL as well.
        modulesRE = re.compile(r'^RHL-9\s+&common.*-dir')
        branchRE = re.compile(r'^([^ ]+)-FC-([0-9]+)-dir\s')
        cvsFile = file(cvspath, 'r')
        records = cvsFile.readlines()

        match = modulesRE.search(records[-1])
        if not match:
            raise CVSError, 'Branches need to be made in CVS module file before continuing'

        for entry in records:
            match = branchRE.search(entry)
            if match:
                # Save the release for the package
                parts = match.group(1).split('-')
                package = match.group(1)
                release = match.group(2)
                self[package].append(release)

                # Keep track of all the releases we're syncing
                self.releases[release] = None

    def __getitem__(self, key):
        '''Return the item with a default value.

        Return the value for key.  If the value is missing, create a default
        value of a list with the 'devel' release inside it.

        Attributes:
        key: The key to assign
        
        Return: The value for the key.
        '''
        if key in self:
            return dict.__getitem__(self, key)
        else:
            dict.__setitem__(self, key, ['devel'])
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

    def _add_acl(self, pkgACLData):
        '''Add and acl for a packageListing.
        Use the data to set the ACL.

        :pkgACLData: The information on the ACL to set.
        '''
        # Get ids for watchbugzilla and watchcommits ACLs
        self.dbCmd.execute("select id from PackageACL as pa" \
                " where pa.packageListingId = %(pkgList)s" \
                " and pa.acl = %(acl)s",
                pkgACLData)
        pkgACL = self.dbCmd.fetchone()
        if not pkgACL:
            # Create the ACL
            self.dbCmd.execute("insert into PackageACL" \
                    " (PackageListingId, acl) values" \
                    " (%(pkgList)s, %(acl)s)",
                    pkgACLData)
            self.dbCmd.execute("select pa.id from" \
                    " PackageACL as pa" \
                    " where pa.packageListingId = %(pkgList)s" \
                    " and pa.acl = %(acl)s",
                    pkgACLData)
            pkgACL = self.dbCmd.fetchone()

        # Save the ACL into the database
        pkgACLData['pkgACL'] = pkgACL[0]

        self.dbCmd.execute("insert into PersonPackageACL" \
                " (packageaclid, userid, status) select" \
                " %(pkgACL)s, %(watcher)s, pasc.statusCodeId from" \
                " PackageACLStatusCode as pasc natural join" \
                " StatusCodeTranslation as sct" \
                " where sct.language = 'C'" \
                " and sct.statusName = %(status)s",
                pkgACLData)

    def import_data(self, owners, cvs, updatedb):
        '''Import data from owners and cvs into the DB.

        owners: The information from owners.list
        cvs: Information from the cvs repo.
        updatedb: If this is True, update the db with our data, otherwise,
            discard any data we have in favor of the data already in the db.
        '''
        # Get the id for any collections we are going to be adding packages
        # to, creating any that do not already exist.  Collections are
        # uniquely specified by name and version so we need to look at the
        # name provided in the owners.list file and the releases from the
        # cvs module file.
        collectionNumbers = {}
        for collection in owners.collections.keys():
            for release in cvs.releases.keys():
                collectionData = {'collection' : collection,
                        'release' : release}
                self.dbCmd.execute("select id from collection" \
                        " where name = %(collection)s" \
                        " and version = %(release)s",
                        collectionData)
                collectionInfo = self.dbCmd.fetchone()
                if not collectionInfo:
                    # This collection is not yet known, create it.  At least
                    # version, status, and owner should be changed before
                    # deployment. (100068 is toshio's account)
                    collectionData.update({'status' : 'EOL', 'user' : 100068})
                    self.dbCmd.execute("insert into collection" \
                            " (name, version, status, owner)" \
                            " select %(collection)s, %(release)s," \
                            " CollectionStatusCode.statusCodeId, %(user)s" \
                            " from CollectionStatusCode" \
                            " natural join StatusCodeTranslation as sct" \
                            " where sct.language = 'C' " \
                            " and sct.statusName = %(status)s",
                            collectionData)
                    self.db.commit()
                    logging.warning('Created new collection %s.  Please' \
                            ' update version, status, and ownership' \
                            ' information for this release.' % collection)
                    self.dbCmd.execute("select id from collection" \
                            " where name = %(collection)s" \
                            " and version = %(release)s",
                            collectionData)
                    collectionInfo = self.dbCmd.fetchone()
                if not collectionNumbers.has_key(collection):
                    collectionNumbers[collection] = {}
                collectionNumbers[collection][release] = collectionInfo[0]

        # Import each package that was listed in the owners.list file.
        for pkg in owners.keys():
            # Add the packages into the database
            pkgData = {'pkg' : pkg, 'summary': owners[pkg]['summary'],
                    'status': 'Approved'}
            try:
                self.dbCmd.execute("insert into package" \
                        " (name, summary, status)" \
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
            pkgListNumbers = []
            pkgListData = {'pkgId' : pkgId,
                    'owner' : owners[pkg]['owner'],
                    'status' : 'Approved'}
            # Create a PackageListing entry for each release that the package
            # is available.
            for release in cvs[pkg]:
                pkgListData['collectId'] = collectionNumbers[owners[pkg]['collection']][release]
                self.dbCmd.execute("select id from PackageListing" \
                        " where packageId = %(pkgId)s and" \
                        " collectionId = %(collectId)s", pkgListData)
                pkgListNum = self.dbCmd.fetchone()
                if not pkgListNum:
                    self.dbCmd.execute("insert into PackageListing" \
                            " (packageId, collectionId, owner, status)" \
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
                pkgListNumbers.append(pkgListNum[0])

            # Set up anyone who should be watching the package
            for watcher in owners[pkg]['watchers']:
                pkgACLData = {'watcher' : watcher, 'status' : 'Approved'}
                for pkgListing in pkgListNumbers:
                    pkgACLData['pkgList'] = pkgListing
                    # Save the watchbugzilla acl for this listing
                    pkgACLData['acl'] = 'watchbugzilla'
                    self._add_acl(pkgACLData)
                    # Save the watchcommits acl for this listing
                    pkgACLData['acl'] = 'watchcommits'
                    self._add_acl(pkgACLData)
            self.db.commit()

def parse_commandline():
    '''Extract options from the command line.
    '''
    parser = optparse.OptionParser(version='%prog ' + __version__,
            usage='''%prog [OPTIONS] [input-filename]
       [input-filename] can be either an owners.list file or an intermediate
       file of preparsed owners information.  This allows us to do a conversion
       in two steps: the first part on a machine with access to the account
       system to associate with the owners information.  The second part with
       access to the database server on which the packageDB will live.

       Note: this script only handles Fedora releases.  It does not handle RHL
       releases or EPEL releases.  We need an up-to-date owners.epel.list to
       do EPEL correctly.
       If [input-filename] is not specified, read from stdin''')

    parser.add_option('-f', '--file', dest='pickleFile',
            help='write to file FILE [default=stdout]',
            metavar='FILE')
    parser.add_option('-d', '--dsn', dest='dsn',
            help='write to the postgres database at DSN instead of a file',
            metavar='DSN')
    parser.add_option('-c', '--cvsmodule', dest='cvsModule',
            help='read release information from cvs module file',
            metavar='MODULE')
    parser.add_option('-u', '--updatedb', dest='updatedb', action='store_true',
            help='update the database with new values.  Otherwise, entries that duplicate what is already in the database are discarded.')

    (options, args) = parser.parse_args()

    # Figure out where to write our parsed information
    if options.pickleFile and options.dsn:
        parser.error('Cannot specify both a dsn (-d) and temporary file (-t) as output')
    if not (options.pickleFile or options.dsn):
        options.pickleFile = '-'

    # Figure out where to read information from
    if len(args) != 1:
        inputFile = '-'
    else:
        inputFile = args[0]

    return (options, inputFile)

def exit(code):
    '''Cleanup and exit the program.'''
    logging.shutdown()
    sys.exit(code)

if __name__ == '__main__':
    logging.basicConfig()
    (options, filename) = parse_commandline()

    # Read the inputFile into memory
    if filename == '-':
        inputFile = sys.stdin
    else:
        try:
            inputFile = file(filename, 'r')
        except IOError:
            logging.critical('%s is not a file you can read' % filename,
                    exc_info=True)
            exit(1)
    body = inputFile.read()
    inputFile.close()

    try:
        # If we have a pickle file, assume it's an intermediate file being
        # saved to the database.
        owners = pickle.loads(body)
    except pickle.UnpicklingError:
        # Otherwise, assume it's an owners.list file.
        owners = Owners(body)

        if options.pickleFile:
            # If we are supposed to output, pickle the output and save to
            # the file
            if options.pickleFile == '-':
                outFile = sys.stdout
            else:
                try:
                    outFile = file(options.pickleFile, 'w')
                except IOError:
                    logging.critical('Unable to open %s to save the data' %
                            options.pickleFile, exc_info=True)
                    exit(2)
            pickle.dump(owners, outFile, -1)
            outFile.close()
            exit(0)

    # Get the cvs information as well
    if options.cvsModule:
        cvsModule = CVSReleases(options.cvsModule)
    else:
        cvsModule = CVSReleases()

    # Write the owner information into the database
    pkgdb = PackageDB()
    pkgdb.import_data(owners, cvsModule, options.updatedb)

    # And a few cleanup items.  Since these are just pieces of information I
    # know rather than in any file I'm keeping them in separate functions.
    pkgdb.set_collection_status()
    pkgdb.set_collection_owner()
    exit(0)
    def set_collection_status(self):
        '''Set the collection status fields.

        Collections are initialized to EOL.  We want to set certain one to be
        active instead.

        This is not being retrieved from any canonical data source, it's just
        knowledge about certain collections that we know about.
        '''
        self.dbCmd.execute("update collection set status=("
                " select csc.statusCodeId from CollectionStatusCode as csc"
                " natural join StatusCodeTranslation as sct"
                " where sct.language = 'C'"
                " and sct.statusName ='Under Development')"
                " where name = 'Fedora Extras' and version='devel'")
        self.dbCmd.execute("update collection set status=("
                " select csc.statusCodeId from CollectionStatusCode as csc"
                " natural join StatusCodeTranslation as sct"
                " where sct.language = 'C'"
                " and sct.statusName ='Active')"
                " where name='Fedora Extras' and version in ('5', '6')")

    def set_collection_owner(self):
        '''Set the collection owner.
        
        This information needs to be filled out.
        '''
        pass
