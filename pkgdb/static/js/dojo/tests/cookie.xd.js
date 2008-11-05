dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "tests.cookie"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["tests.cookie"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["tests.cookie"] = true;
dojo.provide("tests.cookie");
if(dojo.isBrowser){
	doh.registerUrl("tests.cookie", dojo.moduleUrl("tests", "cookie.html"));
}

}

}};});