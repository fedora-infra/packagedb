dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.math.tests.main"],
["require", "dojox.math.tests.math"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.math.tests.main"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.math.tests.main"] = true;
dojo.provide("dojox.math.tests.main");

try{
	// functional block
	dojo.require("dojox.math.tests.math");
}catch(e){
	doh.debug(e);
}

}

}};});