dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "tests.data.ItemFileReadStore"],
["require", "tests.data.readOnlyItemFileTestTemplates"],
["require", "dojo.data.ItemFileReadStore"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["tests.data.ItemFileReadStore"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["tests.data.ItemFileReadStore"] = true;
dojo.provide("tests.data.ItemFileReadStore");
dojo.require("tests.data.readOnlyItemFileTestTemplates");
dojo.require("dojo.data.ItemFileReadStore");

tests.data.readOnlyItemFileTestTemplates.registerTestsForDatastore("dojo.data.ItemFileReadStore");


}

}};});