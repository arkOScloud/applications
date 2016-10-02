import Ember from "ember";


export default Ember.ObjectController.extend({
  devicesSelected: [],
  devicesSelectedProp: (function(){
    this.get("devicesSelected");
  }).property("devicesSelected.@each"),
  actions: {
    addSelectedId: (function(id){
      this.get("devicesSelected").pushObject(id[0]);
    }),
    removeSelectedId: (function(id){
      this.get("devicesSelected").removeObject(id[0]);
    }),
    save: function() {
      var self = this,
          folder = this.get("model");
      folder.set("devices", this.get("devicesSelected"));
      var promise = folder.save();
    },
    removeModal: function() {
      if (this.get('model').get('isDirty')) {
        this.get('model').rollback();
      };
      this.set("devicesSelected", []);
      return true;
    }
  }
});
