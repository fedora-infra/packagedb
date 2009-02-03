dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.testing.tests.module"],
["require", "dojox.testing.tests.DocTest"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.testing.tests.module"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.testing.tests.module"] = true;
dojo.provide("dojox.testing.tests.module");

try{
	dojo.require("dojox.testing.tests.DocTest");
}catch(e){
	doh.debug(e);
}

}

}};});