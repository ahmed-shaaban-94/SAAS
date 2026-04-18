"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Upload, File, Check, X, Eye, Loader2, Play } from "lucide-react";
import { API_BASE_URL } from "@/lib/constants";
import { getSession } from "next-auth/react";
import { LoadingCard } from "@/components/loading-card";
import { PipelineProgress } from "./pipeline-progress";
import { RecentImports } from "./recent-imports";
import { SampleDataCta } from "./sample-data-cta";
import { WizardProgress } from "./wizard-progress";
import { usePipelineRun } from "@/hooks/use-pipeline-run";
import {
  trackUploadStarted,
  trackUploadCompleted,
} from "@/lib/analytics-events";

interface UploadedFile {
  file_id: string;
  filename: string;
  size_bytes: number;
  status: string;
}

interface ColumnInfo {
  name: string;
  dtype: string;
  null_count: number;
  sample_values: string[];
}

interface PreviewData {
  file_id: string;
  filename: string;
  row_count: number;
  columns: ColumnInfo[];
  sample_rows: string[][];
  warnings: string[];
}

/**
 * Derive the 3-step wizard position from actual flow state.
 *
 * Step 1 = choose source (no file yet)
 * Step 2 = map columns (file uploaded, preview opened)
 * Step 3 = validate & run (confirmed OR pipeline in flight/complete)
 */
function deriveStep(opts: {
  hasFiles: boolean;
  confirmed: boolean;
  hasPreview: boolean;
  pipelineStarted: boolean;
}): number {
  if (opts.confirmed || opts.pipelineStarted) return 3;
  if (opts.hasFiles && opts.hasPreview) return 2;
  if (opts.hasFiles) return 2;
  return 1;
}

