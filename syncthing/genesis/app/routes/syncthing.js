import Ember from "ember";
import ENV from "../config/environment";


export default Ember.Route.extend({
  model: function() {
    return Ember.RSVP.hash({
      folders: this.get('store').find('folder'),
      devices: this.get('store').find('device'),
      config: $.getJSON(ENV.APP.krakenHost+'/api/apps/syncthing/config')
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
