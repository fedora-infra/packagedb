#!/usr/bin/python
import os
import sys
import time
import urllib2
import re

portRE = re.compile(r'^[0-9]+$')
fileRE = re.compile(r'^(/pkgs/bzr/fedora-packagedb/|/var/www/repo/fedora-packagedb/pkgdb/)[-_a-zA-Z0-9/]+[-_a-zA-Z0-9]\.py$')

print "Content-type: text/html\r\n\n"

records = os.environ['QUERY_STRING'].split('&', 1)
for row in records:
    (fieldName, fieldValue) = row.split('=', 1)
    if fieldName == 'file':
        if fileRE.match(fieldValue):
            fileName = fieldValue
        else:
            print fieldValue
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
   
os.chdir(os.path.dirname(fileName))
os.system('%s &>/tmp/output &' % fileName)
trial = 0
page = None
while (trial < 10):
    try:
        page = urllib2.urlopen('http://localhost:%s/' % port)
    except:
        time.sleep(1)
        trial += 1
    else:
        print page.read()
        sys.exit(0)

print "Status: 502"
print "Unable to load page"
sys.exit(1)

