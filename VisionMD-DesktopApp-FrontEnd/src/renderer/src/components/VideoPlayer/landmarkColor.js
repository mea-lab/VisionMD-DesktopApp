/** Return the stable display color for one landmark.
 *
 * Backend-provided colors have priority. Gait uses these to encode detected
 * events at the ankles. Tasks without semantic colors use a stable per-index
 * palette; index zero (the MediaPipe/WiLoR wrist) keeps its historic red.
 */
export function landmarkDisplayColor(colors, frameIndex, landmarkIndex) {
  const semantic = colors?.[frameIndex]?.[landmarkIndex];
  if (Array.isArray(semantic) && semantic.length >= 3) {
    const [r, g, b] = semantic;
    return `rgb(${r}, ${g}, ${b})`;
  }
  if (landmarkIndex === 0) return 'red';
  const hue = (landmarkIndex * 137.508) % 360;
  return `hsl(${hue}, 82%, 52%)`;
}
