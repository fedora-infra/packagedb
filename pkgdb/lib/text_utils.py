# -*- coding: utf-8 -*-
#
# Copyright © 2009  Red Hat, Inc.
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
# Red Hat Project Author(s): Martin Bacovsky <mbacovsk@redhat.com>
#
'''
Utilities for text manipulation
'''

import re

def excerpt(text, pattern, max=60, all=False):
    """ Returns selected sentences containing pattern with 
    length up to given size. If max sentence length is exceeded,
    it is trimmed and '...' dots are added to mark the cut(s)

    :text:      text source we trying to excerpt
    :pattern:   pattern we are looking for
    :max:       maximal allowed sentence length
    :all:       find all sentences matching pattern

    :returns:    list of sentences
    """


    p = re.compile(r'\W+')
    pattern = p.sub(' ', pattern)

    p = re.compile('(\\b[A-Z][^.]*)?(%s)([^.]*(?:\\.|$))' % pattern.replace(' ','|'), re.I|re.S|re.L)
    if all:
        sentences = p.findall(text)
    else:
        match = p.search(text)
        if match:
            sentences = [match.groups()]
        else:
            sentences = []

    result = []
    for sentence in sentences:
        b = sentence[0] or ''
        len_b = len(b)
        p = sentence[1] 
        len_p = len(p)
        e = sentence[2] or ''
        len_e = len(e)
        dots = '...'
        len_dots = len(dots)
        
        # it fits
        if len_b + len_p + len_e <= max:
            result.append(b+p+e)
            continue

        # we can cut just e
        if len_b + len_p <= max-len_dots:
            stop = max - len_dots - len_b - len_p
            end = e.rfind(' ', 0, stop)
            if end == -1:
                end = stop
            result.append(b+p+e[:end]+dots)
            continue

        # we have to cut from both ends
        stop = (max - len_p) / 2 - len_dots
        start = e.rfind(' ', 0, stop)
        if start == -1:
            start = stop
        else:
            start += 1  # omit that space
        stop = max - (len_b - start) - 2*len_dots
        end = e.rfind(' ', 0, stop)
        if end == -1:
            end = stop
        result.append(dots+b[start:]+p+e[:end]+dots)
            
    if not all:
        return ''.join(result)

    return result


def highlight(text, pattern, pre='<span class="highlight">', post='</span>'):
    p = re.compile(r'\W+')
    pattern = p.sub(' ', pattern)
    p = re.compile('(%s)' % pattern.replace(' ','|'), re.I)
    result = p.sub(pre+r'\1'+post, text)
    return result
