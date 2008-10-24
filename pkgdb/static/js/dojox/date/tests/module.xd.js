dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.date.tests.module"],
["require", "dojox.date.tests.HebrewDate"],
["require", "dojox.date.tests.IslamicDate"],
["require", "dojox.date.tests.posix"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.date.tests.module"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.date.tests.module"] = true;
dojo.provide("dojox.date.tests.module");

try{
	dojo.require("dojox.date.tests.HebrewDate");
	dojo.require("dojox.date.tests.IslamicDate");
	dojo.require("dojox.date.tests.posix");
}catch(e){
	doh.debug(e);
}


}

}};});