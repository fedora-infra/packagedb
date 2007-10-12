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
Classes for notifications
'''

import logging

import turbomail
from turbogears import config

log = logging.getLogger('pkgdb.controllers')

class Event(object):
    __attributes__ = ['author', 'change', 'subject', 'description']
    pass

class EventLogger(object):
    '''Notify others of events.'''
    MAILFROM = config.get('email.sender', ('PackageDB', 'pkgdb@fedoraproject.org'))

    def __init__(self):
        # Eventually this could contact a notification server and use that to
        # send out notifications
        #
        # Eventually this could handle logging of changes as well.
        pass

    def _send_msg(self, msg, subject, recipients, fromAddr=None):
        '''Send an email from the packagedb.'''
        if not fromAddr:
            fromAddr = self.MAILFROM
        ### For DEBUGing:
        print 'Would have sent: %s' % subject.encode('ascii', 'replace')
        print 'To: %s' % recipients
        print 'From: %s %s' % (fromAddr[0].encode('ascii', 'replace'),
                fromAddr[1].encode('ascii', 'replace'))
        print '%s' % msg.encode('ascii', 'replace')
        return
        for person in recipients:
            email = turbomail.Message(fromAddr, person, '[pkgdb] %s' % (subject,))
            email.plain = msg
            turbomail.enqueue(email)

    # The eventual plan is to abstract this one layer.  The application alerts
    # us to an event via a notify() method.  The notify() method needs to know
    # - Who made the change
    # - What change is made
    # - What the change was made to.
    # - Using that information, it can construct an event that it deals with.
    # Processing could include:
    # - Log change to a database
    # - Send event to a notification server
    # - Update queues with changes that need to be made to other systems.
    send_msg = _send_msg
