/*
 * Show a tooltip explaining the column.
 */
function show_definition(event) {
    var tooltip = new ToolTip(messages[event.target().id],
            event.mouse().client.x, event.mouse().client.y);
    connect(event.target(), 'onmouseout', tooltip.hide);
    tooltip.show();
}

/*
 * Setup event handlers for the collectionoverview page.
 */
function init(event) {
    /* Global tooltip messages */
    messages = {'collectionhead': 'A distribution of Linux Packages Created and Hosted by the Fedora Project', 
        'versionhead': 'The version of the distribution',
        'packagehead':'Number of packages in the cvs repository for this collection version.  The packages are not necessarily built for this distribution'}

    var columns = getElementsByTagAndClassName('th', 'ColumnHead');
    for (var colNum in columns) {
        connect(columns[colNum], 'onmouseover', show_definition);
    }
}
connect(window, 'onload', init); 
