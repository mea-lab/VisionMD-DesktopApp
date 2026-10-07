const LEGACY_EDITABLE_TASKS = new Set([
  'Finger Tap Left',
  'Finger Tap Right',
  'Hand Movement Left',
  'Hand Movement Right',
  'Leg Agility Left',
  'Leg Agility Right',
  'Toe Tapping Left',
  'Toe Tapping Right',
]);

export const landmarkKey = (data, role = 'display') => {
  const roleSchema = data?.landmarkSchema?.[role];
  if (roleSchema && Object.hasOwn(roleSchema, 'key')) return roleSchema.key;
  return role === 'normalization' ? 'allLandMarks' : 'landMarks';
};

export const landmarksForRole = (data, role = 'display') => {
  const key = landmarkKey(data, role);
  if (!key) return undefined;
  return key.split('.').reduce((value, segment) => value?.[segment], data);
};

export const canEditLandmarks = (task) => {
  const declared = task?.data?.landmarkSchema?.manualEditing?.supported;
  return declared ?? LEGACY_EDITABLE_TASKS.has(task?.name);
};
