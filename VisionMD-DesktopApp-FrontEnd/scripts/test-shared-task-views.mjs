// Render the actual task adapters with React, substituting only browser engines.
// Exercises shared chart configuration and segment data without a video/GPU.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import Module from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { build } from 'esbuild';
const base = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const react = require.resolve('react');
const server = require.resolve('react-dom/server');
const graphs = path.join(base,'src/renderer/src/pages/TaskDetails/Graphs');
const source = `
import React from ${JSON.stringify(react)};
import { renderToStaticMarkup } from ${JSON.stringify(server)};
import Sit from ${JSON.stringify(graphs+'/SitToStandGraphs.jsx')};
import Gait from ${JSON.stringify(graphs+'/GaitGraphs.jsx')};
import Segments from ${JSON.stringify(graphs+'/GaitSegmentsPanel.jsx')};
import { reviewedBoundary } from ${JSON.stringify(graphs+'/sitToStandBoundaries.js')};
export { reviewedBoundary };
export function render(Component,props) { return renderToStaticMarkup(React.createElement(Component,props)); }
export { Sit, Gait, Segments };
`;
const out = await build({ stdin: { contents: source, resolveDir: base }, bundle: true,
  write: false, platform: 'node', format: 'cjs', jsx: 'automatic',
  define: { 'import.meta.env.VITE_API_BASE_URL': '"http://localhost:8000/api"' },
  plugins: [{ name: 'browser-engine-stubs', setup(build) {
    build.onResolve({ filter: /^uplot-react$/ }, () => ({ path: 'plot', namespace: 'test' }));
    build.onResolve({ filter: /VideoSegmentsTimeline$/ }, () => ({ path: 'timeline', namespace: 'test' }));
    build.onLoad({ filter: /.*/, namespace: 'test' }, args => ({ contents: args.path === 'plot'
      ? `import React from ${JSON.stringify(react)};export default function Plot(props){globalThis.__plots.push(props);return React.createElement('div',{'data-shared-plot':true});}`
      : `import React from ${JSON.stringify(react)};export default function Timeline(props){globalThis.__timelines.push(props);return React.createElement('div',{'data-shared-timeline':true});}`,
      resolveDir: base }));
    build.onLoad({ filter: /uPlot\.min\.css$/ }, () => ({ contents: '', loader: 'text' }));
  }}],
});
const mod = new Module(path.join(base,'scripts/.task-view-test.cjs'));
mod.filename = path.join(base,'scripts/.task-view-test.cjs');
mod.paths = Module._nodeModulePaths(base);
mod._compile(out.outputFiles[0].text,mod.filename);
const { Sit,Gait,Segments,render,reviewedBoundary } = mod.exports;
const time = Array.from({length:121},(_,i) => 2+i/30);
const boundaries = { preparation_start:2.5,rise_start:3,rise_end:5 };
const signals = {time,pelvis_height:time.map(t=>t/10),pelvis_evidence:time.map(t=>t-2),shoulder_evidence:time.map(t=>t-1.8),pelvis_velocity:time.map(()=>2)};
const data = {sit_to_stand:{boundaries,signals,central_ascent:{start:3.2,end:4.5},feature_window:{start:3.1,end:4.6,source:'automatic_5_95'},quality:{warnings:[]}},sit_to_stand_analysis_cache:{fps:30}};
const video = {currentTime:0};
const props = {selectedTaskIndex:0,tasks:[{id:1,name:'Sit To Stand',data}],setTasks:()=>{},videoRef:{current:video}};
function reset(){globalThis.__plots=[];globalThis.__timelines=[];}
reset();const html=render(Sit,props);
assert(html.includes('Apply from cached sit-to-stand landmarks') && html.includes('Restore automatic'));
assert(html.includes('Sit-to-stand signal'));
assert(html.includes('Preparation signals over Time') && html.includes('Pelvis vertical velocity over Time'));
assert(html.includes('font-semibold') && html.includes('mx-4 min-w-0 rounded-lg'));
assert.equal(__plots.length,1);assert.equal(__plots[0].data[0][0],2);assert.equal(__plots[0].data[0].at(-1),6);
assert.equal(__plots[0].options.height,320);
assert.equal(__timelines.length,1);assert.equal(__timelines[0].regions.filter(r=>r.end==null).length,3);
assert.equal(__timelines[0].previewSignal,signals.pelvis_height);
__timelines[0].onRegionUpdated({id:'preparation_start',start:2.75});assert.equal(video.currentTime,2.7666666666666666);
const chart={over:{getBoundingClientRect:()=>({left:20})},posToVal:x=>x/100+2};
__plots[0].options.hooks.ready[0](chart);
chart.over.onpointerdown({clientX:120});chart.over.onclick({clientX:120});assert.equal(video.currentTime,3);
chart.over.onpointerdown({clientX:120});chart.over.onclick({clientX:170});assert.equal(video.currentTime,3,'drag must retain native zoom instead of seeking');
chart.over.onpointerdown({clientX:900});chart.over.onclick({clientX:900});assert.equal(video.currentTime,6,'seek clamps to cached range');
const ctx=new Proxy({},{get:(_,key)=>()=>{},set:()=>true});const draw={ctx,bbox:{left:50,top:10,width:500,height:180},valToPos:v=>v*20};
for(const plot of __plots){plot.options.hooks.drawClear[0](draw);plot.options.hooks.draw[0](draw);}
assert.equal(reviewedBoundary('preparation_start',4,boundaries,2,6,30),3);
assert.equal(reviewedBoundary('rise_start',6,boundaries,2,6,30),5-1/30);
assert.equal(reviewedBoundary('rise_end',1,boundaries,2,6,30),3+1/30);
reset();render(Gait,{...props,tasks:[{start:2,end:6,data:{signals:{pelvis:[1,2,3]}}}]});assert.equal(__plots.length,1);assert.deepEqual(__plots[0].data[0],[2,4,6]);
reset();render(Segments,{...props,tasks:[{start:2,end:6,data:{gait_analysis_cache:{start_time:2,fps:30,poses3d:new Array(121)},turning_metadata:{turns:[{start_time_seconds:3,end_time_seconds:3.5},{start_time_seconds:4.5,end_time_seconds:5}]}}}]});
assert.equal(__timelines.length,1);assert.equal(__timelines[0].regions.filter(r=>r.id.startsWith('turn-')).length,2);assert.equal(__timelines[0].regions.filter(r=>r.id.startsWith('walking-')).length,3);
reset();render(Gait,{...props,initialSignal:'preparation',plotGroups:[{key:'preparation',title:'Preparation signals',time,series:[{name:'Pelvis',values:signals.pelvis_evidence},{name:'Shoulders',values:signals.shoulder_evidence}],threshold:1}]});
assert.equal(__plots[0].data.length,3);assert.equal(__plots[0].options.series.length,3);
const sitSource=readFileSync(path.join(graphs,'SitToStandGraphs.jsx'),'utf8');
assert(!sitSource.includes('<svg'));assert(sitSource.includes('<GaitGraphs'));assert(sitSource.includes('<AnalysisWindowPanel'));
assert(readFileSync(path.join(graphs,'GaitSegmentsPanel.jsx'),'utf8').includes('<AnalysisWindowPanel'));
assert(!readFileSync(path.join(graphs,'GaitSegmentsPanel.jsx'),'utf8').includes("from 'wavesurfer.js'"));
console.log('PASS: shared task plots, absolute timestamps, two preparation channels, three draggable events, frame snapping, click-to-seek vs zoom, drawing overlays, and multiple gait turn/walking intervals.');
