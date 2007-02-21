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
 * Show that an element is being processed.
 * Do this by 1) Disabling changes
 * 2) Put a spinner on the element.
 */
function busy(elem) {
    // Pop up a small animated image that fits over the widget.
    // FIXME: Walk the tree and set everything to disabled
    logDebug('in busy');
logDebug(elem);

}

/*
 * Set the element and children to accept input again.
 */
function unbusy(elem) {
    //FIXME: Walk the tree and remove disabled from everything
    // Remove the spinner
logDebug('in unbusy');
logDebug(elem);
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
    busy(requestContainer);
    var form = getFirstParentByTagAndClassName(requestContainer, 'form');
    var base = form.action;
    var req = loadJSONDoc(base + action,
            {'containerId': requestContainer.getAttribute('name')});
    if (callback !== null) {
        req.addCallback(partial(callback, requestContainer));
    }
    if (errback !== null) {
        req.addErrback(partial(errback, requestContainer));
    }
    req.addErrback(partial(display_error, requestContainer));
    req.addBoth(unbusy, requestContainer);
    logDebug(base+action+'?'+queryString({'containerId': requestContainer.getAttribute('name')}));
}

