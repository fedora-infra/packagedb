/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dijit.robot"],
["require", "dojo.robot"],
["require", "dijit._base.scroll"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dijit.robot"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dijit.robot"] = true;
dojo.provide("dijit.robot");
dojo.require("dojo.robot");
dojo.require("dijit._base.scroll");

dojo.mixin(doh.robot,{

	// users who use doh+dojo+dijit get the added convenience of scrollIntoView
	// automatically firing when they try to move the mouse to an element

	// TODO: remove post 1.2 when scrollIntoView moves into Dojo core
	_scrollIntoView : function(/*String||DOMNode||Function*/ node){
		// summary:
		//		Scroll the passed node into view, if it is not.
		//
		if(typeof node == "function"){
			// if the user passed a function returning a node, evaluate it
			node = node();
		}
		dijit.scrollIntoView(node);
	}
});

}

}};});
