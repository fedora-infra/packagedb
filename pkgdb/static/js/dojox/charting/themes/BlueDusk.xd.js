/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.charting.themes.BlueDusk"],
["require", "dojox.charting.Theme"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.charting.themes.BlueDusk"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.charting.themes.BlueDusk"] = true;
dojo.provide("dojox.charting.themes.BlueDusk");
dojo.require("dojox.charting.Theme");

(function(){
	var dxc=dojox.charting;
	dxc.themes.BlueDusk=new dxc.Theme({
		colors: [
			"#292e76",
			"#3e56a6",
			"#10143f",
			"#33449c",
			"#798dcd"
		]
	});
})();

}

}};});
