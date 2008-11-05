dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.rpc.tests.module"],
["require", "dojox.rpc.tests.Service"],
["require", "dojox.rpc.tests.JsonReferencing"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.rpc.tests.module"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.rpc.tests.module"] = true;
dojo.provide("dojox.rpc.tests.module");

try{
	dojo.require("dojox.rpc.tests.Service");
	dojo.require("dojox.rpc.tests.JsonReferencing");
}catch(e){
	doh.debug(e);
}


}

}};});