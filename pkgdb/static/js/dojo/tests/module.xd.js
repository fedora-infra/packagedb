dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojo.tests.module"],
["require", "tests._base"],
["require", "tests.i18n"],
["requireIf", dojo.isBrowser, "tests.back-hash"],
["require", "tests.cldr"],
["require", "tests.data"],
["require", "tests.date"],
["require", "tests.number"],
["require", "tests.currency"],
["require", "tests.AdapterRegistry"],
["require", "tests.io.script"],
["require", "tests.io.iframe"],
["requireIf", dojo.isBrowser, "tests.rpc"],
["require", "tests.string"],
["require", "tests.behavior"],
["require", "tests.parser"],
["require", "tests.colors"],
["requireIf", dojo.isBrowser,"tests.cookie"],
["require", "tests.fx"],
["require", "tests.DeferredList"],
["require", "tests.html"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojo.tests.module"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojo.tests.module"] = true;
dojo.provide("dojo.tests.module");

try{
	dojo.require("tests._base");
	dojo.require("tests.i18n"); 
	dojo.requireIf(dojo.isBrowser, "tests.back-hash");
	dojo.require("tests.cldr");
	dojo.require("tests.data");
	dojo.require("tests.date");
	dojo.require("tests.number");
	dojo.require("tests.currency");
	dojo.require("tests.AdapterRegistry");
	dojo.require("tests.io.script");
	dojo.require("tests.io.iframe");
	dojo.requireIf(dojo.isBrowser, "tests.rpc");
	dojo.require("tests.string");
	dojo.require("tests.behavior");
	dojo.require("tests.parser");
	dojo.require("tests.colors");
	dojo.requireIf(dojo.isBrowser,"tests.cookie");
	dojo.require("tests.fx");
	dojo.require("tests.DeferredList");
	dojo.require("tests.html");
}catch(e){
	doh.debug(e);
}

}

}};});