export function UploadOverview() {
  const router = useRouter();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { progress, isRunning, error: pipelineError, trigger, cleanup } = usePipelineRun();

  // Clean up SSE on unmount
  useEffect(() => cleanup, [cleanup]);

  // Golden-Path instrumentation: fire upload_started once per session when
  // the user lands on this page. See Phase 2 Task 0 (#399).
  useEffect(() => {
    trackUploadStarted();
  }, []);

  // Fire upload_completed when a pipeline run reaches success.
  // Dedup is handled per-run_id inside the helper.
  useEffect(() => {
    if (progress?.status === "success" && progress.run_id) {
      trackUploadCompleted({
        run_id: progress.run_id,
        duration_seconds: progress.duration_seconds ?? 0,
        rows_loaded: progress.rows_loaded,
      });
    }
  }, [progress?.status, progress?.run_id, progress?.duration_seconds, progress?.rows_loaded]);

  // Golden-path: a user's real pipeline run just finished — send them to
  // the dashboard's first-insight view (Phase 2 Task 3 / #402 lands the card).
  useEffect(() => {
    if (progress?.status === "success") {
      router.push("/dashboard?first_upload=1");
    }
  }, [progress?.status, router]);

  const currentStep = deriveStep({
    hasFiles: files.length > 0,
    confirmed,
    hasPreview: preview !== null,
    pipelineStarted: progress !== null,
  });

  const getAuthHeaders = async () => {
    const session = await getSession();
    const headers: Record<string, string> = {};
    if (session?.accessToken)
      headers["Authorization"] = `Bearer ${session.accessToken}`;
    return headers;
  };

  const handleUpload = useCallback(async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    setConfirmed(false);
    setErrorMsg(null);
    try {
      const formData = new FormData();
      for (let i = 0; i < fileList.length; i++) {
        formData.append("files", fileList[i]);
      }
      const headers = await getAuthHeaders();
      const res = await fetch(`${API_BASE_URL}/api/v1/upload/files`, {
        method: "POST",
        headers,
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setFiles(data);
    } catch (e) {
      setErrorMsg("Upload failed. Please check your files and try again.");
    } finally {
      setUploading(false);
    }
  }, []);

  const handlePreview = async (fileId: string) => {
    setPreviewLoading(true);
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`${API_BASE_URL}/api/v1/upload/preview/${fileId}`, { headers });
      if (!res.ok) throw new Error(await res.text());
      setPreview(await res.json());
    } catch (e) {
      setErrorMsg("Failed to load preview. Please try again.");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleConfirm = async () => {
    setConfirming(true);
    try {
      const headers = await getAuthHeaders();
      headers["Content-Type"] = "application/json";
      await fetch(`${API_BASE_URL}/api/v1/upload/confirm`, {
        method: "POST",
        headers,
        body: JSON.stringify({ file_ids: files.map((f) => f.file_id) }),
      });
      setConfirmed(true);
    } catch (e) {
      setErrorMsg("Import confirmation failed. Please try again.");
    } finally {
      setConfirming(false);
    }
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      handleUpload(e.dataTransfer.files);
    },
    [handleUpload],
  );

  const handleRunPipeline = async () => {
    await trigger();
  };

  return (
    <div className="mt-6 space-y-6">
      <WizardProgress currentStep={currentStep} />

      {currentStep === 1 && (
        <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-center">
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => inputRef.current?.click()}
            className="viz-panel flex cursor-pointer flex-col items-center justify-center rounded-[1.9rem] border-2 border-dashed border-border p-12 transition-colors hover:border-accent/50"
          >
            <Upload className="h-10 w-10 text-text-tertiary mb-3" />
            <p className="text-sm text-text-secondary">Drop files here or click to browse</p>
            <p className="text-xs text-text-tertiary mt-1">Supports .xlsx, .csv, .xls (max 100MB)</p>
            <input
              ref={inputRef}
              type="file"
              multiple
              accept=".xlsx,.csv,.xls"
              className="hidden"
              onChange={(e) => handleUpload(e.target.files)}
            />
          </div>

          <div className="flex items-center justify-center text-[11px] font-semibold uppercase tracking-[0.22em] text-text-tertiary">
            or
          </div>

          <SampleDataCta />
        </div>
      )}

      {currentStep !== 1 && (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => inputRef.current?.click()}
          className="viz-panel flex cursor-pointer flex-col items-center justify-center rounded-[1.9rem] border-2 border-dashed border-border p-12 transition-colors hover:border-accent/50"
        >
          <Upload className="h-10 w-10 text-text-tertiary mb-3" />
          <p className="text-sm text-text-secondary">Drop files here or click to browse</p>
          <p className="text-xs text-text-tertiary mt-1">Supports .xlsx, .csv, .xls (max 100MB)</p>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".xlsx,.csv,.xls"
            className="hidden"
            onChange={(e) => handleUpload(e.target.files)}
          />
        </div>
      )}

      {errorMsg && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-500">
          <X className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="ml-auto text-xs hover:underline">Dismiss</button>
        </div>
      )}

      {uploading && <LoadingCard className="h-20" />}

      {files.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">Uploaded Files</h3>
          {files.map((f) => (
            <div key={f.file_id} className="viz-panel-soft flex items-center gap-3 rounded-[1.2rem] p-3">
              <File className="h-4 w-4 text-text-secondary" />
              <div className="flex-1">
                <p className="text-sm text-text-primary">{f.filename}</p>
                <p className="text-xs text-text-tertiary">{(f.size_bytes / 1024).toFixed(0)} KB</p>
              </div>
              <button
                onClick={() => handlePreview(f.file_id)}
                className="viz-panel-soft rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-text-secondary transition-colors hover:text-accent"
              >
                <Eye className="h-3 w-3 inline mr-1" />Preview
              </button>
            </div>
          ))}

          {/* Action buttons */}
          <div className="flex gap-3">
            {!confirmed && (
              <button
                onClick={handleConfirm}
                disabled={confirming}
                className="flex items-center gap-1.5 rounded-2xl bg-green-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-60"
              >
                {confirming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4" />
                )}
                {confirming ? "Importing..." : "Confirm Import"}
              </button>
            )}

            {confirmed && !isRunning && !progress?.status?.includes("success") && (
              <button
                onClick={handleRunPipeline}
                className="flex items-center gap-1.5 rounded-2xl bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-accent/90"
              >
                <Play className="h-4 w-4" />
                Run Pipeline
              </button>
            )}
          </div>

          {confirmed && !progress && (
            <div className="viz-panel rounded-[1.25rem] border-green-500/20 bg-green-500/8 p-3 text-sm text-green-500">
              Files confirmed and ready for processing. Click &ldquo;Run Pipeline&rdquo; to start.
            </div>
          )}
        </div>
      )}

      {progress && (
        <PipelineProgress
          progress={progress}
          isRunning={isRunning}
          error={pipelineError}
        />
      )}

      {previewLoading && <LoadingCard className="h-64" />}
      {preview && !previewLoading && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
              Preview: {preview.filename} ({preview.row_count} rows, {preview.columns.length} columns)
            </h3>
            <button onClick={() => setPreview(null)} className="text-text-secondary hover:text-text-primary">
              <X className="h-4 w-4" />
            </button>
          </div>

          {preview.warnings.length > 0 && (
            <div className="viz-panel rounded-[1.25rem] border-yellow-500/20 bg-yellow-500/8 p-3 text-xs text-yellow-500">
              {preview.warnings.map((w, i) => <p key={i}>{w}</p>)}
            </div>
          )}

          <div className="viz-panel overflow-x-auto rounded-[1.75rem]">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-background/50">
                  {preview.columns.map((col) => (
                    <th key={col.name} className="px-3 py-2 text-left font-semibold uppercase tracking-[0.14em] text-text-secondary whitespace-nowrap">
                      {col.name}
                      <br />
                      <span className="font-normal text-text-tertiary">{col.dtype}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.sample_rows.map((row, i) => (
                  <tr key={i} className="border-b border-border/50">
                    {row.map((cell, j) => (
                      <td key={j} className="px-3 py-1.5 text-text-primary whitespace-nowrap max-w-[200px] truncate">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent pipeline runs */}
      <RecentImports />
    </div>
  );
}
