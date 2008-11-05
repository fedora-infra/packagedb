dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "tests._base._loader.hostenv_spidermonkey"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["tests._base._loader.hostenv_spidermonkey"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["tests._base._loader.hostenv_spidermonkey"] = true;
dojo.provide("tests._base._loader.hostenv_spidermonkey");

tests.register("tests._base._loader.hostenv_spidermonkey", 
	[
		function getText(t){
			var filePath = dojo.moduleUrl("tests._base._loader", "getText.txt");
			var text = readText(filePath);
			t.assertEqual("dojo._getText() test data", text);
		}
	]
);

}

}};});