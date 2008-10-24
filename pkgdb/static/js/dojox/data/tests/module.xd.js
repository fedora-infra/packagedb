dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.data.tests.module"],
["require", "dojox.data.tests.ClientFilter"],
["require", "dojox.data.tests.stores.CsvStore"],
["require", "dojox.data.tests.stores.KeyValueStore"],
["require", "dojox.data.tests.stores.AndOrReadStore"],
["require", "dojox.data.tests.stores.AndOrWriteStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.HtmlTableStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.HtmlStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.OpmlStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.XmlStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.FlickrStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.FlickrRestStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.AtomReadStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.jsonPathStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.GoogleSearchStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.GoogleFeedStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.WikipediaStore"],
["require", "dojox.data.tests.stores.QueryReadStore"],
["require", "dojox.data.tests.stores.SnapLogicStore"],
["require", "dojox.data.tests.stores.FileStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.CssRuleStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.stores.CssClassStore"],
["requireIf", dojo.isBrowser, "dojox.data.tests.dom"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.data.tests.module"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.data.tests.module"] = true;
dojo.provide("dojox.data.tests.module");

try{
	dojo.require("dojox.data.tests.ClientFilter");
	dojo.require("dojox.data.tests.stores.CsvStore");
	dojo.require("dojox.data.tests.stores.KeyValueStore");
	dojo.require("dojox.data.tests.stores.AndOrReadStore"); 
	dojo.require("dojox.data.tests.stores.AndOrWriteStore"); 
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.HtmlTableStore");
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.HtmlStore");
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.OpmlStore");
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.XmlStore");
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.FlickrStore");
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.FlickrRestStore");
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.AtomReadStore");
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.jsonPathStore");
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.GoogleSearchStore");
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.GoogleFeedStore");
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.WikipediaStore");

	//Load only if in a browser AND if the location is remote (not file.  As it needs a PHP server to work).
	if(dojo.isBrowser){
		if(window.location.protocol !== "file:"){
			dojo.require("dojox.data.tests.stores.QueryReadStore");
			dojo.require("dojox.data.tests.stores.SnapLogicStore");
			dojo.require("dojox.data.tests.stores.FileStore");
		}
	}
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.CssRuleStore");
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.stores.CssClassStore");
	dojo.requireIf(dojo.isBrowser, "dojox.data.tests.dom");
}catch(e){
	doh.debug(e);
}




}

}};});