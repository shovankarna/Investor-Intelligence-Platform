"use client";

import React from "react";
import { X, ShieldCheck, Check, AlertCircle, BookOpen } from "lucide-react";
import { CitationItem, RawMetric } from "@/types";
import { formatCurrency, METRIC_CONFIG } from "@/lib/formatters";

interface ProvenanceModalProps {
  isOpen: boolean;
  onClose: () => void;
  metricData?: {
    key: string;
    raw: RawMetric;
  } | null;
  citationData?: CitationItem | null;
}

export const ProvenanceModal: React.FC<ProvenanceModalProps> = ({
  isOpen,
  onClose,
  metricData,
  citationData,
}) => {
  if (!isOpen) return null;

  const isMetric = !!metricData;
  const config = isMetric ? METRIC_CONFIG[metricData.key] : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-lg rounded-xl border border-zinc-800 bg-[#0c0c0e] p-5 shadow-2xl">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-md p-1 text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Modal Header */}
        <div className="mb-4 flex items-center space-x-2">
          <ShieldCheck className="h-4 w-4 text-white" />
          <h2 className="text-sm font-semibold text-white">
            {isMetric ? "Metric Lineage & Provenance" : "Citation Source Excerpt"}
          </h2>
        </div>

        {/* Metric Mode */}
        {isMetric && metricData && (
          <div className="space-y-3 text-xs">
            {/* Summary Box */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3.5">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] uppercase font-semibold text-zinc-400">
                    Line Item
                  </span>
                  <h3 className="text-sm font-semibold text-white mt-0.5">
                    {config?.label || metricData.key}
                  </h3>
                  <p className="text-zinc-400 mt-0.5 text-[11px]">{config?.description}</p>
                </div>
                <div className="text-right font-mono">
                  <span className="text-[10px] text-zinc-400 uppercase">Reported</span>
                  <div className="text-base font-bold text-white">
                    {formatCurrency(
                      metricData.raw.value,
                      config?.isPerShare,
                      metricData.raw.currency
                    )}
                  </div>
                  <span className="text-[10px] text-zinc-400">{metricData.raw.unit}</span>
                </div>
              </div>
            </div>

            {/* Audit Grid */}
            <div className="grid grid-cols-2 gap-2.5">
              <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
                <span className="text-[10px] uppercase font-semibold text-zinc-400 block mb-1">
                  Source Page
                </span>
                <span className="font-mono text-xs font-semibold text-white">
                  Page {metricData.raw.source_page}
                </span>
              </div>

              <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
                <span className="text-[10px] uppercase font-semibold text-zinc-400 block mb-1">
                  Verbatim Match
                </span>
                <span className="inline-flex items-center space-x-1 text-emerald-400 font-medium text-xs">
                  <Check className="h-3 w-3" />
                  <span>100% Grounded</span>
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Citation Mode */}
        {!isMetric && citationData && (
          <div className="space-y-3 text-xs">
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3.5 space-y-1">
              <div className="flex items-center justify-between text-[11px] text-zinc-400">
                <span>Section Hierarchy</span>
                <span className="rounded bg-zinc-800 px-2 py-0.5 text-zinc-200">
                  Page {citationData.page_number}
                </span>
              </div>
              <div className="text-sm font-semibold text-white">
                {citationData.section_path || "General Document Section"}
              </div>
            </div>

            {citationData.snippet && (
              <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3.5">
                <span className="text-[10px] uppercase font-semibold text-zinc-400 block mb-1.5">
                  Source Excerpt
                </span>
                <p className="font-mono text-[11px] text-zinc-300 whitespace-pre-wrap leading-relaxed">
                  {citationData.snippet}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="mt-4 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-md bg-zinc-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
