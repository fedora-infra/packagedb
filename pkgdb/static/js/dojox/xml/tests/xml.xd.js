dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.xml.tests.xml"],
["require", "dojox.xml.tests.parser"],
["require", "dojox.xml.tests.widgetParser"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.xml.tests.xml"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.xml.tests.xml"] = true;
dojo.provide("dojox.xml.tests.xml");

try{
	dojo.require("dojox.xml.tests.parser");
	dojo.require("dojox.xml.tests.widgetParser");
}catch(e){
	doh.debug(e);
}

}

}};});