/*
 * Motion Lab fitness kit - Sinew brand palette (src/studio/kits/fitness/brand.js)
 *
 * Load first among the kit files: anatomy.js, graphics.js and exercises.js read Studio.kit.fitness.palette.
 * Mirrors src/studio/styles/sinew-lab.css; Tibi's own colours are in sculpt-data.js (F.sculptData.colors).
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  var KIT = Studio.kit = Studio.kit || {};
  var F = KIT.fitness = KIT.fitness || {};

  F.palette = {
    paper: '#F6F3EC', paper2: '#ECE5D8', ink: '#1B1D29', ink2: '#4A4E60', ink3: '#8A8D9C',
    cobalt: '#2F56E0', cobaltDeep: '#2442B8', cobaltLine: '#18286F', cobaltLight: '#7E98F5', cobaltGlass: '#DCE4FF',
    cobaltPlane: '#4F75EC', cobaltShade: '#2244B8', navy: '#18286F',
    spark: '#FFB224', sparkDeep: '#F08A00', sparkLight: '#FFD98A',
    muscle: '#F2553D', muscleDeep: '#C2381F', muscleLight: '#FF9A80', tendon: '#EBD9B4',
    bone: '#F4EAD5', boneLine: '#A8916A', visor: '#FFF8EC', short: '#22243A', shoe: '#FBF7EE',
    emerald: '#12A36E', violet: '#7B5CE0', oxy: '#E23B4E', deoxy: '#4B5BD6',
    // equipment (flat planes, no outlines, like Tibi)
    steel: '#C9CFE0', steelShade: '#9AA3BF', steelLight: '#E6E9F2', plate: '#2A2D45', plateFace: '#3A3F63', plateRim: '#545A86',
    pad: '#2D3158', padTop: '#454A7C', padShade: '#1E2140'
  };
})(typeof window !== 'undefined' ? window : this);
