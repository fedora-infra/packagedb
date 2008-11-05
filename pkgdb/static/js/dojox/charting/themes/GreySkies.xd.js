/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.charting.themes.GreySkies"],
["require", "dojox.charting.Theme"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.charting.themes.GreySkies"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.charting.themes.GreySkies"] = true;
dojo.provide("dojox.charting.themes.GreySkies");
dojo.require("dojox.charting.Theme");

(function(){
	var dxc=dojox.charting;
	dxc.themes.GreySkies=new dxc.Theme(dxc.Theme._def);
})();

}

}};});
