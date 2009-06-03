/*
 * Copyright © 2008-2009  Red Hat, Inc.
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

dojo.provide('fedora.dojo.Throbber');
dojo.provide('fedora.dojo.ThrobberGroup');

/*
 * Throbber.  Shows that a UI element is busy doing something.  This uses a 
 * ThrobberGroup to manage changing the images for efficiency and individual
 * Throbber widgets for the actual display.
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
        this.watch_throbber = dojo.subscribe('FedoraDojoThrobber', this,
            this._throb);

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
        throbbers = dojo.query('.active.FedoraDojoThrobber' + this.id + 'Img')
            .forEach(dojo.hitch(this, function(node) {
                    node.innerHTML = '<img src="' + this.images[image_num] +
                        '"/>'})
            );

        /* Only set a timeout to cycle the images again if there are active
         * throbbers on the page
         */
        if (throbbers.length) {
            setTimeout(dojo.hitch(this, '_throb', image_num), this.timeout);
        } else {
            /* Otherwise watch for a new throbber */
            this.watch_throbber = dojo.subscribe('FedoraDojoThrobber', this,
                    this._throb);
        }
    },
    create_throbber: function() {
        /* Create a new throbber inside this throbber group */
        return new fedora.dojo.Throbber(this);
    },
    destroy_all_throbbers: function() {
        /* Remove all throbbers on the page */
        dojo.query('.FedoraDojoThrobber' + this.id + 'Img')
            .orphan().forEach(function(node) {node.empty();})
    }
});

dojo.declare('fedora.dojo.Throbber', null, {
    statics: {nextid: 0},
    constructor: function(group, kw) {
        this.id = 'FedoraDojoThrobber' + group.id + '-' +
                (this.statics.nextid++);
        this.group = group;
        kw= kw || {};
        this.domNode = dojo.doc.createElement('span');
        dojo.attr(this.domNode, {id: this.id,
            class: 'FedoraDojoThrobber' + this.group.id + 'Img'
        });
        if (kw['position']) {
            this.set_position(kw['position']);
        }
    },
    set_position: function(position) {
        var coords, img;
        if (dojo.isArray(position)) {
            this.position = position;
        } else {
            coords = dojo.coords(position);
            img = new Image();
            img.src = this.group.images[0];

            this.position = [coords.l - (img.width/4),
                coords.t - (img.height/4)];
        }
        dojo.attr(this.domNode, {style: 'position: absolute; left: ' +
                this.position[0] + 'px; top: ' + this.position[1] + 'px;'
        });
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
