dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.validate.tests.module"],
["require", "dojox.validate.tests.creditcard"],
["require", "dojox.validate.tests.validate"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.validate.tests.module"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.validate.tests.module"] = true;
dojo.provide("dojox.validate.tests.module");

try{
	dojo.require("dojox.validate.tests.creditcard");
	dojo.require("dojox.validate.tests.validate"); 

}catch(e){
	doh.debug(e);
	console.debug(e); 
}

}

}};});