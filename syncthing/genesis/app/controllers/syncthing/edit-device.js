import Ember from "ember";


export default Ember.ObjectController.extend({
  actions: {
    save: function() {
      var self = this,
          device = this.get("model");
      var promise = device.save();
    },
    removeModal: function() {
      if (this.get('model').get('isDirty')) {
        this.get('model').rollback();
      };
      return true;
    }
  }
});
