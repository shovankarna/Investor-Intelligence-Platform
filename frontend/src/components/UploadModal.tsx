"use client";

import React, { useState, useRef } from "react";
import {
  X,
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
} from "lucide-react";
import { uploadFiling } from "@/lib/api";
import { DocumentItem } from "@/types";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (newDoc: DocumentItem) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [company, setCompany] = useState("");
  const [fiscalYear, setFiscalYear] = useState(2024);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  // Auto-detect company & year from filename for instant UX
  const parseFilenameHints = (filename: string) => {
    const clean = filename.replace(/\.[^/.]+$/, ""); // remove extension

    // Match year (e.g. 2020 to 2030)
    const yearMatch = clean.match(/\b(20[123]\d)\b/);
    if (yearMatch) {
      setFiscalYear(parseInt(yearMatch[1], 10));
    }

    // Match company hint (e.g., AAPL, Apple, NVDA, Microsoft, TSLA)
    const namePart = clean
      .replace(/\b(20[123]\d)\b/g, "")
      .replace(/\b(10-?k|10-?q|20-?f|annual|report|filing)\b/gi, "")
      .replace(/[-_]/g, " ")
      .trim();

    if (namePart.length >= 2 && !company) {
      setCompany(namePart);
    }
  };

  const handleFile = (selectedFile: File) => {
    if (
      selectedFile.type === "application/pdf" ||
      selectedFile.name.toLowerCase().endsWith(".pdf")
    ) {
      setFile(selectedFile);
      setErrorMessage(null);
      parseFilenameHints(selectedFile.name);
    } else {
      setErrorMessage("Please upload a PDF document (.pdf).");
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setErrorMessage("Please select a PDF filing first.");
      return;
    }
    if (!company.trim()) {
      setErrorMessage("Please enter the company name.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const result = await uploadFiling(file, company.trim(), fiscalYear);
      setSuccessMessage(result.message);
      setTimeout(() => {
        onUploadSuccess(result.document);
        onClose();
        setFile(null);
        setCompany("");
        setSuccessMessage(null);
      }, 1200);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload processing failed.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-lg rounded-xl border border-zinc-800 bg-[#0c0c0e] p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-zinc-800/80">
          <div>
            <h2 className="text-base font-semibold text-white">Upload Financial Filing</h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              SEC 10-K, 10-Q, or 20-F PDF with automated line-item extraction
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="rounded-md p-1 text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {/* Dropzone */}
          {!file ? (
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`flex flex-col items-center justify-center rounded-lg border border-dashed p-7 text-center cursor-pointer transition-all ${
                dragActive
                  ? "border-white bg-zinc-900"
                  : "border-zinc-700 bg-zinc-950/60 hover:border-zinc-500 hover:bg-zinc-900/60"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) handleFile(e.target.files[0]);
                }}
                disabled={isLoading}
              />
              <UploadCloud className="h-8 w-8 text-zinc-400 mb-2" />
              <p className="text-xs font-medium text-white">
                Drag and drop filing PDF or <span className="underline text-zinc-300">browse</span>
              </p>
              <p className="text-[11px] text-zinc-400 mt-1">Supports digital SEC PDF filings</p>
            </div>
          ) : (
            /* Selected File Card */
            <div className="flex items-center justify-between rounded-lg border border-zinc-700 bg-zinc-900/80 p-3.5">
              <div className="flex items-center space-x-3 overflow-hidden">
                <FileText className="h-6 w-6 shrink-0 text-white" />
                <div className="overflow-hidden text-left">
                  <p className="text-xs font-medium text-white truncate max-w-[280px]">
                    {file.name}
                  </p>
                  <p className="text-[11px] text-zinc-400">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB • PDF Ready
                  </p>
                </div>
              </div>
              {!isLoading && (
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
                  title="Remove file"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          )}

          {/* Form Fields */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-zinc-300 mb-1">
                Company Name
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Apple, Microsoft, Nvidia"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                disabled={isLoading}
                className="w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-white placeholder-zinc-400 focus:border-zinc-500 focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-zinc-300 mb-1">
                Fiscal Year
              </label>
              <input
                type="number"
                required
                min={2000}
                max={2035}
                value={fiscalYear}
                onChange={(e) => setFiscalYear(Number(e.target.value))}
                disabled={isLoading}
                className="w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-white focus:border-zinc-500 focus:outline-none transition-colors"
              />
            </div>
          </div>

          {/* Status Alerts */}
          {errorMessage && (
            <div className="flex items-start space-x-2 rounded-md border border-red-900/50 bg-red-950/30 p-3 text-xs text-red-300">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-400 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="flex items-center space-x-2 rounded-md border border-zinc-700 bg-zinc-900 p-3 text-xs text-zinc-200">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-white" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Processing Indicator */}
          {isLoading && (
            <div className="flex items-center space-x-2.5 rounded-md border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-300">
              <Loader2 className="h-4 w-4 animate-spin text-white" />
              <span>Parsing document layout, extracting metrics & embedding chunks...</span>
            </div>
          )}

          {/* Action Footer */}
          <div className="flex items-center justify-end space-x-2.5 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="rounded-md px-3.5 py-1.5 text-xs font-medium text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !file || !company.trim()}
              className="flex items-center space-x-1.5 rounded-md bg-white px-4 py-1.5 text-xs font-medium text-black hover:bg-zinc-200 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <span>Ingest Report</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
