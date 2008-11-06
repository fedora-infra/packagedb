/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.cometd.longPollTransport"],
["require", "dojox.cometd.longPollTransportJsonEncoded"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.cometd.longPollTransport"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.cometd.longPollTransport"] = true;
dojo.provide("dojox.cometd.longPollTransport");
dojo.require("dojox.cometd.longPollTransportJsonEncoded");

}

}};});
