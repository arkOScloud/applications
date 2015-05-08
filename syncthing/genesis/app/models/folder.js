import DS from "ember-data";


export default DS.Model.extend({
    path: DS.attr('string'),
    order: DS.attr('string'),
    hashers: DS.attr('number'),
    invalid: DS.attr('string'),
    ignorePerms: DS.attr('boolean', {defaultValue: false}),
    devices: DS.attr(),
    readOnly: DS.attr('boolean', {defaultValue: false}),
    lenientMTimes: DS.attr('boolean', {defaultValue: false}),
    rescanIntervalS: DS.attr('number'),
    copiers: DS.attr('number'),
    autoNormalize: DS.attr('boolean', {defaultValue: false}),
    versioning: DS.attr(),
    hasVersioning: function() {
      if (typeof this.get('versioning') == "boolean") {
        return this.get('versioning');
      } else {
        return this.get('versioning.type') != "";
      }
    }.property('versioning'),
    pullers: DS.attr('number')
});
