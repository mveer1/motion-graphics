global.window=global;const w=console.warn;console.warn=()=>{};global.THREE=require('./src/studio/vendor/three.min.js');console.warn=w;global.Studio={};
['brand','tibi3d','anatomy3d','exercises3d'].forEach(f=>require('./src/studio/kits/fitness/'+f+'.js'));
const T3=Studio.kit.fitness.t3d; const st=T3.stage(null,{headless:true}); const f=st.tibi({gender:'m'});
console.log([...new Set(f.muscles.map(r=>r.key+':'+r.layer))].join(' '));
console.log(Object.keys(T3.exercises).join(' '));
