dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.json.tests.module"],
["require", "dojox.json.tests.ref"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.json.tests.module"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.json.tests.module"] = true;
dojo.provide("dojox.json.tests.module");

try{
	dojo.require("dojox.json.tests.ref");
}catch(e){
	doh.debug(e);
}


}

}};});