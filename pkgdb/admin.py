# -*- coding: utf-8 -*-
#
# Copyright © 2007-2008  Red Hat, Inc.
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
Controller for handling admin commands.  These are the dispatcher type methods.
'''

#
# Pylint Explanations
#

# :E1101: SQLAlchemy monkey patches the database fields into the mapper
#   classes so we have to disable these checks.


class Request():
    def __init__(self):
        pass
    def request_branch(self):
        pass
    def request_package(self):
        pass

class Admin(controllers.Controller):
    def __init__(self):
        pass

    def index(self):
        '''List the possible actions to perform.'''
        pass

    def create_collection(self):
        '''Let the user fill in the information for a new collection.'''
        pass

    def remove_package(self):
        '''Mark a package as removed.'''
        pass

    def rename_package(self):
        '''Rename a package to another name:: Note, still need to do things on
        the cvs server and in bugzilla after this.'''
        pass

    def view_queue(self):
        '''View pending admin requests
        '''
        pass
