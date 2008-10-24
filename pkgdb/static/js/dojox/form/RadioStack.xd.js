/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.form.RadioStack"],
["require", "dojox.form.CheckedMultiSelect"],
["require", "dojox.form._SelectStackMixin"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.form.RadioStack"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.form.RadioStack"] = true;
dojo.provide("dojox.form.RadioStack");

dojo.require("dojox.form.CheckedMultiSelect");
dojo.require("dojox.form._SelectStackMixin");

dojo.declare("dojox.form.RadioStack",
	[ dojox.form.CheckedMultiSelect, dojox.form._SelectStackMixin ], {
	// summary: A radio-based select stack.
});

}

}};});
