dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.color.tests.color"],
["require", "dojox.color"],
["require", "dojox.color.tests._base"],
["require", "dojox.color.tests.Palette"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.color.tests.color"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.color.tests.color"] = true;
dojo.provide("dojox.color.tests.color");
dojo.require("dojox.color");

try{
	dojo.require("dojox.color.tests._base");
//	dojo.require("dojox.color.tests.Colorspace");
	dojo.require("dojox.color.tests.Palette");
//	dojo.require("dojox.color.tests.Generator");
}catch(e){
	doh.debug(e);
}

}

}};});