# -*- coding: utf-8 -*-
#
# Copyright © 2008  Red Hat, Inc. All rights reserved.
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
'''
Collection of validators for parameters coming to pkgdb URLs.
'''

# Validators don't need an__init__method (W0232)
# Validators are following an API specification so need certain methods that
#   would otherwise be functions (R0201)
# Validators will usually only have two methods (R0903)
# Only a few validators use the state parameter (W0613)
# pylint: disable-msg=W0232,R0201,R0903,W0613

from turbogears import validators
from sqlalchemy.exceptions import InvalidRequestError

from pkgdb.model import Collection

### HACK: TurboGears/FormEncode requires that we use a dummy _ function for
# error messages.
# http://docs.turbogears.org/1.0/Internationalization#id13
def _(s):
    return s

class BooleanValue(validators.FancyValidator):
    '''Convert a value into a boolean True or False.

    Note: We define no value or "f", "false", or "0" to be false.  Everything
    else will be True.
    '''
    def _to_python(self, value, state):
        '''We follow basic C conventions here.  Most values are True.  Only
        specific strings are allowed to be False.
        '''
        if not value or value.lower() in ('false', 'f', '0'):
            return False
        return True

class CollectionName(validators.FancyValidator):
    '''Test that the value is a recognized colleciton name.'''
    messages = {'no_collection': _('A collection named %(collection)s does'
                    ' not exist.')}

    def _to_python(self, value, state):
        '''Just remove leading and trailing whitespace.'''
        return value.strip()

    def validate_python(self, value, state):
        '''Make sure the collection is in the database.'''
        try:
            Collection.query.filter_by(name=value).first()
        except InvalidRequestError:
            raise validators.Invalid(self.messages('no_collection',
                collection=value), value, state)

#
# Chained Validators
#

# Note: Chaned validators receive a dict in the value parameter so they are
# not interchangable with validators for a single value.

class CollectionNameVersion(validators.FancyValidator):
    '''Test the combination of a Collection and Version for validity.'''
    messages = {'nameless_version': _('Version specified without a collection'),
            'no_version': _('There is no collection for %(name)s-%(version)s'),
            'no_collection': _('Collection named %(name)s does not exist')}

    def validate_python(self, value, state):
        name = value.get('name')
        version = value.get('version')
        if (not name) and version:
            raise validators.Invalid(self.message('nameless_version'),
                    value, state)
        if name and version:
            try:
                Collection.query.filter_by(name=name, version=version).one()
            except InvalidRequestError:
                raise validators.Invalid(self.message('no_version', name=name,
                    version=version), value, state)
        if name and not version:
            try:
                Collection.query.filter_by(name=name).first()
            except InvalidRequestError:
                raise validators.Invalid(self.message('no_collection',
                    name=name), value, state)
