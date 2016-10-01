import Ember from "ember";


export default Ember.ObjectController.extend({
  newFolder: {rescanIntervalS: 60},
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
        id: this.get('newFolder.id'),
        path: this.get('newFolder.path'),
        readOnly: this.get('newFolder.readOnly') || false,
        ignorePerms: this.get('newFolder.ignorePerms') || false,
        versioning: this.get('newFolder.versioning') || false,
        keepVersions: this.get('newFolder.keepVersions'),
        rescanIntervalS: this.get('newFolder.rescanIntervalS'),
        devices: this.get('devicesSelected')
      });
      var promise = folder.save();
      promise.then(function(){}, function(){
        folder.deleteRecord();
      });
    },
    removeModal: function() {
      this.set("newFolder", {rescanIntervalS: 60});
      return true;
    }
  }
});
