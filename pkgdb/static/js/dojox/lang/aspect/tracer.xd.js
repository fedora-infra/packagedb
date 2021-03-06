/*
	Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
	Available via Academic Free License >= 2.1 OR the modified BSD license.
	see: http://dojotoolkit.org/license for details
*/


dojo._xdResourceLoaded(function(dojo, dijit, dojox){
return {depends: [["provide", "dojox.lang.aspect.tracer"]],
defineResource: function(dojo, dijit, dojox){if(!dojo._hasResource["dojox.lang.aspect.tracer"]){ //_hasResource checks added by build. Do not use _hasResource directly in your code.
dojo._hasResource["dojox.lang.aspect.tracer"] = true;
dojo.provide("dojox.lang.aspect.tracer");

(function(){
	var aop = dojox.lang.aspect;
	
	var Tracer = function(/*Boolean*/ grouping){
		this.method   = grouping ? "group" : "log";
		if(grouping){
			this.after = this._after;
		}
	};
	dojo.extend(Tracer, {
		before: function(/*arguments*/){
			var context = aop.getContext(), joinPoint = context.joinPoint,
				args = Array.prototype.join.call(arguments, ", ");
			console[this.method](context.instance, "=>", joinPoint.targetName + "(" + args + ")");
		},
		afterReturning: function(retVal){
			var joinPoint = aop.getContext().joinPoint;
			if(typeof retVal != "undefined"){
				
			}else{
				
			}
		},
		afterThrowing: function(excp){
			
		},
		_after: function(excp){
			
		}
	});
	
	aop.tracer = function(/*Boolean*/ grouping){
		// summary:
		//		Returns an object, which can be used to trace calls with Firebug's console.
		//		Prints argument, a return value, or an exception.
		//
		// grouping:
		//		The flag to group output. If true, indents embedded console messages.
	
		return new Tracer(grouping);	// Object
	};
})();

}

}};});
