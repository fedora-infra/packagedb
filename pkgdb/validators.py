# -*- coding: utf-8 -*-
#
# Copyright © 2008  Red Hat, Inc.
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

#
# Pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.
#   Validators also have a message() method which FormEncode adds in a way
#   that pylint can't detect.
# :W0232: Validators don't need an__init__method
# :R0201: Validators are following an API specification so need certain
#   methods that would otherwise be functions
# :R0903: Validators will usually only have two methods
# :W0613: Only a few validators use the state parameter

# pylint: disable-msg=W0232,R0201,R0903,W0613

from turbogears import validators
from sqlalchemy.exceptions import InvalidRequestError

from pkgdb.model import Collection

# :W0622: We have to redefine _ due to a FormEncode limitation
# pylint: disable-msg=W0622
def _(string):
    ''' *HACK*:  TurboGears/FormEncode requires that we use a dummy _ function.

    Internationalizing error messages won't work otherwise.
    http://docs.turbogears.org/1.0/Internationalization#id13
    '''
    return string
# pylint: enable-msg=W0622

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
        # pylint: disable-msg=E1101
        try:
            Collection.query.filter_by(name=value).first()
        except InvalidRequestError:
            raise validators.Invalid(self.message('no_collection', state,
                collection=value), value, state)
        # pylint: enable-msg=E1101

#
# Chained Validators
#

# Note: Chained validators take different params so they are not interchangable
# with normal validators:
# validate_python: field_dict instead of value.  This is a dictionary of the
# fields passed into the schema.
#
# raising Invalid: error_dict.  In addition to the other values to Invalid()
# we send an error_dict that maps the field to display an error with to the
# message.

class CollectionNameVersion(validators.FancyValidator):
    '''Test the combination of a Collection and Version for validity.'''
    messages = {'nameless_version': _('Version specified without a collection'
                    ' name'),
            'no_version': _('There is no collection for %(name)s-%(version)s'),
            'no_collection': _('Collection named %(name)s does not exist')}

    def validate_python(self, field_dict, state):
        '''Make sure the Collection with the given `name` and `version` exists.

        We want to allow for:
          1) Neither to be set
          2) Name to exist in the db and version unset
          3) Name and version to exist in the db
        '''
        if not field_dict:
            # It's okay for both to be none
            return

        errors = {}
        name = field_dict.get('name')
        version = field_dict.get('version')
        if (not name) and version:
            # pylint: disable-msg=E1101
            errors['version'] = self.message('nameless_version', state)
        elif name and version:
            try:
                Collection.query.filter_by(name=name, version=version).one()
            except InvalidRequestError:
                errors['version'] = self.message('no_version', state,
                        name=name, version=version)
        elif name and not version:
            # pylint: disable-msg=E1101
            try:
                Collection.query.filter_by(name=name).first()
            except InvalidRequestError:
                errors['name'] = self.message('no_collection', state, name=name)

        if errors:
            error_list = sorted(errors.iteritems())
            error_message = '\n'.join([u'%s: %s' % (error, msg)
                    for error, msg in error_list])
            raise validators.Invalid(error_message, field_dict, state,
                    error_dict=errors)
