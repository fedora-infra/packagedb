dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.encoding.tests.compression._base"],
["require", "dojox.encoding.tests.compression.splay"],
["require", "dojox.encoding.tests.compression.lzw"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.encoding.tests.compression._base"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.encoding.tests.compression._base"] = true;
dojo.provide("dojox.encoding.tests.compression._base");

try{
	dojo.require("dojox.encoding.tests.compression.splay");
	dojo.require("dojox.encoding.tests.compression.lzw");
}catch(e){
	doh.debug(e);
}

}

}};});