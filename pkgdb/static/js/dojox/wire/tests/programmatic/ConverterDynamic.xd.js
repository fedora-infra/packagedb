dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.wire.tests.programmatic.ConverterDynamic"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.wire.tests.programmatic.ConverterDynamic"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.wire.tests.programmatic.ConverterDynamic"] = true;
dojo.provide("dojox.wire.tests.programmatic.ConverterDynamic");

dojo.declare("dojox.wire.tests.programmatic.ConverterDynamic", null, {
	convert: function(v){
		return v + 1;
	}
});


}

}};});