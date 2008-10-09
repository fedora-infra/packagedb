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
 * Create select lists for approving acls
 */
function set_acl_approval_box(aclTable, add, aclStatusFields) {
    logDebug('Enter set_acl_approval_box');
    if (add) {
        /* Adding Status option lists is easy.  Just replace all the child
         * nodes in the cell with a drop down that selects the current
         * approval level.
         */
        var aclFields = getElementsByTagAndClassName('td', 'aclcell', aclTable);
        var aclStatus = null;
        for (var aclFieldNum in aclFields) {
            aclStatus = getElementsByTagAndClassName(null, 'aclStatus',
                    aclFields[aclFieldNum])[0];

            /* If we don't encounter a SPAN then this has already been flipped
             * to a SELECT.
             */
            if (aclStatus['nodeName']=='SPAN') {
                /* Create the new select list */
                var aclName = aclStatus.getAttribute('name').strip();
                var aclStatusName = scrapeText(aclStatus).strip();
                var newAclStatusList = SELECT({'name': aclName,
                        'class' : 'aclStatusList'});
                connect(newAclStatusList, 'onchange', request_status_change);
                connect(newAclStatusList, 'onfocus', save_status);

                /* Populate it with options */
                for (var aclNum in aclStatusFields) {
                    if (aclStatusName === aclStatusFields[aclNum]) {
                        aclOption = OPTION({'selected' : 'true'},
                                aclStatusFields[aclNum]);
                    } else {
                        aclOption = OPTION(null, aclStatusFields[aclNum]);
                    }
                    appendChildNodes(newAclStatusList, aclOption);
                }

                /* Create the requestContainer that holds the statusList */
                var newAclStatus = DIV({'name': aclName,
                        'class' : 'requestContainer aclStatus'},
                        newAclStatusList);
                /* Replace the span */
                replaceChildNodes(aclFields[aclFieldNum], newAclStatus);
            }
        }
    } else {
        /* Remove selects and create a span label instead.  Loop through the
         * aclrows to do this.  If there's an aclrow that belongs to the tg
         * user, add checkboxes for them to request acls.
         */
        var aclRows = getElementsByTagAndClassName('tr', 'aclrow', aclTable);
        for (aclRowNum in aclRows) {
            var aclUser = getElementsByTagAndClassName('td', 'acluser',
                    aclRows[aclRowNum])[0];
            var aclUserId = aclUser.getAttribute('name').split(':');
            var createRequestBox = false;
            if (aclUserId[1] == tgUserUserId) {
                createRequestBox = true;
            }
            /* Loop through the aclcells, creating the spans and
             * checkboxes if necessary
             */
            var aclFields = getElementsByTagAndClassName('td', 'aclcell',
                    aclRows[aclRowNum]);
            for (var aclFieldNum in aclFields) {
                /* Find the current status */
                aclStatus = getElementsByTagAndClassName(null, 'aclStatusList',
                        aclFields[aclFieldNum])[0];
                aclStatusDiv = getElementsByTagAndClassName(null, 'aclStatus',
                        aclFields[aclFieldNum])[0];
                if (aclStatus['nodeName'] === 'SELECT') {
                    var aclName = aclStatusDiv.getAttribute('name');
                    var aclStatusName = aclStatus.value;
                    var aclOptions = getElementsByTagAndClassName('option',
                            null, aclStatus);
                    /* Create the new span and add it */
                    var newAclStatus = SPAN({'name' : aclName,
                            'class' : 'aclStatus'}, aclStatusName);
                    replaceChildNodes(aclFields[aclFieldNum], newAclStatus);

                    /* If the user needs a checkbox to request the acl */
                    if (createRequestBox) {
                        if (aclStatusName) {
                            var aclRequestBox = INPUT({'type' : 'checkbox',
                                'class' : 'aclPresentBox', 'checked' : 'true'});
                        } else {
                            var aclRequestBox = INPUT({'type' : 'checkbox',
                                'class' : 'aclPresentBox'});
                        }
                        var requestContainer = DIV({'class':
                                'requestContainer aclPresent', 'name': aclName},
                                aclRequestBox);
                        insertSiblingNodesBefore(newAclStatus, requestContainer);
                        connect(aclRequestBox, 'onclick', request_add_drop_acl);
                    }
                }
            }
        }
    }

    /* Change the groupacl checkboxes now as well. */
    /* Retrieve the group acl boxes */
    var aclStatusContainers = getElementsByTagAndClassName('div',
            'groupAclStatus', aclTable);
    var groupAclLabel = SPAN(null, 'group members can commit?');
    for (aclStatusContainerNum in aclStatusContainers) {
        if (add) {
            /* Enable the checkboxes so the user can click them */
            var aclStatusBox = getElementsByTagAndClassName('input',
                    'groupAclStatusLabelBox',
                    aclStatusContainers[aclStatusContainerNum])[0];
            if (!aclStatusBox) {
                /* This has already been turned on -- probably because the
                 * person has approveacls
                 */
                continue;
            }
            if (aclStatusBox.hasAttribute('checked')) {
                var newAclBox = INPUT({'type' : 'checkbox', 'checked' : 'true',
                        'class' : 'groupAclStatusBox'});
            } else {
                var newAclBox = INPUT({'type' : 'checkbox', 'class' :
                        'groupAclStatusBox'});
                newAclBox.removeAttribute('checked');
            }
            connect(newAclBox, 'onclick', request_approve_deny_groupacl);
        } else {
            /* Disables the checkboxes so the user can't click on them */
            var aclStatusBox = getElementsByTagAndClassName('input',
                    'groupAclStatusBox',
                    aclStatusContainers[aclStatusContainerNum])[0];
            if (aclStatusBox.hasAttribute('checked')) {
                var newAclBox = INPUT({'type' : 'checkbox', 'checked' : 'true',
                        'disabled' : 'true', 
                        'class' : 'groupAclStatusLabelBox'});
            } else {
                var newAclBox = INPUT({'type' : 'checkbox', 'disabled' : 'true',
                        'class' : 'groupAclStatusLabelBox'});
                newAclBox.removeAttribute('checked');
            }
        }
        replaceChildNodes(aclStatusContainers[aclStatusContainerNum],
                groupAclLabel, newAclBox);
    }
}

