dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.highlight.tests.module"],
["require", "dojox.highlight.tests.highlight"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.highlight.tests.module"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.highlight.tests.module"] = true;
dojo.provide("dojox.highlight.tests.module");
//This file loads in all the test definitions.  

try{
	//Load in the highlight module test.
	dojo.require("dojox.highlight.tests.highlight");
}catch(e){
	doh.debug(e);
}

}

}};});