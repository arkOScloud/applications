import Ember from "ember";
import ENV from "../config/environment";


export default Ember.Route.extend({
  model: function() {
    return Ember.RSVP.hash({
      calendars: this.get('store').find('calendar'),
      addressBooks: this.get('store').find('addressBook'),
      domains: this.get('store').find('domain'),
      users: this.get('store').find('user'),
      status: $.getJSON(ENV.APP.krakenHost+'/api/apps/radicale/setup')
    });
  },
  actions: {
    delete: function(model){
      model.destroyRecord().then(function(){}, function(){
        model.rollback();
      });
    }
  }
});
