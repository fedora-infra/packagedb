/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.analytics"],
["require", "dojox.analytics._base"],
["require", "dojo._base.connect"],
["require", "dojo._base.Deferred"],
["require", "dojo._base.json"],
["require", "dojo._base.array"],
["requireIf", dojo.isBrowser, "dojo._base.window"],
["requireIf", dojo.isBrowser, "dojo._base.event"],
["requireIf", dojo.isBrowser, "dojo._base.html"],
["requireIf", dojo.isBrowser, "dojo._base.NodeList"],
["requireIf", dojo.isBrowser, "dojo._base.query"],
["requireIf", dojo.isBrowser, "dojo._base.xhr"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.analytics"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.analytics"] = true;
dojo.provide("dojox.analytics");
dojo.require("dojox.analytics._base");
dojo.require("dojo._base.connect");
dojo.require("dojo._base.Deferred");
dojo.require("dojo._base.json");
dojo.require("dojo._base.array");
dojo.requireIf(dojo.isBrowser, "dojo._base.window");
dojo.requireIf(dojo.isBrowser, "dojo._base.event");
dojo.requireIf(dojo.isBrowser, "dojo._base.html");
dojo.requireIf(dojo.isBrowser, "dojo._base.NodeList");
dojo.requireIf(dojo.isBrowser, "dojo._base.query");
dojo.requireIf(dojo.isBrowser, "dojo._base.xhr");

}

}};});
