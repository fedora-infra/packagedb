#!/usr/bin/python -t
# -*- coding: utf-8 -*-
import sys, os, errno
import website, crypt
import getopt, re
import xmlrpclib
import json
import urllib2
import codecs
import locale

from fedora.accounts.fas import AccountSystem

# Set this to the production bugzilla account when we're ready to go live
#BZSERVER = 'https://bugdev.devel.redhat.com/bugzilla-cvs/xmlrpc.cgi'
BZSERVER = 'https://bugzilla.redhat.com/xmlrpc.cgi'
BZUSER=''
BZPASS=''

PKGDBSERVER = 'https://admin.fedoraproject.org/pkgdb/acls/bugzilla/?tg_format=json'

# Set this to False when we're ready to run it against the bz database
DRY_RUN = False

class DataChangedError(Exception):
    '''Raised when data we are manipulating changes while we're modifying it.'''
    pass

class Bugzilla(object):

    def __init__(self, bzServer, username, password):
        self.userCache = {}
        self.userCache['extras-qa@fedoraproject.org'] = {}
        self.userCache['extras-qa@fedoraproject.org']['email'] = 'extras-qa@fedoraproject.org'
        self.productCache = {}
        self.bzXmlRpcServer = bzServer
        self.username = username
        self.password = password

        self.server = xmlrpclib.Server(bzServer)

        # Connect to the fedora account system
        self.fas = AccountSystem()

    def _get_bugzilla_email(self, username):
        try:
            user = self.userCache[username]
        except KeyError:
            user = {}
            (person, groups) = self.fas.get_user_info(username)
            user['email'] = person['bugzilla_email'].lower()
            self.userCache[username] = user
            return user['email']

        try:
            email = user['email']
        except KeyError:
            try:
                (person, groups) = self.fas.get_user_info(username)
            except fas.AuthError, e:
                raise ValueError,  'Username %s was not found in fas' % username

            email = person['bugzilla_email'].lower()
            user['email'] = email

        return email

    def add_edit_component(self, package, collection, owner, description,
            qacontact=None, cclist=None):
        '''Add or update a component to have the values specified.
        '''
        # Turn the cclist into something usable by bugzilla
        if not cclist or 'people' not in cclist:
            initialCCList = list()
        else:
            initialCCList = []
            for ccMember in cclist['people']:
                ccEmail = self._get_bugzilla_email(ccMember)
                initialCCList.append(ccEmail)

        # Lookup product
        try:
            product = self.productCache[collection]
        except KeyError:
            product = {}
            try:
                components = self.server.bugzilla.getProdCompDetails(collection,
                                self.username, self.password)
            except xmlrpclib.Fault, e:
                # Output something useful in args
                e.args = (e.faultCode, e.faultString)
                raise
            except xmlrpclib.ProtocolError, e:
                e.args = ('ProtocolError', e.errcode, e.errmsg)
                raise

            # This changes from the form:
            #   {'component': 'PackageName',
            #   'initialowner': 'OwnerEmail',
            #   'initialqacontact': 'QAContactEmail',
            #   'description': 'One sentence summary'}
            # to:
            #   product['packagename'] = {'component': 'PackageName',
            #     'initialowner': 'OwnerEmail',
            #     'initialqacontact': 'QAContactEmail',
            #     'description': 'One sentenct summary'}
            # This allows us to check in a case insensitive manner for the
            # package.
            for record in components:
                record['component'] = unicode(record['component'], 'utf-8')
                try:
                    record['description'] = unicode(record['description'], 'utf-8')
                except TypeError:
                    try:
                        record['description'] = unicode(record['description'].data, 'utf-8')
                    except:
                        record['description'] = None
                product[record['component'].lower()] = record

            self.productCache[collection] = product

        pkgKey = package.lower()
        if pkgKey in product:
            # edit the package information
            data = {}

            # Grab bugzilla email for things changable via xmlrpc
            owner = self._get_bugzilla_email(owner).lower()
            if qacontact:
                qacontact = self._get_bugzilla_email(qacontact)
            else:
                qacontact = 'extras-qa@fedoraproject.org'

            # Check for changes to the owner, qacontact, or description
            if product[pkgKey]['initialowner'] != owner:
                data['initialowner'] = owner

            if product[pkgKey]['description'] != description:
                data['description'] = description
            if product[pkgKey]['initialqacontact'] != qacontact and (
                    qacontact or product[pkgKey]['initialqacontact']):
                data['initialqacontact'] = qacontact

            if len(product[pkgKey]['initialcclist']) != len(initialCCList):
                data['initialcclist'] = initialCCList
            else:
                for ccMember in product[pkgKey]['initialcclist']:
                    if ccMember not in initialCCList:
                        data['initialcclist'] = initialCCList
                        break
                    
            if data:
                ### FIXME: initialowner has been made mandatory for some
                # reason.  Asking dkl why.
                data['initialowner'] = owner

                # Changes occurred.  Submit a request to change via xmlrpc
                data['product'] = collection
                data['component'] = product[pkgKey]['component']
                if DRY_RUN:
                    print '[EDITCOMP] Changing via editComponent(%s, %s, "xxxxx")' % (
                            data, self.username)
                    print '[EDITCOMP] Former values: %s|%s|%s' % (
                            product[pkgKey]['initialowner'],
                            product[pkgKey]['description'],
                            product[pkgKey]['initialqacontact'])
                else:
                    try:
                        self.server.bugzilla.editComponent(data, self.username,
                                self.password)
                    except xmlrpclib.Fault, e:
                        print data
                        # Output something useful in args
                        e.args = (data, e.faultCode, e.faultString)
                        raise
                    except xmlrpclib.ProtocolError, e:
                        e.args = ('ProtocolError', e.errcode, e.errmsg)
                        raise
        else:
            # Add component
            owner = self._get_bugzilla_email(owner).lower()
            if qacontact:
                qacontact = self._get_bugzilla_email(qacontact)
            else:
                qacontact = 'extras-qa@fedoraproject.org'

            data = {'product': collection,
                'component': package,
                'description': description,
                'initialowner': owner,
                'initialqacontact': qacontact}
            if initialCCList:
                data['initialcclist'] = initialCCList

            if DRY_RUN:
                print '[ADDCOMP] Adding new component AddComponent:(%s, %s, "xxxxx")' % (
                        data, self.username)
            else:
                try:
                    self.server.bugzilla.addComponent(data, self.username,
                            self.password)
                except xmlrpclib.Fault, e:
                    # Output something useful in args
                    e.args = (data, e.faultCode, e.faultString)
                    raise

