# -*- coding: utf-8 -*-
#
# Copyright © 2007-2008  Red Hat, Inc. All rights reserved.
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

from urllib import quote

from turbogears import controllers, expose, paginate, config, redirect

from sqlalchemy.exceptions import InvalidRequestError
import bugzilla

from pkgdb import model
from cherrypy import request

import logging
log = logging.getLogger('pkgdb.controllers')

class BugList(list):
    '''Transform and store values in the bugzilla.Bug data structure

    The bugzilla.Bug data structure uses 8-bit strings instead of unicode and
    will have a private url instead of a public one.  Storing the bugs in this
    list object will cause these values to be corrected.
    '''

    def __init__(self, queryUrl, publicUrl):
        super(BugList, self).__init__()
        self.queryUrl = queryUrl
        self.publicUrl = publicUrl

    def __convert(self, bug):
        '''Convert bugs from the raw form retrieved from python-bugzilla to
        one that is consumable by a normal python program.

        This involves converting byte strings to unicode type and substituting
        any private URLs returned into a public URL.  (This occurs when we
        have to call bugzilla via one name on the internal network but someone
        clicking on the link in a web page needs to use a different address.)

        Arguments:
        :bug: A bug record returned from the python-bugzilla interface.
        '''
        if not isinstance(bug, bugzilla.Bug):
            raise TypeError('Can only store bugzilla.Bug type')
        if self.queryUrl != self.publicUrl:
            bug.url = bug.url.replace(self.queryUrl, self.publicUrl)
        bug.bug_status = unicode(bug.bug_status, 'utf-8')
        try:
            bug.short_short_desc = unicode(bug.short_short_desc, 'utf-8')
        except TypeError:
            bug.short_short_desc = unicode(bug.short_short_desc.data, 'utf-8')
        return {'url': bug.url, 'bug_status': bug.bug_status,
                'short_short_desc': bug.short_short_desc, 'bug_id': bug.bug_id}

    def __setitem__(self, index, bug):
        bug = self.__convert(bug)
        super(BugList, self).__setitem__(index, bug)

    def append(self, bug):
        '''Override the default append() to convert URLs and unicode.

        Just like __setitem__(), we need to call our __convert() method when
        adding a new bug via append().  This makes sure that we convert urls
        to the public address and convert byte strings to unicode.
        '''
        bug = self.__convert(bug)
        super(BugList, self).append(bug)

class Bugs(controllers.Controller):
    '''Display information related to individual packages.
    '''
    bzUrl = config.get('bugzilla.url',
                'https://bugzilla.redhat.com/')
    bzQueryUrl = config.get('bugzilla.queryurl', bzUrl)

    # pylint: disable-msg=E1101
    removedStatus = model.StatusTranslation.query.filter_by(
            statusname='Removed', language='C').first().statuscodeid
    # pylint: enable-msg=E1101

    def __init__(self, appTitle=None):
        '''Create a Packages Controller.

        :fas: Fedora Account System object.
        :appTitle: Title of the web app.
        '''
        self.bzServer = bugzilla.Bugzilla(url=self.bzQueryUrl + '/xmlrpc.cgi')
        self.appTitle = appTitle

    @expose(template='pkgdb.templates.bugoverview')
    @paginate('packages', default_order='name', limit=100,
            allow_limit_override=True, max_pages=13)
    def index(self):
        '''Display a list of packages with a link to bug reports for each.'''
        # Retrieve the list of packages minus removed packages
        # pylint: disable-msg=E1101
        packages = model.Package.query.filter(
                model.Package.c.statuscode!=self.removedStatus)
        # pylint: enable-msg=E1101

        return dict(title=self.appTitle + ' -- Package Bug Pages',
                bzurl=self.bzUrl, packages=packages)

    @expose(template='pkgdb.templates.pkgbugs', allow_json=True)

    def default(self, packageName, *args, **kwargs):
        '''Display a list of Fedora bugs against a given package.'''
        # Nasty, nasty hack.  The packagedb, via bugz.fp.o is getting sent
        # requests to download files.  These refused to go away even when
        # we fixed up the apache redirects.  Send them to download.fp.o
        # manually.
        if args or kwargs:
            if args:
                url = 'http://download.fedoraproject.org/' + quote(packageName)\
                        + '/' + '/'.join([quote(a) for a in args])
            elif kwargs:
                url = 'http://mirrors.fedoraproject.org/' + quote(packageName)\
                        + '?' + '&'.join([quote(q) + '=' + quote(v) for (q, v)
                            in kwargs.items()])
            log.warning('Invalid URL: redirecting: %s' % url)
            raise redirect(url)

        query = {'product': 'Fedora',
                'component': packageName,
                'bug_status': ['ASSIGNED', 'NEW', 'NEEDINFO', 'MODIFIED'] }
        rawBugs = self.bzServer.query(query)
        bugs = BugList(self.bzQueryUrl, self.bzUrl)
        for bug in rawBugs:
            bugs.append(bug)

        if not bugs:
            # Check that the package exists
            try:
                package = model.Package.query.filter_by(name=packageName).one()
            except InvalidRequestError:
                error = dict(status = False,
                        title = self.appTitle + ' -- Not a Valid Package Name',
                        message='No such package %s' % packageName)
                if request.params.get('tg_format', 'html') != 'json':
                    error['tg_template'] = 'pkgdb.templates.errors'
                return error

        return dict(title='%s -- Open Bugs for %s' %
                (self.appTitle, packageName), package=packageName,
                bugs=bugs)
