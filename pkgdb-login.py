#!/usr/bin/python -t
# Example code to authenticate a command line client with turbogears.
# Hold onto the cookie and send it with all future requests.

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