function toggle_owner(ownerDiv, data) {
    logDebug('in toggle_owner');
    if (! data.status) {
        display_error(null, data);
        return;
    }
    var ownerButton = getElementsByTagAndClassName('input', 'ownerButton',
            ownerDiv)[0];
    var aclTable = getElementsByTagAndClassName('table', 'acls',
            getFirstParentByTagAndClassName(ownerDiv, 'table', 'pkglist'))[0];
    if (data['ownerId'] === 9900) {
        /* Reflect the fact that the package is now orphaned */
        swapElementClass(ownerDiv, 'owned', 'orphaned');
        swapElementClass(ownerButton, 'orphanButton', 'unorphanButton');
        ownerButton.setAttribute('value', 'Take Ownership');
        set_acl_approval_box(aclTable, false);
        /** FIXME: Need to find the Status box and update it as well */
    } else {
        /* Show the new owner information */
        swapElementClass(ownerDiv, 'orphaned', 'owned');
        swapElementClass(ownerButton, 'unorphanButton', 'orphanButton');
        ownerButton.setAttribute('value', 'Release Ownership');
        set_acl_approval_box(aclTable, true, data['aclStatusFields']);
        /** FIXME: Need to find the Status box and update it as well */
    }
    var ownerName = getElementsByTagAndClassName('span', 'ownerName', ownerDiv)[0];
    var newOwnerName = SPAN({'class' : 'ownerName'}, data['ownerName']);
    insertSiblingNodesBefore(ownerName, newOwnerName);
    removeElement(ownerName);
}

function check_acl_status(statusDiv, data) {
    logDebug('in check_acl_status');
    /* The only thing we have to do is check that there weren't any errors */
    if (! data.status) {
        revert_acl_status(statusDiv, data);
        display_error(null, data);
        return;
    }
    delete(commits[statusDiv])
}

