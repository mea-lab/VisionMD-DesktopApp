import { useCallback, useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { useDebouncedCallback } from "use-debounce";
import isEqual from "lodash/isEqual";
import cloneDeep from "lodash/cloneDeep";

const API_URL = import.meta.env.VITE_API_BASE_URL;
const DEBOUNCE_MS = 500;

export function useAutoSave(
  videoId,
  persons,
  boundingBoxes,
  tasks,
  taskBoxes
) {
  const location = useLocation();
  const lastSavedRef = useRef({});
  const latestSlicesRef = useRef({});

  // Keep the latest props in a ref
  useEffect(() => {
    latestSlicesRef.current = { persons, boundingBoxes, taskBoxes, tasks };
  }, [persons, boundingBoxes, taskBoxes, tasks]);

  // Reset cache when video changes
  useEffect(() => {
    lastSavedRef.current = {};
  }, [videoId]);

  // Save one slice if it changed
  const saveSlice = useCallback(async (key, value) => {
    if (!videoId) return;
    const previous = lastSavedRef.current[key];
    if (isEqual(value, previous)) return;

    // Store a deep clone to avoid future mutations
    lastSavedRef.current[key] = cloneDeep(value);

    console.log(`[AutoSave] Saving "${key}"… \n`, value );
    try {
      await fetch(
        `${API_URL}/update_video_data/?id=${videoId}&file_name=${key}.json`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(value),
        }
      );
    } catch (err) {
      console.error(`[AutoSave] Error saving ${key}:`, err);
    }
  }, [videoId]);

  // Flush all non-empty slices
  const flush = useCallback(() => {
    const { persons, boundingBoxes, taskBoxes, tasks } = latestSlicesRef.current;
    const slices = { persons, boundingBoxes, taskBoxes, tasks };

    Object.entries(slices).forEach(([key, value]) => {
      const hasContent =
        Array.isArray(value)
          ? value.length > 0
          : value && Object.keys(value).length > 0;
      if (hasContent) saveSlice(key, value);
    });
  }, [saveSlice]);

  const debouncedFlush = useDebouncedCallback(flush, DEBOUNCE_MS);

  // Flush on route change
  useEffect(() => {
    debouncedFlush();
    return debouncedFlush.cancel;
  }, [location.pathname, debouncedFlush]);

  // Flush before the window unloads
  useEffect(() => {
    window.addEventListener("beforeunload", flush);
    return () => window.removeEventListener("beforeunload", flush);
  }, [flush]);
}
