"use client";

import React, { useState } from "react";
import {
  FileSpreadsheet,
  Check,
  AlertCircle,
  ArrowUpRight,
} from "lucide-react";
import { CompanyFinancialSummary, RawMetric } from "@/types";
import { METRIC_CONFIG, formatCurrency } from "@/lib/formatters";

interface FinancialStatementsTableProps {
  financials: CompanyFinancialSummary;
  onInspectProvenance: (metricKey: string, rawMetric: RawMetric) => void;
}

export const FinancialStatementsTable: React.FC<FinancialStatementsTableProps> = ({
  financials,
  onInspectProvenance,
}) => {
  const [activeStatement, setActiveStatement] = useState<
    "income" | "balance" | "cash_flow"
  >("income");

  const { raw_metrics } = financials;

  const statementMetrics = Object.entries(METRIC_CONFIG).filter(
    ([, config]) => config.statement === activeStatement
  );

  return (
    <div className="rounded-lg border border-zinc-800 bg-[#0e0e11] overflow-hidden">
      {/* Table Header & Category Tabs */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-zinc-800 px-4 py-3 gap-3">
        <div className="flex items-center space-x-2">
          <FileSpreadsheet className="h-4 w-4 text-zinc-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-white">
            Primary Financial Statements
          </h3>
        </div>

        {/* Statement Switcher */}
        <div className="flex items-center rounded-md bg-zinc-950 p-0.5 border border-zinc-800 text-xs">
          <button
            onClick={() => setActiveStatement("income")}
            className={`rounded px-2.5 py-1 font-medium transition-colors ${
              activeStatement === "income"
                ? "bg-zinc-800 text-white"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            Income Statement
          </button>
          <button
            onClick={() => setActiveStatement("balance")}
            className={`rounded px-2.5 py-1 font-medium transition-colors ${
              activeStatement === "balance"
                ? "bg-zinc-800 text-white"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            Balance Sheet
          </button>
          <button
            onClick={() => setActiveStatement("cash_flow")}
            className={`rounded px-2.5 py-1 font-medium transition-colors ${
              activeStatement === "cash_flow"
                ? "bg-zinc-800 text-white"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            Cash Flows
          </button>
        </div>
      </div>

      {/* Table Body */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-zinc-800 bg-zinc-950/70 text-zinc-400 uppercase tracking-wider text-[10px]">
            <tr>
              <th className="px-4 py-2.5 font-medium">Line Item</th>
              <th className="px-4 py-2.5 font-medium text-right">Extracted Value</th>
              <th className="px-4 py-2.5 font-medium text-center">Unit</th>
              <th className="px-4 py-2.5 font-medium text-center">Provenance</th>
              <th className="px-4 py-2.5 font-medium text-center">Audit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/70">
            {statementMetrics.map(([key, config]) => {
              const raw = raw_metrics[key];
              const isPresent = !!raw;

              return (
                <tr
                  key={key}
                  className="hover:bg-zinc-900/50 transition-colors group"
                >
                  {/* Label */}
                  <td className="px-4 py-3">
                    <div className="font-medium text-zinc-200 group-hover:text-white">
                      {config.label}
                    </div>
                    <div className="text-[11px] text-zinc-400">
                      {config.description}
                    </div>
                  </td>

                  {/* Value */}
                  <td className="px-4 py-3 text-right font-mono font-medium text-white">
                    {isPresent ? (
                      formatCurrency(raw.value, config.isPerShare, raw.currency)
                    ) : (
                      <span className="text-zinc-400 font-sans text-xs">Not Reported</span>
                    )}
                  </td>

                  {/* Unit */}
                  <td className="px-4 py-3 text-center text-zinc-400 font-mono text-[11px]">
                    {isPresent ? raw.unit : "—"}
                  </td>

                  {/* Grounding & Provenance */}
                  <td className="px-4 py-3 text-center">
                    {isPresent ? (
                      <div className="inline-flex items-center space-x-1.5">
                        <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-300">
                          Pg. {raw.source_page}
                        </span>
                        {raw.verified ? (
                          <span
                            title="Verbatim match with source filing table"
                            className="inline-flex items-center space-x-0.5 text-zinc-300 text-[10px]"
                          >
                            <Check className="h-3 w-3 text-emerald-400" />
                            <span>Verified</span>
                          </span>
                        ) : raw.low_confidence ? (
                          <span
                            title="Flagged after verification retry"
                            className="inline-flex items-center space-x-0.5 text-amber-400 text-[10px]"
                          >
                            <AlertCircle className="h-3 w-3" />
                            <span>Flagged</span>
                          </span>
                        ) : null}
                      </div>
                    ) : (
                      <span className="text-zinc-400">—</span>
                    )}
                  </td>

                  {/* Inspect */}
                  <td className="px-4 py-3 text-center">
                    {isPresent ? (
                      <button
                        onClick={() => onInspectProvenance(key, raw)}
                        className="inline-flex items-center space-x-1 rounded bg-zinc-800 px-2 py-0.5 text-[10px] font-medium text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors"
                      >
                        <span>View</span>
                        <ArrowUpRight className="h-3 w-3" />
                      </button>
                    ) : (
                      <span className="text-zinc-400">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
