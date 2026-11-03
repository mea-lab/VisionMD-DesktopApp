// Persist the pending reset on the task so it survives navigation and autosave.
export const FRESH_ANALYSIS_KEY = 'fresh_analysis_required';

export const resetTaskForAnalysis = task => ({ ...task, data: null, [FRESH_ANALYSIS_KEY]: true });

export const needsFreshAnalysis = task => task?.[FRESH_ANALYSIS_KEY] === true;

export function taskWithAnalysisResult(task, data) {
  const updated = { ...task, data };
  delete updated[FRESH_ANALYSIS_KEY];
  return updated;
}
