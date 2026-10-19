/** Constrain a dragged event to the cached frame grid and ordered neighbours. */
export function reviewedBoundary(key, value, boundaries, start, end, fps) {
  const frame = 1/fps;
  const snapped = start+Math.round((value-start)*fps)/fps;
  const minimum = key === 'rise_start' ? boundaries.preparation_start
    : key === 'rise_end' ? boundaries.rise_start+frame : start;
  const maximum = key === 'preparation_start' ? boundaries.rise_start
    : key === 'rise_start' ? boundaries.rise_end-frame : end;
  return Math.max(start,Math.min(end,Math.max(minimum,Math.min(maximum,snapped))));
}
