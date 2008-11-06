dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "tests.data"],
["require", "tests.data.utils"],
["require", "tests.data.ItemFileReadStore"],
["require", "tests.data.ItemFileWriteStore"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["tests.data"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["tests.data"] = true;
dojo.provide("tests.data");
//Squelch any json comment messages for now, since the UT allows for both.
dojo.config.usePlainJson = true;
dojo.require("tests.data.utils");
dojo.require("tests.data.ItemFileReadStore");
dojo.require("tests.data.ItemFileWriteStore");



}

}};});