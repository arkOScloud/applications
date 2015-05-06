import Ember from "ember";


export default Ember.ObjectController.extend({
  newDevice: {},
  actions: {
    save: function() {
      var self = this;
      var device = self.store.createRecord('device', {
        id: this.get('newDevice.id'),
        name: this.get('newDevice.id'),
        deviceID: this.get('newDevice.deviceID'),
        addressing: this.get('newDevice.addressing')
      });
      var promise = device.save();
      promise.then(function(){}, function(){
        device.deleteRecord();
      });
    }
  }
});
