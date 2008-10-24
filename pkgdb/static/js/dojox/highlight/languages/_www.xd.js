/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.highlight.languages._www"],
["require", "dojox.highlight.languages.xml"],
["require", "dojox.highlight.languages.html"],
["require", "dojox.highlight.languages.css"],
["require", "dojox.highlight.languages.django"],
["require", "dojox.highlight.languages.javascript"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.highlight.languages._www"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.highlight.languages._www"] = true;
dojo.provide("dojox.highlight.languages._www");

/* common web-centric languages */
dojo.require("dojox.highlight.languages.xml");
dojo.require("dojox.highlight.languages.html");
dojo.require("dojox.highlight.languages.css");
dojo.require("dojox.highlight.languages.django");
dojo.require("dojox.highlight.languages.javascript");

}

}};});
