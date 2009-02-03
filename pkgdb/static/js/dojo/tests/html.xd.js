dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "tests.html"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["tests.html"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["tests.html"] = true;
dojo.provide("tests.html");
if(dojo.isBrowser){
	doh.registerUrl("tests.html", dojo.moduleUrl("tests", "html/test_set.html"));
}

}

}};});