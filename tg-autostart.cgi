#!/usr/bin/python
import os
import sys
import time
import urllib2
import re

portRE = re.compile(r'^[0-9]+$')
fileRE = re.compile(r'^(/srv/bzr/fedora-packagedb/pkgdb/|/var/www/repo/fedora-packagedb/pkgdb/|/var/www/repo/vanilla-fedora-packagedb/pkgdb/)[-_a-zA-Z0-9/]+[-_a-zA-Z0-9]\.py$')

RUNDIR='/tmp'

print "Content-type: text/html\r\n\n"

records = os.environ['QUERY_STRING'].split('&', 1)
for row in records:
    (fieldName, fieldValue) = row.split('=', 1)
    if fieldName == 'file':
        if fileRE.match(fieldValue):
            fileName = fieldValue
        else:
            print "Status: 502"
            print "Unable to load page"
            sys.exit(1)
    elif fieldName == 'port':
        if portRE.match(fieldValue):
            port = fieldValue
        else:
            print "Status: 502"
            print "Unable to load page"
            sys.exit(1)
    else:
        print "Status: 502"
        print "Unable to load page"
        sys.exit(1)

if not (fileName and port):
    print "Status: 502"
    print "Unable to load page"
    sys.exit(1)

baseFileName = os.path.basename(fileName)
### FIXME: Create a /var/run/httpd directory owned by apache for these:
if os.access(os.path.join(RUNDIR, baseFileName), os.F_OK):
    
    ### Compare timestamps
    pass
else:
    ### Create the path
    pass

pathcomponents = os.environ['REDIRECT_URL'].split('/')
path = '/' + '/'.join(pathcomponents[2:])

os.system('pkill -9 -f %s' % fileName)
os.chdir(os.path.dirname(fileName))
os.system('%s &>/tmp/%s-output &' % (fileName, baseFileName))
trial = 0
page = None

while (trial < 15):
    try:
        page = urllib2.urlopen('http://localhost:%s%s' % (port, path))
    except:
        time.sleep(1)
        trial += 1
    else:
        print page.read()
        sys.exit(0)

print "Status: 502"
print "Unable to load page"
sys.exit(1)

