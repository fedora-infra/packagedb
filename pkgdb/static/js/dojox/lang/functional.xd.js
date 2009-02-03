/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.lang.functional"],
["require", "dojox.lang.functional.lambda"],
["require", "dojox.lang.functional.array"],
["require", "dojox.lang.functional.object"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.lang.functional"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.lang.functional"] = true;
dojo.provide("dojox.lang.functional");

dojo.require("dojox.lang.functional.lambda");
dojo.require("dojox.lang.functional.array");
dojo.require("dojox.lang.functional.object");

}

}};});
