import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { DownloadEvent } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { call, desktop } from "./api";
import type { Settings } from "./types";

export interface UpdateView {
  phase: "idle" | "checking" | "available" | "current" | "downloading" | "ready" | "installing" | "error";
  installed?: boolean; busy?: boolean; version?: string; notes?: string;
  downloaded: number; total?: number; verified: boolean; downloadPath?: string;
  error?: string; waitReason?: string; message?: string; channel?: string;
}
// Progress payload follows the official updater's byte counts, never a timer.
export type UpdaterDownloadEvent = DownloadEvent;
export function useUpdates(settings: Settings, ready: boolean) {
  const [view, setView] = useState<UpdateView>({ phase: "idle", downloaded: 0, verified: false });
  const live = useRef(settings); live.current = settings;
  const started = useRef(false);
  const busy = useRef(false);
  const automatic = useRef("");
  const request = async (command: string, args = {}) => {
    if (!desktop) { setView(v => ({ ...v, error: "請在 Windows 桌面版檢查更新" })); return; }
    if (busy.current) return;
    busy.current = true;
    try { setView(await invoke<UpdateView>(command, args)); }
    catch (error) { setView(v => ({ ...v, error: String(error) })); }
    finally { busy.current = false; }
  };
  const check = () => { automatic.current=""; return request("update_check", { channel: live.current.updater.channel }); };
  const download = () => request("update_download");
  const install = async () => {
    if (busy.current || !desktop) return;
    // Persist the latest preference state before the Windows updater exits.
    try { await call("settings", { settings: live.current }); }
    catch (error) { setView(v=>({...v,error:`設定儲存失敗，未安裝更新：${String(error)}`})); return; }
    await request("update_install");
    // Windows NSIS performs /R restart itself. This is the official Process
    // plugin fallback on platforms whose install() returns without exiting.
    if (navigator.platform !== "Win32" && navigator.platform !== "Win64") await relaunch();
  };
  useEffect(() => {
    if (!desktop) return;
    let disposed = false;
    let stop: (() => void) | undefined;
    void listen<UpdateView>("update-state", e=>setView(e.payload)).then(unlisten=>{if(disposed)unlisten();else stop=unlisten;});
    void invoke<UpdateView>("update_status").then(value=>{if(!disposed)setView(value);});
    return () => { disposed=true; stop?.(); };
  },[]);
  useEffect(() => {
    if (!ready || started.current) return;
    started.current=true;
    if (desktop && live.current.updater.checkOnStartup) void check();
  },[ready]);
  useEffect(() => {
    const preferences=settings.updater;
    if (view.phase!=="available" || view.channel!==preferences.channel || !preferences.autoDownload || automatic.current===view.version) return;
    const timer=setInterval(()=>{
      if(busy.current || automatic.current===view.version)return;
      automatic.current=view.version || "";
      void download();
    },300);
    return ()=>clearInterval(timer);
  },[view.phase,view.version,view.channel,settings.updater.channel,settings.updater.autoDownload]);
  useEffect(() => {
    if (view.phase!=="ready" || view.channel!==settings.updater.channel || !view.installed || !settings.updater.autoInstall) return;
    const timer=setInterval(()=>{void install();},5000);
    void install();
    return ()=>clearInterval(timer);
  },[view.phase,view.installed,view.channel,settings.updater.channel,settings.updater.autoInstall]);
  return { view, check, download, install, openDownload: () => invoke("update_open_download") };
}
export type UpdateController = ReturnType<typeof useUpdates>;
