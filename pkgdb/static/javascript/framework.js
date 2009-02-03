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
 * Javascript doesn't provide a strip function so implement one
 */
String.prototype.strip = String.prototype.strip || function(chars) {
    chars = chars ? chars : "\\s";
    return this.replace(new RegExp("^["+chars+"]*|["+chars+"]*$", "g"), "");
}

/*
 * Create a spinner to show that the element is busy processing.
 */
function create_spinner(initialImage) {
    return DIV({'class': 'spinner', 'border': 0},
            IMG({'src': initialImage, 'class': 'spinnerImage'}));
}

/*
 * Make the spinner turn.
 */
function spin_spinner(timeout, seqNum) {
  /* Only one image so we don't need to run this function. */
  if (spinnerImages.length <= 1) {
    return;
  }

  /* Select the next image in the cycle */
  var imageNum = seqNum +1;
  if (imageNum >= spinnerImages.length) {
    imageNum = 0;
  }

  /* Find all the spinners on the page */
  var spinners = getElementsByTagAndClassName('div', 'spinner');
  for (var spinnerNum in spinners) {
    /* Update all of them to the next image */
    replaceChildNodes(spinners[spinnerNum], IMG (
      {'src': spinnerImages[imageNum], 'alt': 'spinner',
      'class': 'spinnerImage'}
    ));
  }

  /* As long as there are active spinners, reinvoke */
  if (spinners.length > 0) {
    window.setTimeout(spin_spinner,
      timeout*1000, timeout, imageNum);
  } else {
    spinnerCount = 0;
  }
}

/*
 * Show that an element is being processed.
 * Do this by 1) Disabling changes
 * 2) Put a spinner on the element.
 */
function busy(elem, event) {
    /* Create a spinner */
    var spinner = create_spinner(spinnerImages[0]);
   
    /* Display it over the widget */ 
    // MochiKit 1.4 has a getElementPosition() function instead
    var pos = elementPosition(elem);
    spinner.style.position = 'absolute';
    setElementPosition(spinner, pos);
    appendChildNodes(elem, spinner);
    elem.spinner = spinner;

    /* If the spinner isn't spinning, get it started */
    spinnerCount = spinnerCount + 1;
    if (spinnerCount <= 1) {
        spin_spinner(spinnerTimeout, 0);
    }
      
    /* Walk the tree and set everything to disabled */
    nodes = getElementsByTagAndClassName(null, null, elem);
    for (nodeNum in nodes) {
        nodes[nodeNum].setAttribute('disabled', 'true');
    }
}

/*
 * Set the element and children to accept input again.
 */
function unbusy(elem) {
    logDebug('in unbusy');
    /* Remove the spinner */
    spinners = getElementsByTagAndClassName('div', 'spinner', elem);
    for (spinnerNum in spinners) {
        removeElement(spinners[spinnerNum]);
        delete(spinners[spinnerNum]);
        spinnerCount = spinnerCount - 1;
    }
    if (spinnerCount <= 0) {
        spinnerCount = 0;
    }

    /* Walk the tree and remove disabled from everything */
    nodes = getElementsByTagAndClassName(null, null, elem);
    for (nodeNum in nodes) {
        nodes[nodeNum].removeAttribute('disabled');
    }
}

/*
 * Display an error message.  Currently using an alert box but the better
 * plan is some sort of in browser notification box so the browser doesn't go
 * modal on us.
 */
function display_error(container, data) {
    logDebug('in display_error');
    logDebug('data:',data);

    if (data.message) {
        alert(data.message);
    } else {
        alert ('Unable to save the value.  Server was not reachable.');
    }
}

/*
 * Make an xmlhttp request.
 * Using partial to set additional values on your callback and errorback
 * is the recommended way to send more data.  Having the server send the
 * values is next best.  Circumventing make_request because it isn't flexible
 * enough is the last resort.
 */
function make_request(action, callback, errback, event) {
    logDebug('in Make_request');
    var requestContainer = getFirstParentByTagAndClassName(event.target(),
            'div', 'requestContainer');
    busy(requestContainer, event);
    var form = getFirstParentByTagAndClassName(requestContainer, 'form');
    if (form.action[form.action.length - 1] == '/' && action[0] == '/') {
        var url = form.action + action.slice(1);
    } else {
        var url = form.action + action;
    }

    if (url[url.length -1] == '/' && 
            requestContainer.getAttribute('name')[0] == '/') {
        url = url + requestContainer.getAttribute('name').slice(1);
    } else if (url[url.length -1] != '/' &&
            requestContainer.getAttribute('name')[0] != '/') {
        url = url + '/' + requestContainer.getAttribute('name');
    } else {
        url = url + requestContainer.getAttribute('name');
    }

    var req = loadJSONDoc(url);
    if (callback !== null) {
        req.addCallback(partial(callback, requestContainer));
    }
    if (errback !== null) {
        req.addErrback(partial(errback, requestContainer));
    }
    req.addErrback(partial(display_error, requestContainer));
    req.addBoth(unbusy, requestContainer);
    logDebug(url);
}

/* Initialize the spinner */
spinnerImages = ['/pkgdb/static/images/spinner/01.png',
              '/pkgdb/static/images/spinner/02.png',
              '/pkgdb/static/images/spinner/03.png',
              '/pkgdb/static/images/spinner/04.png',
              '/pkgdb/static/images/spinner/05.png',
              '/pkgdb/static/images/spinner/06.png',
              '/pkgdb/static/images/spinner/07.png',
              '/pkgdb/static/images/spinner/08.png',
              '/pkgdb/static/images/spinner/09.png',
              '/pkgdb/static/images/spinner/10.png',
              '/pkgdb/static/images/spinner/11.png',
              '/pkgdb/static/images/spinner/12.png'
              ];
spinnerTimeout = 0.1;
spinnerCount = 0;
