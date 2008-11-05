/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.charting.themes.Adobebricks"],
["require", "dojox.charting.Theme"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.charting.themes.Adobebricks"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.charting.themes.Adobebricks"] = true;
dojo.provide("dojox.charting.themes.Adobebricks");
dojo.require("dojox.charting.Theme");

(function(){
	var dxc=dojox.charting;
	dxc.themes.Adobebricks=new dxc.Theme({
		colors: [
			"#7f2518",
			"#3e170c",
			"#cc3927",
			"#651f0e",
			"#8c271c"
		]
	});
})();

}

}};});
