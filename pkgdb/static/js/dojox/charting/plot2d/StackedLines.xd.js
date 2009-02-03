/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.charting.plot2d.StackedLines"],
["require", "dojox.charting.plot2d.Stacked"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.charting.plot2d.StackedLines"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.charting.plot2d.StackedLines"] = true;
dojo.provide("dojox.charting.plot2d.StackedLines");

dojo.require("dojox.charting.plot2d.Stacked");

dojo.declare("dojox.charting.plot2d.StackedLines", dojox.charting.plot2d.Stacked, {
	constructor: function(){
		this.opt.lines = true;
	}
});

}

}};});
