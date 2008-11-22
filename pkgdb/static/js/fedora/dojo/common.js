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

/* Overall provide for this module */
dojo.provide('fedora.dojo.common');

/* Exceptions */
dojo.provide('fedora.dojo.AppError');
dojo.provide('fedora.dojo.AuthError');
dojo.provide('fedora.dojo.MalformedPageError');

/* Functions */
dojo.provide('fedora.dojo.ancestor');

/*****************
 * Exceptions
 */

/*
 * This exception is used when the BaseClient needs to tell client code that
 * the server returned an exception.
 */
dojo.declare('fedora.dojo.AppError', [Error], {
    constructor: function(message, extras) {
        this.name = 'AppError';
        this.message = message;
        this.extras = extras || null;
    }
});

/*
 * This exception is used when the BaseClient needs to tell client code that
 * authentication failed.
 */
dojo.declare('fedora.dojo.AuthError', [Error], {
    constructor: function(message, extras) {
        this.name = 'AuthError';
        this.message = message;
        this.extras = extras || null;
    }
});

/*
 * This exception is returned when a page doesn't have the structure that we
 * want.  This could be an error on the server returning a page with incorrect
 * classes or incorrectly nested html elements.  Or it could be an error where
 * previous dynamic javascript has rewritten the page in an incompatible way.
 */
dojo.declare('fedora.dojo.MalFormedPageError', [Error], {
    constructor: function(message, extras) {
        this.name = 'MalformedPageError';
        this.message = message;
        this.extras = extras || null;
    }
});

/************************
 * Functions
 */

/*
 * Filter function to return nodes that are the ancestor of a known node.
 */
fedora.dojo.ancestor = function (child, item, index, arr) {
    return dojo.isDescendant(child, item);
}