/*
 * Revert an aclStatus dropdown to its previous value.  This can happen when
 * the user requests a change but the server throws an error.
 */
function revert_acl_status(statusDiv, data) {
    logDebug('in revert_acl_status');
    /* Retrieve the select list */
    var aclStatus = getElementsByTagAndClassName('select', 'aclStatusList',
            statusDiv)[0];
    
    /* Set it to the previous value */
    aclStatus.value = commits[statusDiv];

    /* Remove the entry from the commits list */
    delete(commits[statusDiv]);

    logDebug('Falling off the end of revert_acl_status');
}

/*
 * Save the present value of the acl status field so we can revert it if
 * necessary.
 */
function save_status(event) {
    /* Get the requestContainer */
    var requestContainer = getFirstParentByTagAndClassName(event.target(),
            'div', 'requestContainer');
    /* Save the old value keyed by the requestContainer */
    commits[requestContainer] = event.target().value
        event.target().value;
}

/*
 * Show whether an acl is currently requested for this package listing.
 */
function check_acl_request(aclBoxDiv, data) {
    logDebug('in check_acl_request');
    /* If an error occurred, toggle it back */
    if (! data.status) {
        revert_acl_request(aclBoxDiv, data);
        display_error(null, data);
        return;
    }
    /* No error, so update the status to reflect the acl status. */
    var aclCell = getFirstParentByTagAndClassName(aclBoxDiv, 'td',  'aclcell');
    var oldAclStatus = getElementsByTagAndClassName('span', 'aclStatus',
            aclCell);
    for (aclStatusNum in oldAclStatus) {
        removeElement(oldAclStatus[aclStatusNum]);
    }
    var aclBoxId = aclBoxDiv.getAttribute('name');
    var aclStatus = SPAN({'name' : aclBoxId, 'class' : 'aclStatus'},
            data.aclStatus);
    appendChildNodes(aclBoxDiv, aclStatus);
}

function revert_acl_request(aclBoxDiv, data) {
    logDebug('in rever_acl_request');
    var aclBox = getElementsByTagAndClassName('input', 'aclPresentBox', aclBoxDiv)[0];
    /* The browser doesn't let us change the toggle status so we have to
     * create a new checkbox
     */
    /* Since this is a simple toggle, just toggle it back */
    if (aclBox.hasAttribute('checked')) {
        var newAclBox = INPUT({'type' : 'checkbox', 'class' : 'aclPresentBox',
                'checked' : 'true'});
    } else {
        var newAclBox = INPUT({'type' : 'checkbox', 'class' : 'aclPresentBox'});
        newAclBox.removeAttribute('checked');
    }
    connect(newAclBox, 'onclick', request_add_drop_acl);
    replaceChildNodes(aclBoxDiv, newAclBox);
}

function check_groupacl_request(aclBoxDiv, data) {
    logDebug('in check_groupacl_request');
    /* If an error occurred, toggle it back */
    if (! data.status) {
        revert_groupacl_request(aclBoxDiv, data);
        display_error(null, data);
        return;
    }

    /* For some reason firefox doesn't pick this up.  Reconfirm the changes */
    var label = SPAN(null, 'group members can commit?');
    var aclBox = getElementsByTagAndClassName('input', 'groupAclStatusBox', aclBoxDiv)[0];
    if (aclBox.hasAttribute('checked')) {
        var newAclBox = INPUT({'type' : 'checkbox', 'class' : 'groupAclStatusBox'});
        newAclBox.removeAttribute('checked');
    } else {
        var newAclBox = INPUT({'type' : 'checkbox', 'class' : 'groupAclStatusBox',
                'checked' : 'true'});
    }
    connect(newAclBox, 'onclick', request_approve_deny_groupacl);
    replaceChildNodes(aclBoxDiv, label, newAclBox);
}

