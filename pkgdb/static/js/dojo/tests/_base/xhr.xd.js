dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "tests._base.xhr"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["tests._base.xhr"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["tests._base.xhr"] = true;
dojo.provide("tests._base.xhr");
if(dojo.isBrowser){
	doh.registerUrl("tests._base.xhr", dojo.moduleUrl("tests", "_base/xhr.html"));
}

}

}};});