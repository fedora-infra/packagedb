/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.storage._common"],
["require", "dojox.storage.Provider"],
["require", "dojox.storage.manager"],
["require", "dojox.storage.GearsStorageProvider"],
["require", "dojox.storage.WhatWGStorageProvider"],
["require", "dojox.storage.FlashStorageProvider"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.storage._common"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.storage._common"] = true;
dojo.provide("dojox.storage._common");
dojo.require("dojox.storage.Provider");
dojo.require("dojox.storage.manager");

/*
  Note: if you are doing Dojo Offline builds you _must_
  have offlineProfile=true when you run the build script:
  ./build.sh action=release profile=offline offlineProfile=true
*/
dojo.require("dojox.storage.GearsStorageProvider");
dojo.require("dojox.storage.WhatWGStorageProvider");
dojo.require("dojox.storage.FlashStorageProvider");

// now that we are loaded and registered tell the storage manager to
// initialize itself
dojox.storage.manager.initialize();

}

}};});