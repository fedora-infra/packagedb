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
