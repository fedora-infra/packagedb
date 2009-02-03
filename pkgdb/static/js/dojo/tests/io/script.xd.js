dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "tests.io.script"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["tests.io.script"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["tests.io.script"] = true;
dojo.provide("tests.io.script");
if(dojo.isBrowser){
	doh.registerUrl("tests.io.script", dojo.moduleUrl("tests.io", "script.html"));
}

}

}};});