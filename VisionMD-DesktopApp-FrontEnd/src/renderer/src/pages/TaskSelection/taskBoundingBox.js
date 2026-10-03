const hasBox = task =>
  ['x', 'y', 'box_width', 'box_height'].every(key => Number.isFinite(task[key])) &&
  task.box_width > 0 && task.box_height > 0;

export function initializeTaskBox(task, boundingBoxes, fps) {
  // Manual/imported regions survive replacement and full-video restoration.
  if (hasBox(task)) return task;
  return detectedTaskBox(task, boundingBoxes, fps);
}

function detectedTaskBox(task, boundingBoxes, fps) {
  const startFrame = Math.ceil(task.start * fps);
  const endFrame = Math.floor(task.end * fps);
  const boxes = boundingBoxes
    .filter(({ frameNumber }) => frameNumber >= startFrame && frameNumber <= endFrame)
    .flatMap(({ data }) => data.filter(item => item.Subject === true))
    .filter(box => [box.x, box.y, box.width, box.height].every(Number.isFinite) &&
      box.width > 0 && box.height > 0);
  if (!boxes.length) return task;
  const x = Math.min(...boxes.map(box => box.x));
  const y = Math.min(...boxes.map(box => box.y));
  return { ...task, x, y,
    box_width: Math.max(...boxes.map(box => box.x + box.width)) - x,
    box_height: Math.max(...boxes.map(box => box.y + box.height)) - y };
}

export function patchTask(task, patch, boundingBoxes, fps) {
  const merged = { ...task, ...patch };
  // A new task type gets its own default, rather than inheriting the previous
  // type's normalization. Explicit choices on the same task remain intact.
  if (merged.name !== task.name && !patch.norm_strategy) {
    if (['Hand Movement Left', 'Hand Movement Right'].includes(merged.name)) {
      merged.norm_strategy = 'PALMSIZE';
    } else if (['Finger Tap Left', 'Finger Tap Right'].includes(merged.name)) {
      merged.norm_strategy = 'INDEXSIZE';
    }
  }
  const windowChanged = merged.start !== task.start || merged.end !== task.end;
  if (windowChanged && !merged.box_manual) {
    return detectedTaskBox(merged, boundingBoxes, fps);
  }
  return initializeTaskBox(merged, boundingBoxes, fps);
}

export function editTaskBox(task, patch) {
  return { ...task, ...patch, box_manual: true, data: null };
}
