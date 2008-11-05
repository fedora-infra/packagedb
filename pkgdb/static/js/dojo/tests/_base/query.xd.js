dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "tests._base.query"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["tests._base.query"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["tests._base.query"] = true;
dojo.provide("tests._base.query");
if(dojo.isBrowser){
	doh.registerUrl("tests._base.query", dojo.moduleUrl("tests", "_base/query.html"));
	doh.registerUrl("tests._base.NodeList", dojo.moduleUrl("tests", "_base/NodeList.html"));
}

}

}};});