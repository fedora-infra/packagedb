dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.string.tests.string"],
["require", "dojox.string.tests.Builder"],
["require", "dojox.string.tests.sprintf"],
["require", "dojox.string.tests.BidiComplex"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.string.tests.string"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.string.tests.string"] = true;
dojo.provide("dojox.string.tests.string");

try{
	dojo.require("dojox.string.tests.Builder");
	dojo.require("dojox.string.tests.sprintf");
	dojo.require("dojox.string.tests.BidiComplex");
} catch(e){ }

}

}};});