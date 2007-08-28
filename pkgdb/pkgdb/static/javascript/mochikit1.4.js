/* 
 * From MochiKit 1.4
 *
 * (c) 2005 Bob Ippolito.  All rights Reserved.
 * License: MIT or Academic Free License v 2.1
 * See <http://mochikit.com/> for documentation, downloads, license, etc.
 *
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


