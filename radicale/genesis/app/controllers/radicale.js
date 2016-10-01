import Ember from "ember";
import ENV from "../config/environment";
import {showFade, showLoader, hideLoader, hideFade} from "../utils/loading";


export default Ember.Controller.extend({
  setupPort: 80,
  actions: {
    setup: function() {
      var self   = this,
          config = {addr: this.get('setupAddr'), port: this.get('setupPort')};
      showFade();
      showLoader();
      $.ajax({
        url: ENV.APP.krakenHost+'/api/apps/radicale/setup',
        type: "POST",
        data: JSON.stringify({config: config}),
        contentType: 'application/json',
        processData: false,
        success: function(j) {
          self.set('model.status.installed', true);
          self.set('model.status.running', true);
          hideLoader();
          hideFade();
          self.message.success('Setup complete.');
        }
      });
    }
  }
});
