/* Qubitrail V4 — UI structural and functional smoke checks (Node, no browser required).
 * Run: node tests/frontend_smoke.js
 */
const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
let html='',overlay='';
const app={get innerHTML(){return html},set innerHTML(v){html=v}};
const overlays={get innerHTML(){return overlay},set innerHTML(v){overlay=v}};
const body={dataset:{},classList:{toggle(){}},appendChild(){}};
const storage=new Map();
const ctx={
 document:{body,querySelector:k=>k==='#app'?app:k==='#overlay-root'?overlays:null,addEventListener(){},createElement:()=>({remove(){}})},
 localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},
 window:{},setTimeout(){},requestAnimationFrame(){},console,Math,Date,JSON,Number,Array,String,Promise,Intl
};
vm.createContext(ctx);
const js=fs.readFileSync(path.join(__dirname,'..','frontend','app.js'),'utf8');
vm.runInContext(js.replace(/init\(\);\s*$/,'// no remote initialization during structural checks'),ctx);
function check(name,assertion){if(!assertion)throw Error('FAIL: '+name);console.log('PASS '+name)}
function view(page){vm.runInContext(`state.page=${JSON.stringify(page)};render()`,ctx)}
view('home');check('Immersive home entry',html.includes('home-hero')&&html.includes('home-journeys')&&html.includes('data-action="nav-studio"'));
view('studio');
check('Product-level top navigation',html.includes('class="topbar"')&&html.includes('mode-tabs')&&!html.includes('class="rail"'));
check('Central quantum circuit editor',html.includes('class="circuit-svg"')&&html.includes('data-gate="0"'));
check('Floating category-based gate dock',html.includes('data-gate-category="Essentials"')&&html.includes('data-gate-kind="CX"'));
vm.runInContext(`state.gateCategory='Advanced';render()`,ctx);
check('Advanced gate catalogue',html.includes('data-gate-kind="CCX"')&&html.includes('data-gate-kind="RESET"'));
check('Live inspector and gate properties',html.includes('data-field="type"')&&html.includes('data-field="target-0"'));
check('Canvas actions/undo/redo/focus',html.includes('data-action="undo"')&&html.includes('data-action="redo"')&&html.includes('data-action="focus"'));
check('Source & import controls',html.includes('data-action="console-code"')&&html.includes('data-action="console-import"'));
view('simulate');check('Dedicated observation workspace',html.includes('observation-layout')&&html.includes('Measurement distribution'));
view('debug');check('Dedicated repair workflow',html.includes('repair-canvas-panel')&&html.includes('repair-diagnosis-panel')&&html.includes('data-action="repair"'));
view('optimize');check('Optimization instruments',html.includes('optimization-metrics')&&html.includes('data-action="verify"'));
view('noise');check('Noise sliders and simulation',html.includes('data-noise="depolarizing"')&&html.includes('data-action="run-noise"'));
view('library');check('Algorithm library',html.includes('template-grid')&&html.includes('data-filter="All"'));
view('projects');check('Project management workspace',html.includes('feature-page'));
view('research');check('Benchmark and repair suite',html.includes('data-action="benchmark"')&&html.includes('data-action="repair-suite"'));
view('guide');check('Learning companion',html.includes('guide-form'));
vm.runInContext(`state.modal={type:'command'};renderOverlay()`,ctx);
check('Searchable command palette',overlay.includes('command-search')&&overlay.includes('nav-library'));
vm.runInContext(`state.modal={type:'save'};renderOverlay()`,ctx);
check('Save project modal',overlay.includes('save-name')&&overlay.includes('confirm-save'));
console.log('All 18 Qubitrail V4 frontend structural checks passed.');
