/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["require", "dojox.gfx"],
["requireIf", dojox.gfx.renderer == "svg", "dojox.gfx.svg_attach"],
["requireIf", dojox.gfx.renderer == "vml", "dojox.gfx.vml_attach"],
["requireIf", dojox.gfx.renderer == "silverlight", "dojox.gfx.silverlight_attach"],
["requireIf", dojox.gfx.renderer == "canvas", "dojox.gfx.canvas_attach"]],
defineResource: function(dojo, dijit, dojox){dojo.require("dojox.gfx");

// include an attacher conditionally
dojo.requireIf(dojox.gfx.renderer == "svg", "dojox.gfx.svg_attach");
dojo.requireIf(dojox.gfx.renderer == "vml", "dojox.gfx.vml_attach");
dojo.requireIf(dojox.gfx.renderer == "silverlight", "dojox.gfx.silverlight_attach");
dojo.requireIf(dojox.gfx.renderer == "canvas", "dojox.gfx.canvas_attach");

}};});
