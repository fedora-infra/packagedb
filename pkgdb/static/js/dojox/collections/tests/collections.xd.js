dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.collections.tests.collections"],
["require", "dojox.collections"],
["require", "dojox.collections.tests._base"],
["require", "dojox.collections.tests.ArrayList"],
["require", "dojox.collections.tests.BinaryTree"],
["require", "dojox.collections.tests.Dictionary"],
["require", "dojox.collections.tests.Queue"],
["require", "dojox.collections.tests.Set"],
["require", "dojox.collections.tests.SortedList"],
["require", "dojox.collections.tests.Stack"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.collections.tests.collections"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.collections.tests.collections"] = true;
dojo.provide("dojox.collections.tests.collections");
dojo.require("dojox.collections");

try{
	dojo.require("dojox.collections.tests._base");
	dojo.require("dojox.collections.tests.ArrayList");
	dojo.require("dojox.collections.tests.BinaryTree");
	dojo.require("dojox.collections.tests.Dictionary");
	dojo.require("dojox.collections.tests.Queue");
	dojo.require("dojox.collections.tests.Set");
	dojo.require("dojox.collections.tests.SortedList");
	dojo.require("dojox.collections.tests.Stack");
}catch(e){
	doh.debug(e);
}

}

}};});