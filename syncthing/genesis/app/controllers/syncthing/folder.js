import Ember from "ember";


export default Ember.ObjectController.extend({
  setExtra: function(){
    if (!!this.get('extra')) this.set('extra', this.get('model.extra'));
  }.observes('model'),
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
      var self = this;
      var folder = self.store.createRecord('folder', {
        id: this.get('model.id'),
        path: this.get('model.path'),
        readOnly: this.get('model.readOnly'),
        ignorePerms: this.get('model.ignorePerms'),
        versioning: this.get('model.versioning'),
        keepVersions: this.get('model.keepVersions'),
        rescanIntervalS: this.get('model.rescanIntervalS'),
        devices: this.get('devicesSelected')
      });
      var promise = folder.save();
      promise.then(function(){}, function(){
        folder.deleteRecord();
      });
    }
  }
});
