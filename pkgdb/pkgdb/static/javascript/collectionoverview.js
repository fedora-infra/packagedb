/*
 * Copyright © 2007  Red Hat, Inc.
 *
 * This copyrighted material is made available to anyone wishing to use, modify,
 * copy, or redistribute it subject to the terms and conditions of the GNU
 * General Public License v.2.  This program is distributed in the hope that it
 * will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
 * implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU General Public License for more details.  You should have
 * received a copy of the GNU General Public License along with this program;
 * if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
 * Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
 * incorporated in the source code or documentation are not subject to the GNU
 * General Public License and may only be used or replicated with the express
 * permission of Red Hat, Inc.
 *
 * Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
 */

/*
 * Show a tooltip explaining the column.
 */
function show_definition(event) {
    var tooltip = new ToolTip(messages[event.target().id],
            event.mouse().client.x, event.mouse().client.y);
    connect(event.target(), 'onmouseout', tooltip.hide);
    tooltip.show();
}

/*
 * Setup event handlers for the collectionoverview page.
 */
function init(event) {
    /* Global tooltip messages */
    messages = {'collectionhead': 'A distribution of Linux Packages Created and Hosted by the Fedora Project', 
        'versionhead': 'The version of the distribution',
        'packagehead':'Number of packages in the cvs repository for this collection version.  The packages are not necessarily built for this distribution'}

    var columns = getElementsByTagAndClassName('th', 'ColumnHead');
    for (var colNum in columns) {
        connect(columns[colNum], 'onmouseover', show_definition);
    }
}
connect(window, 'onload', init); 
