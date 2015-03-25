import Ember from "ember";


export default Ember.ObjectController.extend({
  name: "",
  actions: {
    save: function() {
      var self = this;
      var cldr = self.store.createRecord('calendar', {
        id: self.get('user')+"_"+self.get('name'),
        name: self.get('name'),
        user: self.get('user')
      });
      var promise = cldr.save();
      promise.then(function(){}, function(){
        cldr.deleteRecord();
      });
    }
  }
});
