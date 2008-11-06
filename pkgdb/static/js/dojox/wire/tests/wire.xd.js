dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.wire.tests.wire"],
["require", "dojox.wire.tests.programmatic._base"],
["require", "dojox.wire.tests.programmatic.Wire"],
["requireIf", dojo.isBrowser, "dojox.wire.tests.programmatic.DataWire"],
["requireIf", dojo.isBrowser, "dojox.wire.tests.programmatic.XmlWire"],
["require", "dojox.wire.tests.programmatic.CompositeWire"],
["require", "dojox.wire.tests.programmatic.TableAdapter"],
["require", "dojox.wire.tests.programmatic.TreeAdapter"],
["require", "dojox.wire.tests.programmatic.TextAdapter"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.wire.tests.wire"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.wire.tests.wire"] = true;
dojo.provide("dojox.wire.tests.wire");

try{
	dojo.require("dojox.wire.tests.programmatic._base");
	dojo.require("dojox.wire.tests.programmatic.Wire");
	dojo.requireIf(dojo.isBrowser, "dojox.wire.tests.programmatic.DataWire");
	dojo.requireIf(dojo.isBrowser, "dojox.wire.tests.programmatic.XmlWire");
	dojo.require("dojox.wire.tests.programmatic.CompositeWire");
	dojo.require("dojox.wire.tests.programmatic.TableAdapter");
	dojo.require("dojox.wire.tests.programmatic.TreeAdapter");
	dojo.require("dojox.wire.tests.programmatic.TextAdapter");
}catch(e){
	doh.debug(e);
}

}

}};});