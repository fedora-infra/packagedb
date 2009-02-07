#!/usr/bin/python -tt
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

''' 
Instructions to modify the schema and script to modify the table data
in order to make the switch from userids to usernames in the pkgdb db.
'''

import os
import sys

import sqlalchemy
from turbogears.database import session
from turbogears import config, update_config

from fedora.client.fas2 import AccountSystem

''' These sql statements have to be run in order to modify the schema:

ALTER TABLE collection ALTER COLUMN owner TYPE text USING CAST( owner AS text);

ALTER TABLE log ALTER COLUMN userid TYPE text USING CAST(userid AS text);
ALTER TABLE log RENAME userid TO username;

ALTER TABLE packagelisting ALTER COLUMN owner TYPE text USING CAST(owner AS text);

ALTER TABLE personpackagelisting ALTER COLUMN userid TYPE text USING CAST(userid AS text);
ALTER TABLE personpackagelisting RENAME userid TO username;

-- updating the Log table needs more privileges

GRANT UPDATE ON log TO pkgdbadmin;

-- Be sure to revoke the privilege AFTER the script has done its job
REVOKE UPDATE ON log FROM pkgdbadmin;
'''

# ugly configs so we can import tables from the model
CONFDIR='@CONFDIR@' 
PKGDBDIR=os.path.join('@DATADIR@', 'fedora-packagedb') 
sys.path.append(PKGDBDIR) 

if len(sys.argv) > 1:
    update_config(configfile=sys.argv[1],
        modulename='pkgdb.config')
elif os.path.exists(os.path.join(os.path.dirname(__file__), '..',
        'setup.py')):
    update_config(configfile='pkgdb.cfg',modulename='pkgdb.config')
else:
    update_config(configfile=os.path.join(CONFDIR,'pkgdb.cfg'),
            modulename='pkgdb.config')
config.update({'pkgdb.basedir': PKGDBDIR}) 

from pkgdb.model import Collection, PackageListing, Log, PersonPackageListing

fas_url = config.get('fas.url', 'https://admin.fedoraproject.org/accounts/')
username = config.get('fas.username', 'admin')
password = config.get('fas.password', 'admin')

fas = AccountSystem(fas_url, username=username, password=password,
            cache_session=False)
people = fas.people_by_id()

def transform(relation, attribute):
    ''' Transforms userids into usernames

        relation - pkgdb.model
        attribute - string 'owner' or 'userid'
    '''
    for field in relation.query.all():
        # get the username by id
        username = people[int(getattr(field, attribute))]['username']
        # set it
        getattr(field, '__setattr__')(attribute, username)

for relation in [Collection, PackageListing]:
    print 'transforming ' + relation.__name__
    transform(relation, 'owner')

for relation in [PersonPackageListing, Log]:
    print 'transforming ' + relation.__name__
    transform(relation, 'username')

print 'Flushing...'
session.flush()
