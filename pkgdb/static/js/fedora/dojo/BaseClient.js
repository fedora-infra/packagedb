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

dojo.provide('fedora.dojo.BaseClient');
dojo.provide('fedora.dojo.Throbber');
dojo.provide('fedora.dojo.ThrobberGroup');

/*
 * A simple throbber that shows that an item is busy.
 */
dojo.declare('fedora.dojo.ThrobberGroup', null, {
    statics: {nextid: 0},
    constructor: function(base_url, num_images, kw) {
        kw = kw || {};
        this.base_url = base_url;
        this.id = this.statics.nextid++;
        /* Throb every tenth of a second by default */
        this.timeout = kw['timeout'] || 100;
        this.inactive_image = kw['inactive_image'] || null;
        this.images = [];
        var extension = kw['extension'] || '.png';
        var i;
        var precache = new dojo.Deferred();

        /* Connect an event to the throbbers so that we know when to make the
         * image cycling active
         */
        this.watch_throbber = dojo.subscribe('FedoraDojoThrobber', this, this._throb);

        /* Create the list of images */
        for (i = 0; i < num_images; i++) {
            this.images[i] = this.base_url + i + extension;
        }

        if (!this.inactive_image) {
            this.inactive_image = this.images[0];
        }
        /* Precache the images asynchronously */
        precache.addCallback(this._precache());
    },
    _precache: function(data) {
        /* Precache the  images for the throbber */
        for (i = 0; i < this.images.length; i++) {
            new Image().src = this.images[i];
        }
        new Image().src = this.inactive_image;
        return data;
    },
    _throb: function(seq_num) {
        /* Change the image for all the throbbers in the group 
         *
         * :arg seq_num: Index of the currently displayed image
         */
        if (typeof(seq_num) == 'undefined') {
            seq_num = -1;
        }
        if (this.watch_throbber) {
            /* Stop looking for new throbbers until all throbbers are stopped
             */
            dojo.unsubscribe(this.watch_throbber);
            this.watch_throbber = null;
        }

        var image_num = seq_num + 1;
        var throbbers;

        /* Only one image, no need to run this method */
        if (this.images.length <= 1) {
            return;
        }

        /* Select the next image in the cycle */
        if (image_num >= this.images.length) {
            image_num = 0;
        }

        /* Update all the active throbbers */
        throbbers = dojo.query('.active.FedoraDojoThrobberImg').forEach(dojo.hitch(this, function(node) {node.innerHTML='<img src="' + this.images[image_num] + '"/>'}));

        /* Only set a timeout to cycle the images again if there are active
         * throbbers on the page
         */
        if (throbbers.length) {
            setTimeout(dojo.hitch(this, '_throb', image_num), this.timeout);
        } else {
            /* Otherwise watch for a new throbber */
            this.watch_throbber = dojo.subscribe('FedoraDojoThrobber', this, this._throb);
        }
    },
    create_throbber: function() {
        /* Create a new throbber inside this throbber group */
        return new fedora.dojo.Throbber(this);
    },
    destroy_all_throbbers: function() {
        /* Remove all throbbers on the page */
        dojo.query('.FedoraDojoThrobberImg')
            .orphan().forEach(function(node) {node.empty();})
    }
});

dojo.declare('fedora.dojo.Throbber', null, {
    statics: {nextid: 0},
    constructor: function(group) {
        // FIXME: Give Each throbber its own position
        // FIXME: Check that the throbbers have different ids
        // FIXME: Add the throbber_group id into the throbber
        this.id = this.statics.nextid++;
        this.group = group;
        this.domNode = dojo.doc.createElement('span');
        dojo.attr(this.domNode, {id: this.id, 'class': 'active FedoraDojoThrobberImg'});
    },
    start: function() {
        /* Turn the throbber on */
        dojo.query('#' + this.id).addClass('active');
        dojo.publish('FedoraDojoThrobber');
    },
    stop: function() {
        /* Turn the throbber off */
        dojo.query('#' + this.id).removeClass('active')
            .forEach(dojo.hitch(this, function(node) {node.innerHTML=
                    '<img src="' + this.group.inactive_image + '"/>'}));
    },
    destroy: function() {
        /* Remove the throbber from the DOM */
        dojo.query('#' + this.id).empty().orphan();
    },
});


/*
 * This is the initial port of the python BaseClient to Dojo.  Be careful in
 * using this as not all concepts have been translated to Dojo verbatim. In
 * particular, we take advantage of Dojo's asynchronous xhr calls whereas
 * ProxyClient and BaseClient are synchronous.  In practical terms, code like
 * this in python::
 *      client = BaseClient(url)
 *      data = client.send_request(action, params)
 *      do_things(data)
 *
 * will be done like this using DojoClient::
 *      client = DojoClient(url);
 *      deferred = client.start_request(action, params);
 *      deferred.addCallback(do_things);
 *
 * Deferreds are a more powerful metaphor and better for actions that could
 * have long latencies (as can happen over the Internet) but Twisted provides
 * them for python and not everyone is comfortable with that.
 *
 */
