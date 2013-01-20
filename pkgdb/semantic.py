# -*- coding: utf-8 -*-
#
# Copyright © 2012  Pierre-Yves Chibon <pingou@pingoured.fr>.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2, or (at your option) any later version.  This
# program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the GNU
# General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA. Any Red Hat trademarks that are incorporated in the source
# code or documentation are not subject to the GNU General Public License and
# may only be used or replicated with the express permission of Red Hat, Inc.
#
# Red Hat Project Author(s): Pierre-Yves Chibon <pingou@pingoured.fr>
#
'''
Controller for displaying Applications related information
'''
#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.

from sqlalchemy.sql.expression import and_, literal_column, union
from sqlalchemy import Text, Integer, func, desc

from turbogears import controllers, expose, identity, redirect, flash
from turbogears import paginate, validate, validators
from turbogears.database import session

from pkgdb.model import Package
from pkgdb.lib.utils import STATUS

# rdflib import to generate the doap graph.
from rdflib.graph import Graph
from rdflib.term import URIRef, Literal
from rdflib.namespace import Namespace, RDF


import logging
log = logging.getLogger('pkgdb.applications')

class DoapController(controllers.Controller):
    '''Display general information related to Applicaiton.
    '''

    def __init__(self, app_title=None):
        '''Create a Applications Controller

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title

    @expose(content_type='text/xml')
    def default(self, pkgname=None):
        '''Retrieve application by its name.

        :arg app_name: Name of the packagebuild/rpm to lookup
        '''
        if pkgname == None:
            raise redirect('/')

        pkg = session.query(Package).filter(
                Package.statuscode!=STATUS['Removed']
                ).filter_by(name=pkgname).first()
                
        store = Graph()

        # Bind a few prefix, namespace pairs.
        store.bind('dc', 'http://http://purl.org/dc/elements/1.1/')
        store.bind('doap', 'http://usefulinc.com/ns/doap#')

        # Create a namespace object for the doap namespace
        DOAP = Namespace('http://usefulinc.com/ns/doap#')

        # Create the subject
        project = URIRef(pkg.upstreamurl)

        # Add the triples
        store.add((project, RDF.type, DOAP['Project']))
        store.add((project, DOAP['name'],
            Literal(pkg.name)))
        store.add((project, DOAP['description'],
            Literal(pkg.description, lang='en')))
        store.add((project, DOAP['summary'],
            Literal(pkg.summary, lang='en')))
        store.add((project, DOAP['bug-database'],
            Literal('https://bugz.fedoraproject.org/%s' % pkg.name)))

        # Retrieve the serialized RDF/XML into a variable
        output = store.serialize(format='pretty-xml')

        print output
        return output
