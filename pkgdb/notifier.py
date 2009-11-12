# -*- coding: utf-8 -*-
#
# Copyright © 2007-2009  Red Hat, Inc.
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
from pkgdb import _
from pkgdb.utils import LOG

class Event(object):
    '''Data structure to constrain an event record to just a few fields.
    '''
    __attributes__ = ['author', 'change', 'subject', 'description']

class EventLogger(object):
    '''Notify others of events.'''
    MAILFROM = config.get('email.sender',
            ('PackageDB', 'pkgdb@fedoraproject.org'))

    def __init__(self):
        # Eventually this could contact a notification server and use that to
        # send out notifications
        #
        # Eventually this could handle logging of changes as well.
        pass

    def _send_msg(self, msg, subject, recipients, from_addr=None):
        '''Send an email from the packagedb.'''
        if not from_addr:
            from_addr = self.MAILFROM

        if config.get('mail.on', False):
            for person in recipients:
                email = turbomail.Message(from_addr, person,
                        '[pkgdb] %s' % (subject,))
                email.plain = msg
                turbomail.enqueue(email)
        else:
            LOG.debug(_('Would have sent: %(subject)s') % {
                'subject': subject.encode('ascii', 'replace')})
            LOG.debug('To: %s' % recipients)
            LOG.debug('From: %s %s' %
                    (from_addr[0].encode('ascii', 'replace'),
                    from_addr[1].encode('ascii', 'replace')))
            LOG.debug('%s' % msg.encode('ascii', 'replace'))

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
