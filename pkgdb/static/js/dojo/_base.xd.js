/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojo._base"],
["require", "dojo._base.lang"],
["require", "dojo._base.declare"],
["require", "dojo._base.connect"],
["require", "dojo._base.Deferred"],
["require", "dojo._base.json"],
["require", "dojo._base.array"],
["require", "dojo._base.Color"],
["requireIf", dojo.isBrowser, "dojo._base.browser"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojo._base"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojo._base"] = true;
dojo.provide("dojo._base");
dojo.require("dojo._base.lang");
dojo.require("dojo._base.declare");
dojo.require("dojo._base.connect");
dojo.require("dojo._base.Deferred");
dojo.require("dojo._base.json");
dojo.require("dojo._base.array");
dojo.require("dojo._base.Color");
dojo.requireIf(dojo.isBrowser, "dojo._base.browser");

}

}};});
