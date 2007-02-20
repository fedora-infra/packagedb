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
logDebug('in busy');
logDebug(elem);
}

/*
 * Set the element and children to accept input again.
 */
function unbusy(elem) {
logDebug('in unbusy');
logDebug(elem);
}

function toggle_owner(ownerDiv, data) {
    logDebug('in toggle_owner');
    if (! data.status) {
        display_error(data);
        return;
    }
    ownerButton = getElementsByTagAndClassName('input', 'ownerButton',
            ownerDiv)[0];
    if (data['ownerId'] === 9900) {
        /* Reflect the fact that the package is now orphaned */
        swapElementClass(ownerDiv, 'owned', 'orphaned');
        swapElementClass(ownerButton, 'orphanButton', 'unorphanButton');
        ownerButton.setAttribute('value', 'Take Ownership');
    } else {
        /* Show the new owner information */
        swapElementClass(ownerDiv, 'orphaned', 'owned');
        swapElementClass(ownerButton, 'unorphanButton', 'orphanButton');
        ownerButton.setAttribute('value', 'Release Ownership');
    }
    ownerName = getElementsByTagAndClassName('span', 'ownerName', ownerDiv)[0];
    newOwnerName = SPAN({'class' : 'ownerName'}, data['ownerName']);
    insertSiblingNodesBefore(ownerName, newOwnerName);
    removeElement(ownerName);
    logDebug('Exit toggle_owner');
}


/*
 * Revert an aclStatus dropdown to its previous value.  This can happen when
 * the user requests a change but the server throws an error.
 */
function revert_acl_status(statusDiv, data) {
    // FIXME: Have to make sure we pass in the TARGET
    delete(commits[TARGET]);
}

/*
 * Show that an acl can be requested or dropped at this time.
 */
function toggle_acl_request(aclBoxDiv, data) {
}

function display_error(container, data) {
    logDebug('in displap_error');
    logDebug('data:',data);

    if (data.message) {
        alert(data.message);
    } else {
        alert ('Unable to save the value.  Server was not reachable.');
    }
}

/*
 * Save the present value of the acl status field so we can revert it if
 * necessary.
 */
function save_status(event) {
    commits[event.target().id] = event.target().value;
}

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

function init(event) {
    /* Global commits hash.  When a change from the user is anticipated, add
     * relevant information to this hash.  After the change is committed or
     * cancelled, remove it.
     */
    logDebug('In Init');
    commits = {};

    var ownerButtons = getElementsByTagAndClassName('input', 'ownerButton');
    for (var buttonNum in ownerButtons) {
        var request_owner_change = partial(make_request, '/toggle_owner',
                toggle_owner, null);
        connect(ownerButtons[buttonNum], 'onclick', request_owner_change);
    }

    var statusBoxes = getElementsByTagAndClassName('select', 'aclStatusList');
    for (var statusNum in  statusBoxes) {
        var request_status_change = partial(make_request, '/set_acl_status',
                null, revert_acl_status);
        connect(statusBoxes[statusNum], 'onclick', request_status_change);
        connect(statusBoxes[statusNum], 'onfocus', save_status);
    }

    var aclReqBoxes = getElementsByTagAndClassName('input', 'aclPresentBox');
    for (var aclReqNum in aclReqBoxes) {
        var request_add_drop_acl = partial(make_request, '/toggle_acl_request',
            toggle_acl_request, null);
        connect(aclReqBoxes[aclReqNum], 'onclick', request_add_drop_acl);
    }
}

connect(window, 'onload', init);
