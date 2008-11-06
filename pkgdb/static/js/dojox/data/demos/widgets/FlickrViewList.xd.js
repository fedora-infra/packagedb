/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.data.demos.widgets.FlickrViewList"],
["require", "dojox.dtl._Templated"],
["require", "dijit._Widget"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.data.demos.widgets.FlickrViewList"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.data.demos.widgets.FlickrViewList"] = true;
dojo.provide("dojox.data.demos.widgets.FlickrViewList");
dojo.require("dojox.dtl._Templated");
dojo.require("dijit._Widget");

dojo.declare("dojox.data.demos.widgets.FlickrViewList", 
	[ dijit._Widget, dojox.dtl._Templated ],
	{
		store: null,
		items: null,

		templateString:"{% load dojox.dtl.contrib.data %}\n{% bind_data items to store as flickr %}\n<div dojoAttachPoint=\"list\">\n\t{% for item in flickr %}\n\t<div style=\"display: inline-block; align: top;\">\n\t\t<h5>{{ item.title }}</h5>\n\t\t<a href=\"{{ item.link }}\" style=\"border: none;\">\n\t\t\t<img src=\"{{ item.imageUrlMedium }}\">\n\t\t</a>\n\t\t<p>{{ item.author }}</p>\n\n\t\t<!--\n\t\t<img src=\"{{ item.imageUrl }}\">\n\t\t<p>{{ item.imageUrl }}</p>\n\t\t<img src=\"{{ item.imageUrlSmall }}\">\n\t\t-->\n\t</div>\n\t{% endfor %}\n</div>\n\n",
	
		fetch: function(request){
			request.onComplete = dojo.hitch(this, "onComplete");
			request.onError = dojo.hitch(this, "onError");
			return this.store.fetch(request);
		},

		onError: function(){
			
			this.items = [];
			this.render();
		},

		onComplete: function(items, request){
			this.items = items||[];
			this.render();
		}
	}
);

}

}};});