if __name__ == '__main__':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

    opts, args = getopt.getopt(sys.argv[1:], '', ('usage', 'help'))
    if len(args) > 0:
        print """
Usage: bz-make-components.py

Sync package information from the package database to bugzilla.
"""
        sys.exit(1)

    # Initialize the connection to bugzilla
    bugzilla = Bugzilla(BZSERVER, BZUSER, BZPASS)

    # Non-fatal errors to alert people about
    errors = []

    # Get bugzilla information from the package database
    ownerPage = urllib2.urlopen(PKGDBSERVER)
    bugzillaData = json.read(ownerPage.read())
    ownerPage.close()
    acls = bugzillaData['bugzillaAcls']
    del bugzillaData

    for product in acls.keys():
        if product not in ('Fedora', 'Fedora OLPC', 'Fedora EPEL'):
            continue
        for pkg in acls[product]:
            pkgInfo = acls[product][pkg]
            try:
                bugzilla.add_edit_component(pkg, product,
                        pkgInfo['owner'], pkgInfo['summary'],
                        pkgInfo['qacontact'], pkgInfo['cclist'])
            except ValueError, e:
                # A username didn't have a bugzilla address
                errors.append(str(e.args))
            except DataChangedError, e:
                # A Package or Collection was returned via xmlrpc but wasn't
                # present when we tried to change it
                errors.append(str(e.args))
            except xmlrpclib.ProtocolError, e:
                # Unrecoverable and likely means that nothing is going to
                # succeed.
                errors.append(str(e.args))
                break
            except xmlrpclib.Error, e:
                # An error occurred in the xmlrpc call.  Shouldn't happen but
                # we better see what it is
                errors.append(str(e.args))

    # Send notification of errors 
    if errors:
        #print '[DEBUG]', '\n'.join(errors)
        website.send_email('accounts@fedoraproject.org',
                'a.badger@gmail.com',
                'Errors while syncing bugzilla with the PackageDB',
'''
The following errors were encountered while updating bugzilla with information
from the Package Database.  Please have the problems taken care of:

%s
''' % ('\n'.join(errors),))

    sys.exit(0)
