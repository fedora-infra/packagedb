dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.lang.tests.array"],
["require", "dojox.math"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.lang.tests.array"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.lang.tests.array"] = true;
dojo.provide("dojox.lang.tests.array");

dojo.require("dojox.math");

(function(){
	tests.register("dojox.math.tests.factorial", [
		function fact0(t){ t.assertEqual(1, dojox.math.factorial(0)); },
		function fact5(t){ t.assertEqual(120, dojox.math.factorial(5)); },
		function factneg(t){ t.assertTrue(isNaN(dojox.math.factorial(-1))); }
	]);
})();

}

}};});