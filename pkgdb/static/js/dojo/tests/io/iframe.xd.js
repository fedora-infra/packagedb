dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "tests.io.iframe"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["tests.io.iframe"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["tests.io.iframe"] = true;
dojo.provide("tests.io.iframe");
if(dojo.isBrowser){
	doh.registerUrl("tests.io.iframe", dojo.moduleUrl("tests.io", "iframe.html"));
}

}

}};});