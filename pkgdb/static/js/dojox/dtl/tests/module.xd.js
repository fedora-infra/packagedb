dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.dtl.tests.module"],
["require", "dojox.dtl.tests.text.filter"],
["require", "dojox.dtl.tests.text.tag"],
["require", "dojox.dtl.tests.html.tag"],
["require", "dojox.dtl.tests.html.buffer"],
["require", "dojox.dtl.tests.context"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.dtl.tests.module"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.dtl.tests.module"] = true;
dojo.provide("dojox.dtl.tests.module");

try{
	dojo.require("dojox.dtl.tests.text.filter");
	dojo.require("dojox.dtl.tests.text.tag");
	dojo.require("dojox.dtl.tests.html.tag");
	dojo.require("dojox.dtl.tests.html.buffer");
	dojo.require("dojox.dtl.tests.context");
}catch(e){
	doh.debug(e);
}

}

}};});