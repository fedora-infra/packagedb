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
#

'''
JSON Helper functions.  Most JSON code  directlry related to functions is
implemented via the __json__() methods in model.py
'''
# A JSON-based API(view) for your app.
# Most rules would look like:
# @jsonify.when("isinstance(obj, YourClass)")
# def jsonify_yourclass(obj):
#     return [obj.val1, obj.val2]
# @jsonify can convert your objects to following types:
# lists, dicts, numbers and strings

import sqlalchemy
from turbojson.jsonify import jsonify

@jsonify.when("isinstance(obj, sqlalchemy.ext.selectresults.SelectResults)")
def jsonify_sa_select_results(obj):
    '''Transform selectresults into lists.
    
    The one special thing is that we bind the special jsonProps into each
    descendent.  This allows us to specify a jsonProps on the toplevel
    query result and it will pass to all of its children.
    '''
    if 'jsonProps' in obj.__dict__:
        for element in obj:
            element.jsonProps = obj.jsonProps
    return list(obj)

@jsonify.when("isinstance(obj, sqlalchemy.orm.attributes.InstrumentedList)")
def jsonify_salist(obj):
    '''Transform SQLAlchemy InstrumentedLists into json.
    
    The one special thing is that we bind the special jsonProps into each
    descendent.  This allows us to specify a jsonProps on the toplevel
    query result and it will pass to all of its children.
    '''
    if 'jsonProps' in obj.__dict__:
        for element in obj:
           element.jsonProps = obj.jsonProps
    return map(jsonify, obj)

