/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.charting.plot2d.Markers"],
["require", "dojox.charting.plot2d.Default"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.charting.plot2d.Markers"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.charting.plot2d.Markers"] = true;
dojo.provide("dojox.charting.plot2d.Markers");

dojo.require("dojox.charting.plot2d.Default");

dojo.declare("dojox.charting.plot2d.Markers", dojox.charting.plot2d.Default, {
	constructor: function(){
		this.opt.markers = true;
	}
});

}

}};});