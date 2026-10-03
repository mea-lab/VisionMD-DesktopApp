export function prepareSubjectSelection(data, fps, automatic = false) {
  const boxes = Array.isArray(data.boundingBoxes) ? data.boundingBoxes : [];
  const first = new Map();
  boxes.forEach(frame => frame.data.forEach(box => {
    if (!first.has(box.id)) first.set(box.id, frame.frameNumber);
  }));
  const ids = [...first.keys()];
  const suggested = ids.includes(data.suggestedSubjectId) ? data.suggestedSubjectId
    : ids.length === 1 ? ids[0] : null;
  const persons = ids.map(id => {
    const prior = data.persons?.find(person => person.id === id);
    const isSubject = automatic ? id === suggested : prior?.isSubject ?? boxes.some(frame => frame.data.some(box => box.id === id && box.Subject));
    return { ...prior, id, name: prior?.name || `Person ${id}`, frameNumber: first.get(id),
      timestamp: (first.get(id) / fps).toFixed(2), isSubject,
      isSuggested: automatic && id === suggested };
  });
  return { persons, boundingBoxes: boxes.map(frame => ({ ...frame,
    data: frame.data.map(box => ({ ...box, Subject: persons.find(p => p.id === box.id)?.isSubject || false })) })),
    autoAdvance: automatic && ids.length === 1 && persons[0].isSubject };
}
