dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.jsonPath.tests.module"],
["require", "dojox.jsonPath.tests.jsonPath"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.jsonPath.tests.module"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.jsonPath.tests.module"] = true;
dojo.provide("dojox.jsonPath.tests.module");

try{
	dojo.require("dojox.jsonPath.tests.jsonPath");
}catch(e){
	doh.debug(e);
}


}

}};});