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
  taskBoxes,
  opts,
) {
  const { onReset } = opts ?? {};
  const location = useLocation();

  const lastSavedRef = useRef({});
  const latestSlicesRef = useRef({ persons, boundingBoxes, taskBoxes, tasks });
  const prevVideoIdRef = useRef(null);

  useEffect(() => {
    latestSlicesRef.current = { persons, boundingBoxes, taskBoxes, tasks };
  }, [persons, boundingBoxes, taskBoxes, tasks]);

  const hasContent = (value) =>
    Array.isArray(value) ? value.length > 0 : !!(value && Object.keys(value).length > 0);

  const saveSlice = useCallback(
    async (key, value, idOverride, force = false) => {
      const resolvedId = (idOverride ?? videoId ?? prevVideoIdRef.current) || null;
      if (!resolvedId) return;

      if (!force) {
        const previous = lastSavedRef.current[key];
        if (isEqual(value, previous)) return;
      }

      lastSavedRef.current[key] = cloneDeep(value);

      const url = `${API_URL}/update_video_data/?id=${resolvedId}&file_name=${encodeURIComponent(key)}.json`;

      try {
        console.log(`[AutoSave] Saving "${key}" to ${resolvedId}\n`, value);
        await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(value),
        });
      } catch (err) {
        console.error(`[AutoSave] Error saving ${key}:`, err);
      }
    },
    [videoId]
  );

  const flushWithId = useCallback(
    async (id, force = false) => {
      const { persons, boundingBoxes, taskBoxes, tasks } = latestSlicesRef.current;
      const slices = { persons, boundingBoxes, taskBoxes, tasks };

      const work = [];
      Object.entries(slices).forEach(([key, value]) => {
        if (hasContent(value)) work.push(saveSlice(key, value, id ?? null, force));
      });
      await Promise.all(work);
    },
    [saveSlice]
  );

  const flush = useCallback(() => {
    return flushWithId(videoId ?? prevVideoIdRef.current ?? null);
  }, [flushWithId, videoId]);

  const debouncedFlush = useDebouncedCallback(flush, DEBOUNCE_MS);

  useEffect(() => {
    if (videoId) {
      prevVideoIdRef.current = videoId;
      lastSavedRef.current = {};
      return;
    }

    if (videoId === null && prevVideoIdRef.current) {
      (async () => {
        try {
          await flushWithId(prevVideoIdRef.current, true);
        } finally {
          lastSavedRef.current = {};
          onReset?.();
        }
      })();
    }
  }, [videoId, flushWithId, onReset]);

  useEffect(() => {
    debouncedFlush();
    return debouncedFlush.cancel;
  }, [location.pathname, debouncedFlush]);

  useEffect(() => {
    const handleBeforeUnload = () => {
      const id = videoId ?? prevVideoIdRef.current;
      if (!id) return;

      const { persons, boundingBoxes, taskBoxes, tasks } = latestSlicesRef.current;
      const slices = { persons, boundingBoxes, taskBoxes, tasks };

      Object.entries(slices).forEach(([key, value]) => {
        if (!hasContent(value)) return;

        const url = `${API_URL}/update_video_data/?id=${id}&file_name=${encodeURIComponent(key)}.json`;
        try {
          if (navigator.sendBeacon) {
            const blob = new Blob([JSON.stringify(value)], { type: "application/json" });
            navigator.sendBeacon(url, blob);
          } else {
            const xhr = new XMLHttpRequest();
            xhr.open("POST", url, false);
            xhr.setRequestHeader("Content-Type", "application/json");
            try { xhr.send(JSON.stringify(value)); } catch (_) {}
          }
        } catch (_) {}
      });
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [videoId]);
}
