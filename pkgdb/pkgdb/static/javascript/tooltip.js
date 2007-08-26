/*
 * Copyright © 2007  Jose Manimala
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
 * Author(s): Toshio Kuratomi <tkuratom@redhat.com>
 *            Jose Manimala <josemm@fedoraproject.org>
 */

/* A ToolTip function for javascript */
ToolTip = function (tip, x, y) {
    logDebug('Create tooltip');
    this.tip = tip;
    this.x = x;
    this.y = y+5;
    this.widget = DIV({'id': 'tooltip', 'class': 'ToolTip'}, tip);
    this.widget.style.position='absolute';
    setElementPosition(this.widget, {'x':this.x, 'y':this.y});
    addElementClass(this.widget, 'invisible');
    appendChildNodes(getElement('collectionhead'), this.widget);
}

ToolTip.prototype.show = function() {
    /* The invisible class makes any element invisible */
    removeElementClass(this.widget, 'invisible');
}

ToolTip.prototype.hide = function() {
    /* We make this invisible and destroy it. */
    this.widget = getElement('tooltip');
    if (this.widget) {
        addElementClass(this.widget, 'invisible');
        removeElement(this.widget);
    }
}
