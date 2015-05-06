import DS from "ember-data";


export default DS.Model.extend({
    path: DS.attr('string'),
    order: DS.attr('string'),
    hashers: DS.attr('number'),
    invalid: DS.attr('string'),
    ignorePerms: DS.attr('boolean'),
    devices: DS.attr(),
    readOnly: DS.attr('boolean'),
    lenientMTimes: DS.attr('boolean'),
    rescanIntervalS: DS.attr('number'),
    copiers: DS.attr('number'),
    autoNormalize: DS.attr('boolean'),
    versioning: DS.attr(),
    pullers: DS.attr('number')
});
