# -*- coding: utf-8 -*-
#
# Copyright © 2007-2009  Red Hat, Inc. All rights reserved.
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
# Red Hat Author(s):        Toshio Kuratomi <tkuratom@redhat.com>
#                           Seth Vidal <svidal@redhat.com>
# Fedora Project Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#
'''
Controller for displaying Package Bug Information.
'''
#
# PyLint Explanations
#

# :E1101: SQLAlchemy mapped classes are monkey patched.  Unless otherwise
#   noted, E1101 is disabled due to a static checker not having information
#   about the monkey patches.

from urllib import quote
from turbogears import controllers, expose, config, redirect
from sqlalchemy.exceptions import InvalidRequestError
from cherrypy import request

try:
    # python-bugzilla 0.4 >= rc5
    from bugzilla.base import _Bug as Bug
except ImportError:
    try:
        # python-bugzilla 0.4 < rc5
        from bugzilla.base import Bug
    except ImportError:
        # python-bugzilla 0.3
        # :E0611: This is only found if we are using python-bugzilla 0.3
        from bugzilla import Bug # pylint: disable-msg=E0611

from pkgdb.model import Package
from pkgdb.letter_paginator import Letters
from pkgdb.utils import to_unicode, LOG, bugzilla
from pkgdb import _

class BugList(list):
    '''Transform and store values in the bugzilla.Bug data structure

    The bugzilla.Bug data structure uses 8-bit strings instead of unicode and
    will have a private url instead of a public one.  Storing the bugs in this
    list object will cause these values to be corrected.
    '''

    def __init__(self, query_url, public_url):
        super(BugList, self).__init__()
        self.query_url = query_url
        self.public_url = public_url

    def __convert(self, bug):
        '''Convert bugs from the raw form retrieved from python-bugzilla to
        one that is consumable by a normal python program.

        This involves converting byte strings to unicode type and substituting
        any private URLs returned into a public URL.  (This occurs when we
        have to call bugzilla via one name on the internal network but someone
        clicking on the link in a web page needs to use a different address.)

        :arg bug: A bug record returned from the python-bugzilla interface.
        '''
        if not isinstance(bug, Bug):
            raise TypeError(_('Can only store bugzilla.Bug type'))
        if self.query_url != self.public_url:
            bug.url = bug.url.replace(self.query_url, self.public_url)

        bug.bug_status = to_unicode(bug.bug_status, errors='replace')
        bug.short_desc = to_unicode(bug.short_desc, errors='replace')
        bug.product = to_unicode(bug.product, errors='replace')
        return {'url': bug.url, 'bug_status': bug.bug_status,
                'short_desc': bug.short_desc, 'bug_id': bug.bug_id,
                'product': bug.product}

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

    def __init__(self, app_title=None):
        '''Create a Packages Controller.

        :app_title: Title of the web app.
        '''

        self.app_title = app_title
        self.index = Letters(app_title)

    @expose(template='pkgdb.templates.pkgbugs', allow_json=True)
    def default(self, package_name, *args, **kwargs):
        '''Display a list of Fedora bugs against a given package.'''
        # Nasty, nasty hack.  The packagedb, via bugz.fp.o is getting sent
        # requests to download files.  These refused to go away even when
        # we fixed up the apache redirects.  Send them to download.fp.o
        # manually.
        if args or kwargs:
            if args:
                url = 'http://download.fedoraproject.org/' \
                        + quote(package_name) \
                        + '/' + '/'.join([quote(a) for a in args])
            elif kwargs:
                url = 'http://mirrors.fedoraproject.org/' \
                        + quote(package_name) \
                        + '?' + '&'.join([quote(q) + '=' + quote(v) for (q, v)
                            in kwargs.items()])
                LOG.warning(_('Invalid URL: redirecting: %(url)s') %
                        {'url':url})
            raise redirect(url)

        query = {'product': ('Fedora', 'Fedora EPEL'),
                'component': package_name,
                'bug_status': ('ASSIGNED', 'NEW', 'MODIFIED',
                    'ON_DEV', 'ON_QA', 'VERIFIED', 'FAILS_QA',
                    'RELEASE_PENDING', 'POST') }
        # :E1101: python-bugzilla monkey patches this in
        raw_bugs = bugzilla.query(query) # pylint: disable-msg=E1101
        bugs = BugList(self.bzQueryUrl, self.bzUrl)
        for bug in raw_bugs:
            bugs.append(bug)

        if not bugs:
            # Check that the package exists
            try:
                # pylint: disable-msg=E1101
                Package.query.filter_by(name=package_name).one()
            except InvalidRequestError:
                error = dict(status=False,
                        title=_('%(app)s -- Not a Valid Package Name') %
                            {'app': self.app_title},
                        message=_('No such package %(pkg)s') %
                            {'pkg': package_name})
                if request.params.get('tg_format', 'html') != 'json':
                    error['tg_template'] = 'pkgdb.templates.errors'
                return error

        return dict(title=_('%(app)s -- Open Bugs for %(pkg)s') %
                {'app': self.app_title, 'pkg': package_name},
                package=package_name, bugs=bugs)
