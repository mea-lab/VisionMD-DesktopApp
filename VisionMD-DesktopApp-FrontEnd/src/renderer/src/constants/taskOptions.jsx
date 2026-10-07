// src/constants/taskOptions.jsx

const taskDetailsFiles = import.meta.glob(
  '../pages/TaskDetails/Tasks/*.jsx'
);
const taskSelectionFiles = import.meta.glob([
  '../pages/TaskSelection/Tasks/*.jsx',
  '!../pages/TaskSelection/Tasks/default.jsx',
]);

const taskOptions = [
  { value: 'Gait', label: 'Gait' },
  { value: 'Finger Tap Left', label: 'Finger Tap Left' },
  { value: 'Finger Tap Right', label: 'Finger Tap Right' },
  { value: 'Hand Movement Left', label: 'Hand Movement Left' },
  { value: 'Hand Movement Right', label: 'Hand Movement Right' },
  // Keep the legacy values because they determine backend module/class names;
  // the clearer labels are what users see in the task selection screen.
  { value: 'Hand Pronation Left', label: 'Pronation/Supination Left' },
  { value: 'Hand Pronation Right', label: 'Pronation/Supination Right' },
  { value: 'Toe tapping Left', label: 'Toe tapping Left' },
  { value: 'Toe tapping Right', label: 'Toe tapping Right' },
  { value: 'Leg agility Left', label: 'Leg agility Left' },
  { value: 'Leg agility Right', label: 'Leg agility Right' },
  { value: 'Hand Tremor Left Elbow Extended', label: 'Hand Tremor Left Elbow Extended' },
  { value: 'Hand Tremor Right Elbow Extended', label: 'Hand Tremor Right Elbow Extended' },
];


const errors = [];
taskOptions.forEach(({ value }) => {
  const fileName = value.toLowerCase().replace(/\s+/g, '_') + '.jsx';
  const hasSelection = Object.keys(taskSelectionFiles).some((p) =>
    p.endsWith(`/Tasks/${fileName}`)
  );
  const hasDetails = Object.keys(taskDetailsFiles).some((p) =>
    p.endsWith(`/Tasks/${fileName}`)
  );

  if (!hasSelection) {
    errors.push(
      `Startup check failed: missing “${fileName}” in src/pages/TaskSelection/Tasks. Task selection tab is not defined for value: “${value}”.`
    );
  }
  if (!hasDetails) {
    errors.push(
      `Startup check failed: missing “${fileName}” in src/pages/TaskDetails/Tasks/. Task analysis is not defined for value: “${value}”.`
    );
  }
});

if (errors.length > 0) {
  errors.forEach((msg) => console.error(msg));
  throw new Error(`Startup checks failed with ${errors.length} error(s).`);
}

export { taskOptions };
