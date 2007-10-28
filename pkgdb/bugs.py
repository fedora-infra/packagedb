# -*- coding: utf-8 -*-
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
#                    Seth Vidal <svidal@redhat.com>
#
'''
Controller for displaying Package Bug Information.
'''

from sqlalchemy.ext.selectresults import SelectResults
import sqlalchemy.mods.selectresults

from turbogears import controllers, expose, paginate, config
from turbogears.database import session

import bugzilla

from pkgdb import model

class BzBug(object):
    def __init__(self, bug):
        self.bug_id = bug.bug_id
        self.url = bug.url
        self.bug_status = unicode(bug.bug_status, 'utf-8')
        try:
            self.short_short_desc = unicode(bug.short_short_desc, 'utf-8')
        except TypeError:
            self.short_short_desc = unicode(bug.short_short_desc.data, 'utf-8')

class Bugs(controllers.Controller):
    '''Display information related to individual packages.
    '''
    def __init__(self, appTitle=None):
        '''Create a Packages Controller.

        :fas: Fedora Account System object.
        :appTitle: Title of the web app.
        '''
        bzurl = config.get('bugzilla.url',
                'https://bugzilla.redhat.com/xmlrpc.cgi')
        self.bzServer = bugzilla.Bugzilla(url=bzurl)
        self.appTitle = appTitle
        self.removedStatus = model.StatusTranslation.get_by(
                statusname='Removed', language='C').statuscodeid

    @expose(template='pkgdb.templates.bugoverview')
    @paginate('packages', default_order='name', limit=100,
            allow_limit_override=True, max_pages=13)
    def index(self):
        '''Display a list of packages with a link to bug reports for each.'''
        # Retrieve the list of packages minus removed packages
        packages = SelectResults(session.query(model.Package)).select_by(
                model.Package.c.statuscode!=self.removedStatus)

        return dict(title=self.appTitle + ' -- Package Bug Pages',
                tg_template='pkgdb.templates.bugoverview',
                packages=packages)


    @expose(template='pkgdb.templates.pkgbugs', allow_json=True)
    def default(self, packageName):
        '''Display a list of Fedora bugs against a given package.'''
        query = {'product': 'Fedora',
                'component': packageName,
                'bug_status': ['ASSIGNED', 'NEW', 'NEEDINFO', 'MODIFIED'] }
        rawBugs = self.bzServer.query(query)
        bugs = []
        for bug in rawBugs:
            bugs.append(BzBug(bug))
        return dict(title='%s -- Open Bugs for %s' %
                (self.appTitle, packageName), package=packageName,
                bugs=bugs)
