import Ember from "ember";


export default Ember.ObjectController.extend({
  name: "",
  actions: {
    save: function() {
      var self = this;
      var book = self.store.createRecord('addressBook', {
        id: self.get('user')+"_"+self.get('name'),
        name: self.get('name'),
        user: self.get('user')
      });
      var promise = book.save();
      promise.then(function(){}, function(){
        book.deleteRecord();
      });
    }
  }
});
