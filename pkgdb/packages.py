# -*- coding: utf-8 -*-
#
# Copyright © 2009  Red Hat, Inc. All rights reserved.
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
Controller for displaying PackageBuild(Rpm) related information
'''

from sqlalchemy.sql import and_

from turbogears import controllers, expose, identity

from pkgdb.model import Comment, PackageBuild, Repo
from pkgdb.utils import mod_grp

from fedora.tg.util import request_format

from cherrypy import request

class Package(controllers.Controller):
    '''Display general information related to PackageBuilds.
    '''

    def __init__(self, app_title=None):
        '''Create a Packages Controller

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title

    @expose(template='pkgdb.templates.userpkgpage', allow_json=True)
    def default(self, buildName=None, repo='F-11-i386', language='en_US'):
        '''Retrieve PackageBuild by their name.

        This method returns general packagebuild/rpm information about a
        package like: version, release, size, last changelog message,
        committime etc. This information comes from yum and is stored in
        the pkgdb.

        :arg buildName: Name of the packagebuild/rpm to lookup
        :arg repo: shortname of the repository to look in
        :arg language: A language string, (e.g. 'American English' or 'en_US')
        '''
        if buildName==None:
            raise redirect(config.get('base_url_filter.base_url') +
                '/packages/list/')

        builds_query = PackageBuild.query.filter_by(name=buildName)
        # look for The One packagebuild
        try:
            build = builds_query.join(PackageBuild.repo).filter(
                Repo.shortname==repo).one()
        except:
            error = dict(status=False,
                         title=_('%(app)s -- Invalid PackageBuild Name') % {
                             'app': self.app_title},
                             message=_('The package build you were linked to'
                             ' (%(pkg)s) does not appear in the Package '
                             ' Database. If you received this error from a link'
                             ' on the fedoraproject.org website, please report'
                             ' it.') % {'pkg': buildName})
            if request_format() != 'json':
                error['tg_template'] = 'pkgdb.templates.errors'
                return error
        other_repos = []
        arches = set()
        for b in builds_query.all():
            other_repos.append(b.repo)
            arches.add(b.architecture)
        other_repos.remove(build.repo)
        
        tagscore = build.scores(language)

        comment_query = Comment.query.filter(and_(
            Comment.packagebuildname==build.name,
            Comment.language==language)).order_by(Comment.time)
        # hide the mean comments from ordinary users
        if identity.in_group(mod_grp):
            comments = comment_query.all()
        else:
            comments = comment_query.filter_by(published=True).all()

        return dict(title=_('%(title)s -- %(pkg)s') % {
            'title': self.app_title, 'pkg': buildName},
                    repo=repo, build=build, other_repos=other_repos,
                    arches=arches, tagscore=tagscore, language=language,
                    comments=comments)

