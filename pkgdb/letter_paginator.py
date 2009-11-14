# -*- coding: utf-8 -*-
#
# Copyright © 2007-2009  Red Hat, Inc.
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
# Fedora Project Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#
'''
Module to be used for letter pagination and search.
'''
#
# PyLint Explanations
#

# :E1101: SQLAlchemy mapped classes are monkey patched.  Unless otherwise
#   noted, E1101 is disabled due to a static checker not having information
#   about the monkey patches.

from sqlalchemy.sql import or_
from sqlalchemy.orm import lazyload
from turbogears import controllers, expose, paginate, config
from pkgdb.model import Package
from pkgdb.utils import STATUS
from pkgdb import _

from cherrypy import request

class Letters(controllers.Controller):
    '''Display package lists with letter pagination, search and links
    '''

    def __init__(self, app_title=None):
        # pylint: disable-msg=E1101
        self.app_title = app_title

    @expose(template='pkgdb.templates.pkgbugoverview', allow_json=True)
    @paginate('packages', default_order='name', limit=100,
                max_limit=None, max_pages=13)
    def default(self, searchwords=''):
        '''Return a list of all packages in the database.

           :kwarg searchwords: optional - string to restrict the list, can use
           % or * as wildcards
        '''
        if searchwords != '':
            searchwords = searchwords.replace('*','%')
            if searchwords.isdigit() and int(searchwords) < 10: # 0-9
                # pylint: disable-msg=E1101
                packages = Package.query.options(
                        lazyload('listings2'), lazyload('status')).filter(or_(
                               Package.name.between('0','9'),
                                   Package.name.like('9%')))
            else: 
                # sanitize for ilike:
                searchwords = searchwords.replace('&','').replace('_','') 
                # pylint: disable-msg=E1101
                packages = Package.query.options(
                        lazyload('listings2'), lazyload('status')).filter(
                        Package.name.ilike(searchwords)
                        ).order_by(Package.name.asc())
        else:
            # pylint: disable-msg=E1101
            packages = Package.query.options(lazyload('listings2'),
                    lazyload('status'))
        searchwords = searchwords.replace('%','*')
        # minus removed packages
        packages = packages.filter(
                        Package.c.statuscode!=STATUS['Removed'].statuscodeid)

        # set the links for bugs or package info
        if request.path.startswith('/pkgdb/packages/index/'):
            mode = ''
            bzUrl = ''
        else:
            mode = 'bugs/'
            bzUrl = config.get('bugzilla.url', 'https://bugzilla.redhat.com/')
        return dict(title=_('%(app)s -- Packages Overview %(mode)s') % {
            'app': self.app_title, 'mode': mode},
                       searchwords=searchwords, packages=packages, mode=mode,
                       bzurl=bzUrl)
