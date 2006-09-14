#!/usr/bin/python -tt
'''Usage: owners.py [PATH TO owners.list]

This program parses the owners.list file from a cvs checkout and constructs
an sql file expressing package database relations.
'''

__version__ = '0.1'

dbName='packagedb'
host='localhost'
user='pkgdbadmin'
password='4r3t`3'

import sys
### TODO:
# Comment for now.  I think we'll have to rework this script to either parse
# owners.list (on the fedora infrastructure servers where fedora-accounts is
# available) or enter a pre-parsed list into the db. (since the test db is not
# on fedora infrastructure.)
#import psycopg2
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

    def __init__(self, filename):
        '''Pull the data from the file into the data structure.'''
        self.collections = {}
        self.errors = []
        accountsDB = AccountsDB()
        ownersFile = file(filename, 'r')
        accounts = self.__preseed_accounts()

        for line in ownersFile.readlines():
            if line.startswith('#'):
                continue
            line = line.strip()
            fields = line.split('|')

            if len(fields) != 6:
                self.errors.append('Malformed line: ' + line)
                continue

            # Lookup the owner id from the account system:
            if fields[3] in accounts:
                ownerID = accounts[fields[3]]
            else:
                ownerID = accountsDB.user_id_from_email(fields[3])
                if not ownerID:
                    self.errors.append('Unknown Owner: ' + line)
                    continue
                accounts[fields[3]] = ownerID

            # Lookup the qacontact in the accoutns system:
            if fields[4] in accounts:
                qacontact = accounts[fields[4]]
            else:
                qacontact = accountsDB.user_id_from_email(fields[4])
                if not qacontact:
                    qacontact = '0'
                    self.errors.append('Unknown QA Contact: ' + line)
                    continue
                accounts[fields[4]] = qacontact

            # Parse the watchers into an array and check the accounts system
            # to see if they're there.
            if fields[5]:
                watchers = fields[5].split(',')
                watcherIDs = []
                for watcher in watchers:
                    if watcher in accounts:
                        watcherIDs.append(accounts[watcher])
                    else:
                        watcherID = accountsDB.user_id_from_email(watcher)
                        if not watcherID:
                            # Having unknown watchers is not a fatal error
                            self.errors.append('Warning: Unknown watcher ' +
                                watcher + ' in:' + line)
                            continue
                        accounts[watcher] = watcherID
                        watcherIDs.append(watcherID)
                        
                self[fields[1]] = { 'collection' : fields[0],
                        'summary' : fields[2],
                        'owner' : ownerID,
                        'qacontact' : qacontact,
                        'watchers' : watcherIDs
                        }

            # Record the collections this owners.list uses.  That way we can
            # check that we have all the necessary collections later.
            self.collections[fields[0]] = None

    def __preseed_accounts(self):
        '''Give good values for accounts that are not in the accounts db.
            
        Some of the accounts in owners.list are not in the account system
        database.  We have to take care of these somehow.  Since some of them
        show up so often, we can take care of them manually.
        '''
        
        return {'extras-qa@fedoraproject.org' : None,
                'extras-orphan@fedoraproject.org' : 0}

"""
class PackageDB(object):
    '''The PackageDB we're entering information into.'''

    def __init__(self):
        '''Setup the connection to the DB.'''
        self.db = psycopg2.connect(database=dbName, host=dbHost, user=dbUser, password=dbPass)
        self.dbCmd = self.db.cursor()
"""
if __name__ == '__main__':
    if not sys.argv[1]:
        usage()
        sys.exit(1)

    # Load the data from owners.list
    try:
        owners = Owners(sys.argv[1])
    except IOError:
        print sys.argv[1], 'is not a file you can read'
        sys.exit(1)
    if (owners.errors):
        for error in owners.errors:
            print error

    ### FIXME: We need to also take a path to a mirror of the CVS repository.
    # Then we can create the Collections and the packages present in them.
    print owners
    ### FIXME: We need to write out the owners information into a file.  Then
    # we can transfer it to the test machine.  Need to use a commandline
    # switches to either do that (parse the owners.list file and translate email
    # addresses into account ids) or do this second part: enter data into the
    # packagedb.
    sys.exit(1)
    pkgdb = PackageDB()
    pkgdb.import_owners(owners)
    ### FIXME: Next steps:
    # Make sure the collections are in the db
    # Add the packages to the db.
    sys.exit(0)
