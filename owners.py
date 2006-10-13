#!/usr/bin/python -t
'''Usage: owners.py [PATH TO owners.list]

This program parses the owners.list file from a cvs checkout and constructs
an sql file expressing package database relations.
'''

__version__ = '0.1'

dbName='packagedb'
dbHost='localhost'
dbUser='pkgdbadmin'
dbPass='4r3t`3'

import sys
import optparse
import cPickle as pickle

sys.path.append('/var/www/repo/fedora-accounts/')
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
        self.errors = []
        accountsDB = AccountsDB()
        accounts = self.__preseed_accounts()

        for line in ownersData.splitlines():
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
                    self.errors.append('Unknown Owner: ' + fields[3] +
                            ' in: ' + line)
                    continue
                accounts[fields[3]] = ownerID

            # Lookup the qacontact in the accoutns system:
            if fields[4] in accounts:
                qacontact = accounts[fields[4]]
            else:
                qacontact = accountsDB.user_id_from_email(fields[4])
                if not qacontact:
                    qacontact = '0'
                    self.errors.append('Unknown QA Contact: ' + fields[4] +
                            ' in: ' + line)
                    continue
                accounts[fields[4]] = qacontact

            # Parse the watchers into an array and check the accounts system
            # to see if they're there.
            if fields[5]:
                watchers = fields[5].split(',')
                watcherIDs = []
                for watcher in watchers:
                    if watcher in accounts:
                        if type(accounts[watcher]) == dict:
                            pass
                            ### FIXME: This one takes special handling.
                            # Currently special handling is just for adding
                            # the watcher as a group instead of a person.
                        else:
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
                # 100068 is toshio's account.  Use this for now.  Long term,
                # create an extras-orphan account to set this to.
                'extras-orphan@fedoraproject.org' : 100068,
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
                'davidhart@tqmcube.com' : 100211
                }

class PackageDBError(Exception):
    pass

class PackageDB(object):
    '''The PackageDB we're entering information into.'''

    def __init__(self):
        '''Setup the connection to the DB.'''
        import psycopg2

        self.db = psycopg2.connect(database=dbName, host=dbHost,
                user=dbUser, password=dbPass)
        self.dbCmd = self.db.cursor()

    def import_owners(self, owners):
        '''Import data from owners into the DB.

        owners: The information from owners.list
        '''
        for collection in owners.collections.keys():
            self.dbCmd.execute("select * from collection where name = '%s'" %
                    collection)
            if not self.dbCmd.fetchall():
                raise PackageDBError, 'Unknown Collection %s' % collection
            ### FIXME: determine which collection to place the packages. 
        for pkg in owners.keys():
            ### FIXME:  Add the packages to the db.
            pass

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

       If [input-filename] is not specified, read from stdin''')

    parser.add_option('-f', '--file', dest='pickleFile',
            help='write to file FILE [default=stdout]',
            metavar='FILE')
    parser.add_option('-d', '--dsn', dest='dsn',
            help='write to the postgres database at DSN instead of a file',
            metavar='DSN')

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

if __name__ == '__main__':
    (options, filename) = parse_commandline()

    # Read the inputFile into memory
    if filename == '-':
        inputFile = sys.stdin
    else:
        try:
            inputFile = file(filename, 'r')
        except IOError:
            print filename, 'is not a file you can read'
            sys.exit(1)
    body = inputFile.read()
    inputFile.close()

    try:
        # If we have a pickle file, assume it's an intermediate file being
        # saved to the database.
        owners = pickle.loads(body)
    except pickle.UnpicklingError:
        # Otherwise, assume it's an owners.list file.
        owners = Owners(body)
        if owners.errors:
            # Print the errors but continue
            for error in owners.errors:
                print error

        if options.pickleFile:
            # If we are supposed to output, pickle the output and save to
            # the file
            if options.pickleFile == '-':
                outFile = sys.stdout
            else:
                try:
                    outFile = file(options.pickleFile, 'w')
                except IOError:
                    print 'Unable to open', options.pickleFile, 'to save the data'
                    sys.exit(2)
            pickle.dump(owners, outFile, -1)
            outFile.close()
            sys.exit(0)

    # Write the owner information into the database
    pkgdb = PackageDB()
    pkgdb.import_owners(owners)
    sys.exit(0)
