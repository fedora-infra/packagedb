/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.uuid"],
["require", "dojox.uuid._base"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.uuid"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.uuid"] = true;
dojo.provide("dojox.uuid");
dojo.require("dojox.uuid._base");

}

}};});
