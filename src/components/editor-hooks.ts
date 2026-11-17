import { useEffect, useRef, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";
import { open, save } from "@tauri-apps/plugin-dialog";
import { call, desktop } from "../api";
import type { Job } from "../types";
export function useUndo<T>(initial: T) {
  const [value, setValue] = useState(initial);
  const live = useRef(value);
  live.current = value;
  const replace = (next: T) => {
    live.current = next;
    setValue(next);
  };
  const [past, setPast] = useState<T[]>([]);
  const [future, setFuture] = useState<T[]>([]);
  const start = useRef<T | null>(null);
  const change = (next: T) => {
    const previous = live.current;
    setPast((old) => [...old.slice(-99), previous]);
    setFuture([]);
    replace(next);
  };
  return {
    value,
    change,
    replace,
    read: () => live.current,
    begin: () => {
      start.current = live.current;
    },
    finish: () => {
      if (start.current) {
        const old = start.current;
        setPast((p) => [...p.slice(-99), old]);
        setFuture([]);
        start.current = null;
      }
    },
    undo: () => {
      if (past.length) {
        setFuture((f) => [value, ...f]);
        replace(past[past.length - 1]);
        setPast((p) => p.slice(0, -1));
      }
    },
    redo: () => {
      if (future.length) {
        setPast((p) => [...p, value]);
        replace(future[0]);
        setFuture((f) => f.slice(1));
      }
    },
    canUndo: !!past.length,
    canRedo: !!future.length,
  };
}
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
async function release(job: Job) {
  try {
    let current = job;
    if (["queued", "running", "cancelling"].includes(current.status))
      await call("cancel", { id: job.id });
    for (let i = 0; i < 60; i++) {
      current = await call<Job>("preview_status", { id: job.id });
      if (!["queued", "running", "cancelling"].includes(current.status)) {
        await call("clear_preview", { id: job.id });
        return;
      }
      await sleep(300);
    }
  } catch {
    /* Application shutdown also terminates the job tree. */
  }
}
export function useRenderedPreview(
  project: unknown,
  enabled: boolean,
  type = "fcvideo",
) {
  const serialized = JSON.stringify(project);
  const [result, setResult] = useState<{
    uri: string;
    hash: string;
    error: string;
    progress: number;
  }>({ uri: "", hash: "", error: "", progress: 0 });
  useEffect(() => {
    if (!desktop || !enabled) return;
    let cancelled = false;
    let job: Job | undefined;
    const timer = setTimeout(() => {
      void (async () => {
        try {
          setResult((r) => ({ ...r, error: "", progress: 0 }));
          job = await call<Job>("editor", {
            action: "enqueue",
            type,
            project: JSON.parse(serialized),
            preview: true,
            format: type === "fcvideo" ? "mp4" : "png",
          });
          while (!cancelled) {
            const state = await call<Job>("preview_status", { id: job.id });
            if (state.status === "failed" || state.status === "cancelled")
              throw new Error(state.error || "預覽已取消");
            if (state.status === "completed") {
              setResult({
                uri: convertFileSrc(state.outputs[0]),
                hash: serialized,
                error: "",
                progress: 100,
              });
              return;
            }
            setResult((r) => ({ ...r, progress: state.progress }));
            await sleep(400);
          }
        } catch (e) {
          if (!cancelled) setResult((r) => ({ ...r, error: String(e) }));
        } finally {
          if (cancelled && job) void release(job);
        }
      })();
    }, 650);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      if (job) void release(job);
    };
  }, [serialized, enabled, type]);
  return { ...result, dirty: result.hash !== serialized };
}
export async function projectDialog(
  type: "fcvideo" | "fcimage",
  action: "save" | "load",
  project?: unknown,
  path?: string,
) {
  const extension = type + ".json";
  const chosen =
    path ||
    (action === "load"
      ? await open({
          multiple: false,
          filters: [
            { name: "File Converter project", extensions: [extension] },
          ],
        })
      : await save({
          defaultPath: "Project." + extension,
          filters: [
            { name: "File Converter project", extensions: [extension] },
          ],
        }));
  if (!chosen || Array.isArray(chosen)) return null;
  const suffix = "." + extension;
  const target =
    action === "save" && !chosen.toLowerCase().endsWith(suffix)
      ? chosen + suffix
      : chosen;
  return {
    path: target,
    ...(await call<{ project: unknown; missing?: string[] }>("editor", {
      action,
      type,
      path: target,
      project,
    })),
  };
}

export const editorStatus: Record<string, string> = {
  queued: "等待中",
  running: "處理中",
  cancelling: "取消中",
  completed: "已完成",
  failed: "失敗",
  cancelled: "已取消",
};
