/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.storage"],
["require", "dojox.storage._common"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.storage"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.storage"] = true;
dojo.provide("dojox.storage");
dojo.require("dojox.storage._common");

}

}};});
