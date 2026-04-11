"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Upload, File, Check, X, Eye, Loader2, Play } from "lucide-react";
import { API_BASE_URL } from "@/lib/constants";
import { getSession } from "next-auth/react";
import { LoadingCard } from "@/components/loading-card";
import { PipelineProgress } from "./pipeline-progress";
import { RecentImports } from "./recent-imports";
import { usePipelineRun } from "@/hooks/use-pipeline-run";

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

export function UploadOverview() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { progress, isRunning, error: pipelineError, trigger, cleanup } = usePipelineRun();

  // Clean up SSE on unmount
  useEffect(() => cleanup, [cleanup]);

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
      console.error("Upload failed", e);
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
      console.error("Preview failed", e);
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
      console.error("Confirm failed", e);
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
    <div className="space-y-6 mt-6">
      {/* Dropzone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-border bg-card p-12 cursor-pointer hover:border-accent/50 transition-colors"
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

      {uploading && <LoadingCard className="h-20" />}

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-text-primary">Uploaded Files</h3>
          {files.map((f) => (
            <div key={f.file_id} className="flex items-center gap-3 rounded-lg border border-border bg-card p-3">
              <File className="h-4 w-4 text-text-secondary" />
              <div className="flex-1">
                <p className="text-sm text-text-primary">{f.filename}</p>
                <p className="text-xs text-text-tertiary">{(f.size_bytes / 1024).toFixed(0)} KB</p>
              </div>
              <button
                onClick={() => handlePreview(f.file_id)}
                className="rounded-lg border border-border px-2 py-1 text-xs text-text-secondary hover:bg-muted"
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
                className="flex items-center gap-1.5 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-60"
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
                className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90"
              >
                <Play className="h-4 w-4" />
                Run Pipeline
              </button>
            )}
          </div>

          {confirmed && !progress && (
            <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-3 text-sm text-green-500">
              Files confirmed and ready for processing. Click &ldquo;Run Pipeline&rdquo; to start.
            </div>
          )}
        </div>
      )}

      {/* Pipeline progress */}
      {progress && (
        <PipelineProgress
          progress={progress}
          isRunning={isRunning}
          error={pipelineError}
        />
      )}

      {/* Preview table */}
      {previewLoading && <LoadingCard className="h-64" />}
      {preview && !previewLoading && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-text-primary">
              Preview: {preview.filename} ({preview.row_count} rows, {preview.columns.length} columns)
            </h3>
            <button onClick={() => setPreview(null)} className="text-text-secondary hover:text-text-primary">
              <X className="h-4 w-4" />
            </button>
          </div>

          {preview.warnings.length > 0 && (
            <div className="rounded-lg bg-yellow-500/10 border border-yellow-500/20 p-3 text-xs text-yellow-500">
              {preview.warnings.map((w, i) => <p key={i}>{w}</p>)}
            </div>
          )}

          <div className="overflow-x-auto rounded-xl border border-border bg-card">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  {preview.columns.map((col) => (
                    <th key={col.name} className="px-3 py-2 text-left font-medium text-text-secondary whitespace-nowrap">
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
