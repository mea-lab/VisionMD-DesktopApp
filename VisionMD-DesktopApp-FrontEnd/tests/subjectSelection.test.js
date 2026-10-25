import test from 'node:test';
import assert from 'node:assert/strict';
import { prepareSubjectSelection as select } from '../src/renderer/src/pages/SubjectResolution/subjectSelection.js';
const boxes = ids => [{frameNumber: 0, data: ids.map(id => ({id, Subject: false}))}];
test('sole automatic candidate is selected and advances', () => {
  const r = select({boundingBoxes: boxes([7]), suggestedSubjectId: 7}, 30, true);
  assert.equal(r.autoAdvance, true);
  assert.equal(r.persons[0].isSubject, true);
  assert.equal(r.boundingBoxes[0].data[0].Subject, true);
});
test('multiple candidates select suggestion and wait for confirmation', () => {
  const r = select({boundingBoxes: boxes([1,2]), suggestedSubjectId: 2}, 30, true);
  assert.equal(r.autoAdvance, false);
  assert.deepEqual(r.persons.map(p => p.isSubject), [false,true]);
  assert.deepEqual(r.boundingBoxes[0].data.map(p => p.Subject), [false,true]);
});
test('empty or invalid suggestions do not advance', () => {
  assert.equal(select({boundingBoxes: []}, 30, true).autoAdvance, false);
  const r = select({boundingBoxes: boxes([1,2]), suggestedSubjectId: 9}, 30, true);
  assert.equal(r.autoAdvance, false);
  assert.ok(r.persons.every(p => !p.isSubject));
});
test('manual imports preserve choices and do not auto advance', () => {
  const r = select({boundingBoxes: boxes([1,2]), suggestedSubjectId: 2,
    persons: [{id:1, isSubject:true}, {id:2, isSubject:false}]}, 30);
  assert.deepEqual(r.persons.map(p => p.isSubject), [true,false]);
  assert.equal(r.autoAdvance, false);
});