function revert_groupacl_request(aclBoxDiv, data) {
    logDebug('in revert_groupacl_request');
    var aclBox = getElementsByTagAndClassName('input', 'groupAclStatusBox', aclBoxDiv)[0];
    /* The browser doesn't let us change the toggle status so we have to
     * create a new checkbox
     */
    /* Since this is a simple toggle, just toggle it back */
    var label = SPAN(null, 'group members can commit?');
    if (aclBox.hasAttribute('checked')) {
        var newAclBox = INPUT({'type' : 'checkbox', 'class' : 'groupAclStatusBox',
                'checked' : 'true'});
    } else {
        var newAclBox = INPUT({'type' : 'checkbox', 'class' : 'groupAclStatusBox'});
        newAclBox.removeAttribute('checked');
    }
    connect(newAclBox, 'onclick', request_approve_deny_groupacl);
    replaceChildNodes(aclBoxDiv, label, newAclBox);
}

function toggle_shouldopen(ignored, data) {
	if (data.status == false) toggle_shouldopen_failure(ignored, data);
}

function toggle_shouldopen_failure(ignored, data) {
    var shouldOpenBox = getElementsByTagAndClassName('input', 'shouldOpenBox')[0];
    shouldOpenBox.checked = !shouldOpenBox.checked
    display_error(null, data);
}


function request_acl_gui(event) {
    var buttonRow = getFirstParentByTagAndClassName(event.target(), 'tr');
    var pkgListTable = getFirstParentByTagAndClassName(buttonRow, 'table',
            'pkglist');
    
    /* Check that this user doesn't already have an acl GUI setup */
    var oldAclUsers = getElementsByTagAndClassName('td', 'acluser', pkgListTable);
    for (var aclNum in oldAclUsers) {
        idParts = oldAclUsers[aclNum].getAttribute('name').split(':');
        if (idParts[1] == tgUserUserId) {
            /* User already has an acl gui.  No need to create a new one. */
            return;
        }
    }
    var aclTable = getElementsByTagAndClassName('table', 'acls', pkgListTable)[0];

    // FIXME: We should have the acls handed over in a JSON array in the
    // template so that we could operate on it as javascript now.  But we
    // don't.
    acls = ['watchbugzilla', 'watchcommits', 'commit', 'approveacls'];
    var newAclRow = TR({'class' : 'aclrow'},
            TD({'class' : 'acluser',
                'name': pkgListTable.getAttribute('name') + ':' + tgUserUserId},
                tgUserDisplayName + ' (' + tgUserUserName + ')'
            ))
    for (var aclNum in acls) {
        // FIXME: If the user is also the owner, create aclStatus as a select
        // list instead of a span so they can approve acls for themselves.
        // Have to add the pkg owner information to the table somewhere.
        // Probaby <span class='ownerName'
        //    name='pkgListId:ownerId'>username</span>
        // is the place to store that.
        var aclStatus = SPAN({'class': 'aclStatus',
            'name': pkgListTable.getAttribute('name') + ':' + acls[aclNum]});
        var aclReqBox = INPUT({'type' : 'checkbox', 'class' : 'aclPresentBox'})
        connect(aclReqBox, 'onclick', request_add_drop_acl);
        var newAclCell = TD({'class' : 'aclcell'},
                DIV({'name' : pkgListTable.getAttribute('name') + ':' + acls[aclNum],
                    'class' : 'requestContainer aclPresent'},
                    aclReqBox
                   ), aclStatus
                );
        appendChildNodes(newAclRow, newAclCell);
    }
    /*
     * Insert the GUI element and remove the button that requests the GUI be
     * shown.
     */
    appendChildNodes(aclTable, newAclRow);
    removeElement(buttonRow);
}

/*
 * Callback for clicking on the acl request checkboxes
 */
request_add_drop_acl = partial(make_request, '/toggle_acl_request',
        check_acl_request, revert_acl_request);

/*
 * Callback for clicking on the groupacl allow checkboxes
 */
request_approve_deny_groupacl = partial(make_request, '/toggle_groupacl_status',
        check_groupacl_request, revert_groupacl_request);

