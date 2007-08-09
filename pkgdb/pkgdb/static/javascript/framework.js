/* 
 * From MochiKit 1.4
 */

/** @id MochiKit.DOM.insertSiblingNodesBefore */
insertSiblingNodesBefore = function (node/*, nodes...*/) {
    var elem = node;
    var self = MochiKit.DOM;
    if (typeof(node) == 'string') {
        elem = self.getElement(node);
    }
    var nodeStack = [
        self.coerceToDOM(
            MochiKit.Base.extend(null, arguments, 1),
            elem
        )
    ];
    var parentnode = elem.parentNode;
    var concat = MochiKit.Base.concat;
    while (nodeStack.length) {
        var n = nodeStack.shift();
        if (typeof(n) == 'undefined' || n === null) {
            // pass
        } else if (typeof(n.nodeType) == 'number') {
            parentnode.insertBefore(n, elem);
        } else {
            nodeStack = concat(n, nodeStack);
        }
    }
    return parentnode;
}

/** @id MochiKit.DOM.getFirstParentByTagAndClassName */
getFirstParentByTagAndClassName = function (elem, tagName, className) {
    var self = MochiKit.DOM;
    elem = self.getElement(elem);
    if (typeof(tagName) == 'undefined' || tagName === null) {
        tagName = '*';
    } else {
        tagName = tagName.toUpperCase();
    }
    if (typeof(className) == 'undefined' || className === null) {
        className = null;
    }

    var classList = '';
    var curTagName = '';
    while (elem && elem.tagName) {
        elem = elem.parentNode;
        if (tagName == '*' && className === null) {
            return elem;
        }
        classList = elem.className.split(' ');
        curTagName = elem.tagName.toUpperCase();
        if (className === null && tagName == curTagName) {
            return elem;
        } else if (className !== null) {
            for (var i = 0; i < classList.length; i++) {
                if (tagName == '*' && classList[i] == className) {
                    return elem;
                } else if (tagName == curTagName && classList[i] == className) {
                    return elem;
                }
            }
        }
    }
    return elem;
}
/* End from MochiKit 1.4.1 */

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
        var url = form.action + action
    }

    var req = loadJSONDoc(url
            {'containerId': requestContainer.getAttribute('name')});
    if (callback !== null) {
        req.addCallback(partial(callback, requestContainer));
    }
    if (errback !== null) {
        req.addErrback(partial(errback, requestContainer));
    }
    req.addErrback(partial(display_error, requestContainer));
    req.addBoth(unbusy, requestContainer);
    logDebug(url+'?'+queryString({'containerId': requestContainer.getAttribute('name')}));
}

/* Initialize the spinner */
spinnerImages = ['/pkgdb-dev/static/images/spinner/01.png',
              '/pkgdb-dev/static/images/spinner/02.png',
              '/pkgdb-dev/static/images/spinner/03.png',
              '/pkgdb-dev/static/images/spinner/04.png',
              '/pkgdb-dev/static/images/spinner/05.png',
              '/pkgdb-dev/static/images/spinner/06.png',
              '/pkgdb-dev/static/images/spinner/07.png',
              '/pkgdb-dev/static/images/spinner/08.png',
              '/pkgdb-dev/static/images/spinner/09.png',
              '/pkgdb-dev/static/images/spinner/10.png',
              '/pkgdb-dev/static/images/spinner/11.png',
              '/pkgdb-dev/static/images/spinner/12.png'
              ];
spinnerTimeout = 0.1;
spinnerCount = 0;
