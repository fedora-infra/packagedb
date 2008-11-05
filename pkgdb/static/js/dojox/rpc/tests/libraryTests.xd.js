dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.rpc.tests.libraryTests"],
["require", "dojox.rpc.tests.Yahoo"],
["require", "dojox.rpc.tests.Geonames"],
["require", "dojox.rpc.tests.Wikipedia"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.rpc.tests.libraryTests"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.rpc.tests.libraryTests"] = true;
dojo.provide("dojox.rpc.tests.libraryTests");

try{
	dojo.require("dojox.rpc.tests.Yahoo");
	dojo.require("dojox.rpc.tests.Geonames");
	dojo.require("dojox.rpc.tests.Wikipedia");
}catch(e){
	doh.debug(e);
}


}

}};});