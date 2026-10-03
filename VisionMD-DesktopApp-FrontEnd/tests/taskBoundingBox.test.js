import test from 'node:test';
import assert from 'node:assert/strict';
import { initializeTaskBox, patchTask, editTaskBox } from '../src/renderer/src/pages/TaskSelection/taskBoundingBox.js';
const detections = [
  { frameNumber: 0, data: [{ Subject: true, x: 10, y: 20, width: 100, height: 200 }] },
  { frameNumber: 30, data: [{ Subject: true, x: 30, y: 20, width: 100, height: 200 }] },
];
const task = { id: 1, name: 'Region', start: 0, end: 1 };
const box = t => [t.x, t.y, t.box_width, t.box_height];
test('resize then select a task preserves the edited region and invalidates analysis', () => {
  const initial = initializeTaskBox(task, detections, 30);
  const edited = editTaskBox({ ...initial, data: { old: true } }, { box_height: 60 });
  const selected = patchTask(edited, { name: 'Finger Tap Right' }, detections, 30);
  assert.deepEqual(box(selected), [10, 20, 120, 60]);
  assert.equal(selected.name, 'Finger Tap Right');
  assert.equal(selected.data, null);
  assert.equal(selected.box_manual, true);
});
test('moved regions survive timing edits and full-video restoration', () => {
  const edited = editTaskBox(initializeTaskBox(task, detections, 30), { x: 50, y: 60 });
  const changed = patchTask(edited, { start: 1 }, detections, 30);
  assert.deepEqual(box(changed), box(edited));
  assert.deepEqual(initializeTaskBox(changed, detections, 30), changed);
});
test('automatic regions follow time-range changes but task changes retain imported boxes', () => {
  const initial = initializeTaskBox(task, detections, 30);
  assert.deepEqual(box(patchTask(initial, { start: 1 }, detections, 30)), [30, 20, 100, 200]);
  const imported = { ...initial, x: 50, box_height: 40 };
  assert.deepEqual(box(patchTask(imported, { name: 'Gait' }, detections, 30)), box(imported));
});
test('missing detections never replace a valid region with infinite coordinates', () => {
  const initial = initializeTaskBox(task, detections, 30);
  assert.deepEqual(box(patchTask(initial, { start: 5, end: 6 }, detections, 30)), box(initial));
  assert.deepEqual(initializeTaskBox(task, [], 30), task);
});
