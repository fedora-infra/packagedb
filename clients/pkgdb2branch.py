#!/usr/bin/python -tt
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

import sys
try:
    import subprocess
except ImportError:
    import popen2

import json
import urllib2

try:
    from fedora.tg.client import BaseClient, ServerError
except ImportError:
    from client import BaseClient, ServerError

BASEURL='http://test3.fedora.phx.redhat.com/pkgdb-dev'
BRANCHER='/cvs/extras/CVSROOT/mkbranchwrapper'

class PackageDBError(ServerError):
    pass

class ProcessError(Exception):
    pass

class PackageDBClient(BaseClient):
    def __init__(self, baseURL):
        '''Initial ize the connection.

        Args:
        :baseURL: URL from which the packageDB is accessed
        '''
        # We're only performing read operations so we don't need a username
        super(PackageDBClient, self).__init__(baseURL, None, None)

    def get_package_branches(self, pkgname):
        data = self.send_request('/packages/name/%s' % pkgname)
        if 'message' in data:
            raise PackageDBError((data['message']))
        branches = []
        for packageListing in data['packageListings']:
            branches.append(packageListing['collection']['branchname'])
        return branches

def print_usage():
    print '''%s packagename [packagename, ...]

For each packagename specified as an argument, create any branches that are
listed for it in the packagedb.
''' % sys.argv[0]

def create_branches(pkgname, branches):
    cmdLine = [BRANCHER, pkgname]
    cmdLine.extend(branches)
    if 'subprocess' in sys.modules():
        branchScript = subprocess.Popen(cmdLine, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
        retCode = branchScript.wait()
        if retCode:
            e = ProcessError()
            e.returnCode = retCode
            e.cmd = ' '.join(cmdLine)
            e.message = ''.join(branchScript.stdout.readlines())
            raise e
    else:
        branchScript = popen2.Popen4(' '.join(cmdLine))
        retCode = branchScript.wait()
        if os.WIFEXITED(retCode) and os.WEXITSTATUS(retCode):
            e = ProcessError()
            e.returnCode = os.WEXITSTATUS(retCode)
            e.cmd = ' '.join(cmdLine)
            e.message = ''.join(branchScript.fromchild.readlines())

if __name__ == '__main__':
    if '--help' in sys.argv or '-h' in sys.argv or len(sys.argv) == 1:
        print_usage()
        sys.exit(0)

    warnings = False
    packages = sys.argv[1:]
    client = PackageDBClient(BASEURL)
    for pkgname in packages:
        try:
            branches = client.get_package_branches(pkgname)
        except PackageDBError, e:
            print 'Unable to retrieve information about %s: %s' % (pkgname, e.message)
            warnings = True
            continue
        try:
            create_branches(pkgname, branches)
        except ProcessError, e:
            print 'Error, "%s" returned %s: %s' % (e.cmd, e.returncode,
                    e.message)
            warnings = True
            continue

    if warnings:
        sys.exit(100)
    sys.exit(0)
