#!/usr/bin/python -t
#
# Copyright © 2007  Red Hat, Inc. All rights reserved.
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
Example code to authenticate a command line client with turbogears.
Hold onto the cookie and send it with all future requests.
'''

import sys
import urllib
import urllib2
import Cookie
import json

LOGINURL='https://admin.fedoraproject.org/pkgdb-dev/login?tg_format=json'
USERNAME=''
PASSWORD=''
DEBUG=False

class AuthError(Exception):
    pass

def authenticate(username, password):
    sessionCookie = Cookie.SimpleCookie()
    req = urllib2.Request(LOGINURL)
    req.add_data(urllib.urlencode({'user_name': USERNAME, 'password': PASSWORD, 'login': 'Login'}))
    req.add_header('Cookie', sessionCookie.output(attrs=[], header='').strip())
    f = urllib2.urlopen(req)

    serverData = json.read(f.read())
    if 'message' in serverData:
        raise AuthError, 'Unable to login to server: %s' % serverData['message']

    try:
        sessionCookie.load(f.headers['set-cookie'])
    except KeyError:
        raise AuthError, 'Unable to login to the server.  Server did not send back a cookie.'

    if DEBUG:
        print 'DEBUG:', sessionCookie, serverData

    return sessionCookie

if __name__ == '__main__':
    # Retrieve public data
    req = urllib2.Request('https://admin.fedoraproject.org/pkgdb-dev/packages/dispatcher/')
    f = urllib2.urlopen(req)
    publicData = json.read(f.read())
    print 'Methods supported by the Package DB Package Dispatcher:'
    for method in publicData['methods']:
        print ' ', method
    print

    # Authenticate
    try:
        sessionCookie = authenticate(USERNAME, PASSWORD)
    except AuthError, e:
        print e
        sys.exit(1)

    # Retrieve private data
    req = urllib2.Request('https://admin.fedoraproject.org/pkgdb-dev/test/?tg_format=json')
    req.add_header('Cookie', sessionCookie.output(attrs=[], header='').strip())
    f = urllib2.urlopen(req)
    privateData = json.read(f.read())
    print 'Only members of cvsextras can know the server time:',privateData['now']
