/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.grid.VirtualGrid"],
["require", "dojox.grid.compat.VirtualGrid"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.grid.VirtualGrid"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.grid.VirtualGrid"] = true;
dojo.provide("dojox.grid.VirtualGrid");
dojo.require("dojox.grid.compat.VirtualGrid");
dojo.deprecated("dojox.grid.VirtualGrid");

}

}};});
