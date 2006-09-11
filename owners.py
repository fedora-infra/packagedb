#!/usr/bin/python -tt
'''Usage: owners.py [PATH TO owners.list]

This program parses the owners.list file from a cvs checkout and constructs
an sql file expressing package database relations.
'''

import sys

def usage():
    print 'Usage: owners.py [PATH TO owners.list]'

if __name__ == '__main__':
    if not sys.argv[1]:
        usage()
        sys.exit(1)

    try:
        owners = file(sys.argv[1])
    except IOError:
        print sys.argv[1] + 'is not a file you can read'
        sys.exit(1)

    for line in owners.readlines():
        if line.startswith('#'):
            continue
        fields = line.split('|')
 
        if len(fields) != 6:
            print 'Malformed line:', line
            continue

        collection = fields[0]
        name = fields[1]
        summary = fields[2]
        owner = fields[3]
        qacontact = fields[4]
        comaintainers = fields[5]

        # Add these to the package db.
        # Pull from the package db, the ACLs, the 
    sys.exit(0)
