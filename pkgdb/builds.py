# -*- coding: utf-8 -*-
#
# Copyright © 2009  Red Hat, Inc.
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
# Red Hat Project Author(s): Martin Bacovsky <mbacovsk@redhat.com>
#
'''
Controller for displaying PackageBuild related information
'''
#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import and_, literal_column, union
from sqlalchemy import Text, Integer

from turbogears import controllers, expose, identity, redirect, flash
from turbogears import paginate
from turbogears.database import session

from pkgdb.model import Repo, PackageBuild
from pkgdb import release, _

from fedora.tg.util import request_format

from operator import itemgetter
import re


import logging
log = logging.getLogger('pkgdb.builds')

class BuildsController(controllers.Controller):
    
    def __init__(self, app_title=None):
        '''Create an Builds Controller

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title


    @expose(template='pkgdb.templates.builds')
    def default(self):
        '''Builds Home Page
        '''

        redirect('/apps/name/list/a*')

    
    @expose(template='pkgdb.templates.builds_search')
    @paginate('build_list', limit=50, default_order='name', max_limit=None,
            max_pages=13) #pylint:disable-msg=C0322
    def search(self, pattern=''):
        '''Builds search result

        :arg pattern: pattern to be looked for in apps.

        Search is performed on name, license, architecture, version, release,
        provides, requires, obsoletes, depends and files. Results are sorted according 
        to relevancy. Parts where pattern was recognized are shown
        in listing.
        '''

        pkg_list = []

        if pattern == '':
            flash('Insert search pattern...')

        builds = self._builds_search_query(pattern).execute()

        # merge all hits 
        merged_results = {}
        for b in builds:
            result = merged_results.get(b['id'], None)
            if result is None:
                result = {
                    'name': b['name'],
                    'epoch': b['epoch'],
                    'release': b['release'],
                    'version': b['version'],
                    'arch': b['architecture'],
                    'repo': b['repo'],
                    'score': 0,
                    'obsoletes': [],
                    'provides': [],
                    'requires': [],
                    'conflicts': [],
                    'depend': [],
                }
            result['score'] += b['score']
            if b['foundin'] == 'Obsoletes':
                result['obsoletes'].append(b['data'])
            elif b['foundin'] == 'Provides':
                result['provides'].append(b['data'])
            elif b['foundin'] == 'Requires':
                result['requires'].append(b['data'])
            elif b['foundin'] == 'Conflicts':
                result['conflicts'].append(b['data'])
            elif b['foundin'] == 'Depend':
                result['depend'].append(b['data'])

            merged_results[b['id']] = result

        build_list = sorted(merged_results.values(), key=itemgetter('score'), reverse=True)
                
        return dict(title=self.app_title, version=release.VERSION,
            pattern=pattern, build_list=build_list)


    def _builds_search_query(self, pattern):
        p = re.compile(r'\W+')
        s_pattern = p.sub(' ', pattern).split(' ')

        # name
        q_name = session.query(
                PackageBuild.id,
                PackageBuild.name,
                PackageBuild.epoch,
                PackageBuild.version,
                PackageBuild.release,
                PackageBuild.architecture,
                Repo.shortname.label('repo'),
                literal_column("'Name'", Text).label('foundin'),
                literal_column('100', Integer).label('score'),
                literal_column('0', Integer).label('data'))\
            .join(Repo)\
            .filter(
                and_(
                    1 == 1, 
                    *(PackageBuild.name.ilike('%%%s%%' % p) for p in s_pattern)
                )
            )

        # union that
        builds_query = union(
                    q_name,
                    )

        return builds_query


    @expose(template='pkgdb.templates.builds')
    @paginate('build_list', limit=50, default_order='name', max_limit=None,
            max_pages=13) #pylint:disable-msg=C0322
    def name(self, searchwords='a*' ):
        '''Builds view by name

        :arg searchwords: filter used by letter_paginator
        '''
        
        pattern = searchwords.replace('*','%')
        #pylint:disable-msg=E1101
        build_list = session.query(PackageBuild)\
                .filter(
                    PackageBuild.name.ilike(pattern))
        #pylint:enable-msg=E1101

        return dict(title=self.app_title, version=release.VERSION,
            searchwords=searchwords, list_type='name',
            build_list=build_list, pattern='')


    @expose(template='pkgdb.templates.build')
    def show(self, shortname, buildname, epoch, version, rel, arch):
        
        try:
            repo = session.query(Repo).filter_by(shortname=shortname).one()
        except NoResultFound:
            flash('Repo "%s" was not found' % shortname)
            redirect('/builds')

        try:
            build = session.query(PackageBuild).filter_by(
                name=buildname,
                epoch=epoch,
                version=version,
                release=rel,
                architecture=arch,
                repo=repo).one()
        except NoResultFound:
            flash('Build (%s-%s:%s-%s.%s) was not found' % (buildname, epoch, version, rel, arch))
            redirect('/builds')

        return dict(title=self.app_title, version=release.VERSION,
            build=build)
            

                
        