/*
 * Callback for selecting a new acl status from an option list.
 *
 * This can't use the generic make_request as we have to pass special
 * more information in the request.
 */
function request_status_change(event) {
    logDebug('in request_status_change');
    var requestContainer = getFirstParentByTagAndClassName(event.target(),
            'div', 'requestContainer');
    busy(requestContainer);
    var form = getFirstParentByTagAndClassName(requestContainer, 'form');
    var base = form.action;
    if (base[base.length-1] == '/') {
        base = base.slice(0,-1);
    }

    /* Retrieve person to make the change for. */
    var aclRow = getFirstParentByTagAndClassName(requestContainer, 'tr',
            'aclrow');
    var aclUser = getElementsByTagAndClassName('td', 'acluser', aclRow)[0];
    logDebug(aclUser);
    logDebug(aclUser.getAttribute('name'))
    var personid = aclUser.getAttribute('name').split(':')[1];

    /* Retrieve the status to change to for this acl */
    var selectElement = getElementsByTagAndClassName('select', 'aclStatusList',
            requestContainer)[0];
    var aclStatus = selectElement.value;

    /* Retrieve pkgid and aclName */
    var idParts = requestContainer.getAttribute('name').split(':');

    var req = loadJSONDoc(base + '/set_acl_status', {'pkgid': idParts[0],
            'personid': personid, 'new_acl': idParts[1],
            'statusname': aclStatus});
    req.addCallback(partial(check_acl_status, requestContainer));
    req.addErrback(partial(revert_acl_status, requestContainer));
    req.addErrback(partial(display_error, requestContainer));
    req.addBoth(unbusy, requestContainer);
    logDebug(base+'/set_acl_status'+'?'+queryString({'pkgid':idParts[0], 'personid':personid,'new_acl':idParts[1],'statusname':aclStatus}));
}

/*
 * Initialize the web page.
 *
 * This mostly involves setting event handlers to be called when the user
 * clicks on something.
 */
jQuery(document).ready(function() {
    logDebug('In Init');
    /* Restore $() to whatever other library wants it */
    jQuery.noConflict();

    /* Global commits hash.  When a change from the user is anticipated, add
     * relevant information to this hash.  After the change is committed or
     * cancelled, remove it.
     */
    commits = {};

    //jQuery('input').class('ownerButton')
    var ownerButtons = getElementsByTagAndClassName('input', 'ownerButton');
    for (var buttonNum in ownerButtons) {
        var request_owner_change = partial(make_request, '/toggle_owner',
                toggle_owner, null);
        connect(ownerButtons[buttonNum], 'onclick', request_owner_change);
    }

    var statusBoxes = getElementsByTagAndClassName('select', 'aclStatusList');
    for (var statusNum in statusBoxes) {
        connect(statusBoxes[statusNum], 'onchange', request_status_change);
        connect(statusBoxes[statusNum], 'onfocus', save_status);
    }

    var shouldOpenBox = getElementsByTagAndClassName('input',
            'shouldOpenBox')[0];
    if (shouldOpenBox) {
        connect(shouldOpenBox, 'onchange', partial(make_request,
                    '/toggle_shouldopen', toggle_shouldopen,
                    toggle_shouldopen_failure));
    }

    var aclReqBoxes = getElementsByTagAndClassName('input', 'aclPresentBox');
    for (var aclReqNum in aclReqBoxes) {
        connect(aclReqBoxes[aclReqNum], 'onclick', request_add_drop_acl);
    }

    var groupAclReqBoxes = getElementsByTagAndClassName('input',
            'groupAclStatusBox');
    for (var groupAclReqNum in groupAclReqBoxes) {
        connect(groupAclReqBoxes[groupAclReqNum], 'onclick', request_approve_deny_groupacl);
    }

    /* This one's unique in that it doesn't have to talk to the server */
    var addMyselfButtons = getElementsByTagAndClassName('input', 'addMyselfButton');
    for (var addButtonNum in addMyselfButtons) {
        connect(addMyselfButtons[addButtonNum], 'onclick', request_acl_gui);
    }
});