dojo.declare('fedora.dojo.BaseClient', null, {
    base_url : null,
    useragent: 'Fedora DojoClient/0.1',
    session_name: 'tg-visit',
    debug: false,
    username: null,
    password: null,
    constructor: function(base_url, kw) {
        /* 
         * Create a client configured for a particular service.
         *
         * :arg base_url: Base of every URL used to contact the server
         * :kwarg useragent: useragent string to use.  If not given, default
         *      to "Fedora DojoClient/VERSION"
         * :kwarg session_name: name of the cookie to use with session
         *      handling.  Default: 'tg-visit'
         * :kwarg username: Username for establishing authenticated connections
         * :kwarg password: Password to use with authenticated connections
         * :kwarg debug: If True, log debug information Default: false
         */
        if (!base_url) {
            throw {'name': 'TypeError',
                'message': 'You must give a base_url to DojoClient()'};
        }
        if (base_url.charAt(base_url.length - 1) != '/') {
            base_url = base_url + '/';
        }
        this.base_url = base_url;

        this.useragent = kw['useragent'] || this.useragent;
        this.session_name = kw['session_name'] || this.session_name;
        this.debug = kw['debug'] || this.debug;
        this.username = kw['username'] || this.username;
        this.password = kw['password'] || this.password;
    },
    /*
     * Make an HTTP request to a server method.
     *
     * This is similar to send_request() from the python BaseClient but
     * different in that it makes an asynchronous request instead of a
     * synchronous request.
     *
     * The given method is called with any parameters set in
     * ``req_params``.  If auth is True, then the request is made with an
     * authenticated session cookie.  Note that path parameters should be
     * set by adding onto the method, not via ``req_params``.
     *
     * :arg method: Method to call on the server.  It's a url fragment
     *      that comes after the base_url set in __init__().  Note that
     *      any parameters set as extra path information should be listed
     *      here, not in ``req_params``.
     * :kwarg req_params: dict containing extra parameters to send to the
     *      server
     * :kwarg auth: If True, perform authentication to the server.
     * :kwarg timeout: Milliseconds to wait for a response.  Default 600000:
     *      10 minutes.
     * :returns: Deferred that will give data back to the function.  Set a
     *      callback on the Deferred using .addCallback().  Set an error
     *      handler using.addErrorback().
     * :rtype: Dojo.Deferred
     */
    start_request: function(method, kw) {
        kw = kw || {};
        method = method.replace(/^\/+/,'');
        var timeout = kw['timeout'] || 60000;
        var params = kw['req_params'] || {};

        /* If username and password are set, then use them to authenticate
         * otherwise we have to rely on the session cookie
         */
        if (kw['auth'] && this.username && this.password) {
            params['user_name'] = this.username;
            params['password'] = this.password;
            params['login'] = 'Login';
        }
        action = dojo.xhrPost({url: this.base_url + method,
            headers: {Accept: 'text/javascript',
                'User-agent': this.useragent},
            content: params,
            handleAs:"json",
            load: function(data, args) {
                /* If we're dealing with an error from the server, send us
                 * into the errorback chain.
                 */
                if (data['exc']) {
                    throw {name: data['exc'],
                        message: data['tg_flash']
                    };
                }
                return data;
            },
            /* If we have an error during authentication, we get back an http
             * 403.  This errorback changes the 403 into an exception that
             * can simply be detected by the exception name.  That way
             * consuming code doesn't have to look at error.status just to
             * check for username/password.
             */
            error: function (error, args) {
                if (error.status == 403) {
                    error.name = 'AuthError';
                    error.message = 'Unable to log into server.  Invalid' +
                            ' authentication tokens.  Send new username and' +
                            ' password: ' + error.message;
                }
                return error;
            },
            timeout: timeout,
        });

        return action;
    },
    /* Logout from the server.
     *
     * :returns: Deferred so you can attach a callback/errorback if you want to
     *      do something special after the logout is processed.
     */
    logout: function() {
        logout_action = dojo.xhrPost({
            url: this.base_url + 'logout',
            handleAs: "json",
            /* Don't need a callback because any success is fine */
            error: function(error, args) {
                if (error.status == 403) {
                    /* a 403 is fine since it means we aren't authenticated.
                     * Anything else means we propogate the error.
                     */
                    return {}
                }
            },
            timeout: 5000,
        });
        return logout_action;
    },
});
