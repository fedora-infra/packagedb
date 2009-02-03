/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.highlight.languages._all"],
["require", "dojox.highlight.languages._static"],
["require", "dojox.highlight.languages._dynamic"],
["require", "dojox.highlight.languages._www"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.highlight.languages._all"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.highlight.languages._all"] = true;
dojo.provide("dojox.highlight.languages._all");

/* groups of similar languages */
dojo.require("dojox.highlight.languages._static");
dojo.require("dojox.highlight.languages._dynamic");
dojo.require("dojox.highlight.languages._www");


}

}};});
