# -*- coding: utf-8 -*-
#
# Copyright © 2008, 2010  Red Hat, Inc.
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
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Collection of validators for parameters coming to pkgdb URLs.
'''

#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.
#   Validators also have a message() method which FormEncode adds in a way
#   that pylint can't detect.
# :W0232: Validators don't need an__init__method
# :W0613: Only a few validators use the state parameter
# :W0622: We have to redefine _ due to a FormEncode limitation
# :R0201: Validators are following an API specification so need certain
#   methods that would otherwise be functions
# :R0903: Validators will usually only have two methods

#pylint:disable-msg=W0232,R0201,R0903,W0613

import re

from turbogears.validators import Invalid, FancyValidator, Set, Regex, \
        UnicodeString
from sqlalchemy.exceptions import InvalidRequestError

try:
    from fedora.textutils import to_unicode
except ImportError:
    from pkgdb.lib.utils import to_unicode

from pkgdb.model import Collection
from pkgdb.lib.utils import STATUS

#pylint:disable-msg=W0622
def _(string):
    ''' *HACK*:  TurboGears/FormEncode requires that we use a dummy _ function.

    Internationalizing error messages won't work otherwise.
    http://docs.turbogears.org/1.0/Internationalization#id13
    '''
    return string
#pylint:enable-msg=W0622

#
# SetOf validator can validate its elements
#
class SetOf(Set):
    '''formencode Set() validator with the ability to validate its elements.

    :kwarg element_validator: Validator to run on each of the elements of the set.
    '''
    element_validator = None
    messages = {'incorrect_value': 'list values did not satisfy the element_validator'}

    def validate_python(self, value, state):
        if self.element_validator:
            try:
                value = map(self.element_validator.to_python, value)
            except Invalid:
                raise
            except:
                # Just in case the element validator doesn't throw an Invalid
                # exception
                raise Invalid(self.message('incorrect_value', state),
                        value, state)

#
# Three sorts of validators:
#
# 1) does minimal checking that a string looks sort of right
#    - For these we'll mostly just use the standard tg and formencode
#      validators.
# 2) Hits the db to verify that the string exists in the proper field
#    - These are appropriate where we're going to use the string anyways.  For
#      instance, in a select statement.
#    - These should be checked by making calls against something that's easily
#      sent to a memcached or redis server.
# 3) Looks in the db and transforms the string into the type of thing that it
#    is a key for
#    - This will do an actual call into the database and load an ORM mapped
#      object.
#

class IsCollectionSimpleNameRegex(Regex):
    '''Test the collection simple name against a simple heuristic

    :kwarg strip: If True, strips whitespace from the beginnng and end of the
        value.  (default True)
    :kwarg regex: regular expression object or string to be compiled to match
        the simple name against. Default: r'^[A-Z]+-([0-9]+|devel)$'
    '''
    strip = True
    regex = re.compile(r'^([A-Z]+-[0-9]+|devel)$')

    messages = {'no_collection': _('%(collection)s does not match the pattern'
        ' for collection names')}

    def _to_python(self, value, state):
        value = Regex._to_python(self, value, state)
        return to_unicode(value)

    def validate_python(self, value, state):
        if not self.regex.match(value):
            raise Invalid(self.message('no_collection', state,
                collection=value), value, state)

class IsCollectionSimpleName(UnicodeString):
    '''Test that the value is a recognized collection short name.

    :kwarg eol: If True, include eol releases. (default False)
    :kwarg strip: If True, strips whitespace from the beginnng and end of the
        value.  (default True)
    '''
    strip = True
    eol = False

    messages = {'no_collection': _('A collection named %(collection)s does'
                    ' not exist'),
                'eol_collection': _('Collection named %(collection)s is eol')
                }

    def validate_python(self, value, state):
        try:
            collection = Collection.by_simple_name(value)
        except InvalidRequestError:
            raise Invalid(self.message('no_collection', state,
                collection=value), value, state)
        if not self.eol and (collection.statuscode ==
                STATUS['EOL'].statuscodeid):
            raise Invalid(self.message('eol_collection', state,
                collection=value), value, state)
        return value

class IsCollection(IsCollectionSimpleName):
    '''Transforms a Collection simplename into a Collection.

    :kwarg eol: If True, include eol releases. (default False)
    :kwarg strip: If True, strips whitespace from the beginnng and end of the
        value.  (default True)
    :rtype: Collection
    :returns: Collection that the simplename we were given references.
    '''
    messages = {'no_collection': _('A collection named %(collection)s does'
                    ' not exist'),
                'eol_collection': _('Collection named %(collection)s is eol')
                }

    def validate_python(self, value, state):
        try:
            collection = Collection.by_simple_name(value)
        except InvalidRequestError:
            raise Invalid(self.message('no_collection', state,
                collection=value), value, state)
        if not self.eol and (collection.statuscode ==
                STATUS['EOL'].statuscodeid):
            raise Invalid(self.message('eol_collection', state,
                collection=value), value, state)
        return collection



#
# Legacy -- Remove when we update the API
#

class CollectionName(FancyValidator):
    '''Test that the value is a recognized collection name.'''
    messages = {'no_collection': _('A collection named %(collection)s does'
                    ' not exist.')}

    def _to_python(self, value, state):
        '''Just remove leading and trailing whitespace.'''
        return value.strip()

    def validate_python(self, value, state):
        '''Make sure the collection is in the database.'''
        #pylint:disable-msg=E1101
        try:
            Collection.query.filter_by(name=value).first()
        except InvalidRequestError:
            raise Invalid(self.message('no_collection', state,
                collection=value), value, state)
        #pylint:enable-msg=E1101

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

class CollectionNameVersion(FancyValidator):
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
            #pylint:disable-msg=E1101
            errors['version'] = self.message('nameless_version', state)
        elif name and version:
            #pylint:disable-msg=E1101
            try:
                Collection.query.filter_by(name=name, version=version).one()
            except InvalidRequestError:
                errors['version'] = self.message('no_version', state,
                        name=name, version=version)
        elif name and not version:
            #pylint:disable-msg=E1101
            try:
                Collection.query.filter_by(name=name).first()
            except InvalidRequestError:
                errors['name'] = self.message('no_collection', state, name=name)

        if errors:
            error_list = sorted(errors.iteritems())
            error_message = '\n'.join([u'%s: %s' % (error, msg)
                    for error, msg in error_list])
            raise Invalid(error_message, field_dict, state,
                    error_dict=errors)
