/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.form.DropDownStack"],
["require", "dojox.form.DropDownSelect"],
["require", "dojox.form._SelectStackMixin"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.form.DropDownStack"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.form.DropDownStack"] = true;
dojo.provide("dojox.form.DropDownStack");

dojo.require("dojox.form.DropDownSelect");
dojo.require("dojox.form._SelectStackMixin");

dojo.declare("dojox.form.DropDownStack",
	[ dojox.form.DropDownSelect, dojox.form._SelectStackMixin ], {
	// summary: A dropdown-based select stack.
	
});

}

}};});
