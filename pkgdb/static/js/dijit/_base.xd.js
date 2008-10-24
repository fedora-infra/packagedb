/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dijit._base"],
["require", "dijit._base.focus"],
["require", "dijit._base.manager"],
["require", "dijit._base.place"],
["require", "dijit._base.popup"],
["require", "dijit._base.scroll"],
["require", "dijit._base.sniff"],
["require", "dijit._base.typematic"],
["require", "dijit._base.wai"],
["require", "dijit._base.window"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dijit._base"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dijit._base"] = true;
dojo.provide("dijit._base");

dojo.require("dijit._base.focus");
dojo.require("dijit._base.manager");
dojo.require("dijit._base.place");
dojo.require("dijit._base.popup");
dojo.require("dijit._base.scroll");
dojo.require("dijit._base.sniff");
dojo.require("dijit._base.typematic");
dojo.require("dijit._base.wai");
dojo.require("dijit._base.window");

}

}};});
