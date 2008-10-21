/*
 * Copyright © 2008  Red Hat, Inc.
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

dojo.require('fedora.dojo.BaseClient');
dojo.require('fedora.dojo.ThrobberGroup');
dojo.require('fedora.dojo.Throbber');

function get_pkgdb_info(event) {
    /* Example of a non-auth'ed page */
    var throbber = new throbber_group.create_throbber();
    var params = {collectionName: 'Fedora', collectionVersion: 'devel'};
    var action = pkgdb.start_request('packages/name/'+ event.target.id, {req_params: params});

    coords = dojo.coords(event.target);
    dojo.attr(throbber.domNode, {style: 'position: absolute; left: ' + (coords.x - coords.l) + '; top: ' + (coords.y - coords.h) + ';'});
    event.target.appendChild(throbber.domNode);
    throbber.start()
    action.addErrback(function(error, args) {
        console.warn('This was the error:' + error);
        console.dir(error);
        return error;
    });

    action.addCallback(function(data, args) {
        console.warn('Returned data:' + data);
        console.dir(data);
        event.target.innerHTML=event.target.id + ' -- ' + data.packageListings[0].package.description;
        return data;
    });
    action.addCallback(throbber.stop);
};

dojo.addOnLoad(function() {
    pkgdb = new fedora.dojo.BaseClient('https://localhost/pkgdb/', {useragent: 'My User Agent/1.0', username:'', password:''});
    throbber_group = new fedora.dojo.ThrobberGroup('https://localhost/pkgdb/static/images/throbber/', 12);

    dojo.query(".package")
        .connect("onclick", get_pkgdb_info);
});
