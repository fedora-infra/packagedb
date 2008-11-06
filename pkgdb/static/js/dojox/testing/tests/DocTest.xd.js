dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.testing.tests.DocTest"],
["require", "dojox.testing.DocTest"],
["require", "dojo.string"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.testing.tests.DocTest"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.testing.tests.DocTest"] = true;
dojo.provide("dojox.testing.tests.DocTest");

dojo.require("dojox.testing.DocTest");
dojo.require("dojo.string");

tests.registerDocTests("dojox.testing.DocTest");

}

}};});