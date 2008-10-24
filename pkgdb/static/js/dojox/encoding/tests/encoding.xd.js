dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.encoding.tests.encoding"],
["require", "dojox.encoding.tests.ascii85"],
["require", "dojox.encoding.tests.easy64"],
["require", "dojox.encoding.tests.bits"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.encoding.tests.encoding"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.encoding.tests.encoding"] = true;
dojo.provide("dojox.encoding.tests.encoding");

try{
	dojo.require("dojox.encoding.tests.ascii85");
	dojo.require("dojox.encoding.tests.easy64");
	dojo.require("dojox.encoding.tests.bits");
}catch(e){
	doh.debug(e);
}

}

}};});