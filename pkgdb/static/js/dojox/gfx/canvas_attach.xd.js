/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["require", "dojox.gfx.canvas"]],
defineResource: function(dojo, dijit, dojox){dojo.require("dojox.gfx.canvas");

dojo.experimental("dojox.gfx.canvas_attach");

// not implemented
dojox.gfx.attachNode = function(){
	return null;	// for now
};

}};});
