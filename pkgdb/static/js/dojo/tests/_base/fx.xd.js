dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "tests._base.fx"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["tests._base.fx"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["tests._base.fx"] = true;
dojo.provide("tests._base.fx");
if(dojo.isBrowser){
	doh.registerUrl("tests._base.fx", dojo.moduleUrl("tests", "_base/fx.html"), 15000);
}

}

}};});