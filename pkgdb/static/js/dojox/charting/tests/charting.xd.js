dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.charting.tests.charting"],
["require", "dojox.charting.tests.Theme"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.charting.tests.charting"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.charting.tests.charting"] = true;
dojo.provide("dojox.charting.tests.charting");

try{
	dojo.require("dojox.charting.tests.Theme");
}catch(e){
	doh.debug(e);
}

}

}};});