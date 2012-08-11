# -*- coding: utf-8 -*-
#
# Copyright (C) 2012  Red Hat, Inc.
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
# Author(s):         Frank Chiulli <fchiulli@fedoraproject.org>
#
'''
Utilities for all classes to use
'''

from sqlalchemy import select

from pkgdb.model import Collection, CollectionTable

#
# Function to sort collection versions.
#
def version_sort(arg1, arg2):
    '''
    A compare (cmp) function to compare two collection.versions.
    version is a string which may contain an integer such as 13
    or a string such as 'devel'.  We want the non-integers (i.e., names) first.
    And we want the integers sorted in reverse order.

    Returns: -1 if arg1 < arg2
              0 if arg1 = arg2
             +1 if arg1 > arg2
    '''

    try:
        ver1 = int(arg1)
        try:
            ver2 = int(arg2)
            #
            # ver1 and ver2 are integers.
            # Put in reverse order.
            #
            if (ver1 < ver2):
                return 1

            elif (ver1 > ver2):
                return -1

            else:
                return 0

        except ValueError:
            #
            # ver1 is an integer.
            # ver2 is not an interger.
            # Names go first.
            #
            return 1

    except ValueError:
        try:
            ver2 = int(arg2)
            #
            # ver1 is not an integer.
            # ver2 is an integer.
            # Names (non-integers go first).
            #
            return -1

        except ValueError:
            #
            # Neither versions are integers.
            #
            ver1 = arg1
            ver2 = arg2

    if (ver1 < ver2):
        return -1

    elif (ver1 > ver2):
        return 1

    else:
        return 0


def get_collection_info():
    '''
    This function queries the database for collection information.
    It then returns an array of dictionaries.
    '''

    #pylint:disable=E1103
    query = select([Collection.id, Collection.name, Collection.version],
                   use_labels=True)
    #pylint:enable=E1103
    collections = {}
    for row in query.execute():
        c_id = row[CollectionTable.c.id]
        c_name = row[CollectionTable.c.name]
        c_version = row[CollectionTable.c.version]

        if not collections.has_key(c_name):
            collections[c_name] = {}

        if not collections[c_name].has_key(c_version):
            collections[c_name][c_version] = c_id

    collection_list = []
    c_names = collections.keys()
    c_names.sort()
    for name in c_names:
        versions = collections[name].keys()
        versions.sort(cmp=version_sort)
        for version in versions:
            collection_info = {}
            collection_info['name'] = name
            collection_info['version'] = version
            collection_info['id'] = collections[name][version]

            collection_list.append(collection_info)

    return collection_list

