dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.encoding.tests.digests._base"],
["require", "dojox.encoding.digests._base"],
["require", "dojox.encoding.tests.digests.MD5"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.encoding.tests.digests._base"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.encoding.tests.digests._base"] = true;
dojo.provide("dojox.encoding.tests.digests._base");
dojo.require("dojox.encoding.digests._base");

try{
	dojo.require("dojox.encoding.tests.digests.MD5");
}catch(e){
	doh.debug(e);
}

}

}};});