import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import Module from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';

const base = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = `export * from './src/renderer/src/utils/resetAnalysis.js'; export * from './src/renderer/src/utils/analysisJobs.js';`;
const out = await build({stdin: {contents: source, resolveDir: base}, bundle: true, write: false, platform: 'node', format: 'cjs',
  define: {'import.meta.env.VITE_API_BASE_URL': '"http://localhost:8000/api"'}});
const mod = new Module(path.join(base, 'scripts/.reset-test.cjs'));
mod.filename = path.join(base, 'scripts/.reset-test.cjs');
mod.paths = Module._nodeModulePaths(base);
mod._compile(out.outputFiles[0].text, mod.filename);
const { resetTaskForAnalysis, needsFreshAnalysis, taskWithAnalysisResult, runAnalysisJob, FRESH_ANALYSIS_KEY } = mod.exports;
const taskNames = readdirSync(path.join(base, '../VisionMD-DesktopApp-BackEnd/app/analysis/tasks')).filter(name => name.endsWith('.py') && !name.startsWith('_') && name !== 'base_task.py').map(name => name.slice(0, -3));
const previousFetch = globalThis.fetch;
try {
  for (const name of taskNames) {
    const original = {id: 1, name, start: 2, end: 8, height: 175, data: {old: true}};
    const reset = resetTaskForAnalysis(original);
    assert.equal(reset.data, null);
    assert.equal(reset.start, original.start);
    assert.equal(original.data.old, true);
    // Pending reset survives autosave/reload and a failed attempt.
    const restored = JSON.parse(JSON.stringify(reset));
    assert(needsFreshAnalysis(restored));
    globalThis.fetch = async url => {
      assert(url.includes('&force=1'), `${name} must bypass backend cache`);
      return {ok: true, json: async () => ({status: 'failed', error: 'Tracking failed'})};
    };
    await assert.rejects(runAnalysisJob({taskName: name, videoId: 'v', jsonData: '{}', force: needsFreshAnalysis(restored)}), /Tracking failed/);
    assert(needsFreshAnalysis(restored));
    globalThis.fetch = async (url, options) => {
      assert(url.includes(`/analysis_jobs/${name}/?id=v&force=1`));
      assert(!options.body.get('json_data').includes(FRESH_ANALYSIS_KEY));
      return {ok: true, json: async () => ({status: 'completed', result: {fresh: true}})};
    };
    const result = await runAnalysisJob({taskName: name, videoId: 'v', jsonData: '{}', force: needsFreshAnalysis(restored)});
    const completed = taskWithAnalysisResult(restored, result);
    assert.equal(completed.data.fresh, true);
    assert.equal(needsFreshAnalysis(completed), false);
  }
  // Both Analyze and Analyze All use the same pending-reset flag.
  for (const name of ['index.jsx', 'JSONUploadDialog.jsx']) {
    const source = readFileSync(path.join(base, 'src/renderer/src/pages/TaskDetails', name), 'utf8');
    assert(source.includes('force: needsFreshAnalysis(taskData)'));
    assert(source.includes("['start', 'end', 'name', 'data', FRESH_ANALYSIS_KEY]"));
  }
  console.log(`PASS: Reset forces fresh inference for all ${taskNames.length} tasks; failures retain the reset; successful results clear it.`);
} finally {
  globalThis.fetch = previousFetch;
}
