# A JSON-based API(view) for your app.
# Most rules would look like:
# @jsonify.when("isinstance(obj, YourClass)")
# def jsonify_yourclass(obj):
#     return [obj.val1, obj.val2]
# @jsonify can convert your objects to following types:
# lists, dicts, numbers and strings

import sqlalchemy
from turbojson.jsonify import jsonify

@jsonify.when("isinstance(obj, sqlalchemy.ext.selectresults.SelectResults)")
def jsonify_sa_select_results(obj):
    return list(obj)

@jsonify.when("isinstance(obj, sqlalchemy.orm.attributes.InstrumentedList)")
def jsonify_salist(obj):
    return map(jsonify, obj)

