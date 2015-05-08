import DS from "ember-data";


export default DS.Model.extend({
    name: DS.attr('string'),
    deviceID: DS.attr('string'),
    certName: DS.attr('string'),
    compression: DS.attr('string'),
    introducer: DS.attr('boolean'),
    addresses: DS.attr(),
    selectId: function() {
      return this.get('deviceID');
    }.property('deviceID'),
    selectText: function() {
      return this.get('name');
    }.property('name')
});
