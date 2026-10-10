"use client";

import React, { useState } from "react";
import { GitCompare, CheckSquare, Square } from "lucide-react";
import { CompanyFinancialSummary, DocumentItem } from "@/types";
import { formatCurrency, formatPercent, formatRatio } from "@/lib/formatters";

interface MultiCompanyComparisonProps {
  documents: DocumentItem[];
  allSummaries: Record<number, CompanyFinancialSummary>;
  onFetchDocFinancials: (docId: number) => Promise<void>;
}

export const MultiCompanyComparison: React.FC<MultiCompanyComparisonProps> = ({
  documents,
  allSummaries,
  onFetchDocFinancials,
}) => {
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>(
    documents.slice(0, 3).map((d) => d.id)
  );

  const toggleDocSelection = async (id: number) => {
    if (selectedDocIds.includes(id)) {
      if (selectedDocIds.length > 1) {
        setSelectedDocIds(selectedDocIds.filter((docId) => docId !== id));
      }
    } else {
      setSelectedDocIds([...selectedDocIds, id]);
      if (!allSummaries[id]) {
        await onFetchDocFinancials(id);
      }
    }
  };

  const activeSummaries = selectedDocIds
    .map((id) => allSummaries[id])
    .filter(Boolean);

  const maxRevenue = Math.max(
    ...activeSummaries.map((s) => Number(s.raw_metrics.total_revenue?.value || 0)),
    1
  );

  return (
    <div className="space-y-4">
      {/* Header & Checkbox Selector */}
      <div className="rounded-lg border border-zinc-800 bg-[#0e0e11] p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-white">
              Peer Comparison Matrix
            </h3>
            <p className="text-[11px] text-zinc-400">
              Select 2 or more filings to benchmark quantitative performance
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {documents.map((doc) => {
              const isSelected = selectedDocIds.includes(doc.id);
              return (
                <button
                  key={doc.id}
                  onClick={() => toggleDocSelection(doc.id)}
                  className={`flex items-center space-x-1.5 rounded-md px-2.5 py-1 text-xs font-medium border transition-colors ${
                    isSelected
                      ? "border-zinc-600 bg-zinc-800 text-white"
                      : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:text-white"
                  }`}
                >
                  {isSelected ? (
                    <CheckSquare className="h-3 w-3 text-white" />
                  ) : (
                    <Square className="h-3 w-3 text-zinc-400" />
                  )}
                  <span>
                    {doc.company} (FY{doc.fiscal_year})
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {activeSummaries.length < 2 ? (
        <div className="rounded-lg border border-zinc-800 bg-[#0e0e11] p-8 text-center text-zinc-400 text-xs">
          Select at least 2 filings above to benchmark performance.
        </div>
      ) : (
        <>
          {/* Revenue Scale Bar Benchmark */}
          <div className="rounded-lg border border-zinc-800 bg-[#0e0e11] p-4">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-3">
              Normalized Revenue Scale Benchmark
            </h4>

            <div className="space-y-3">
              {activeSummaries.map((summary) => {
                const rev = Number(summary.raw_metrics.total_revenue?.value || 0);
                const barWidth = Math.max(Math.min((rev / maxRevenue) * 100, 100), 4);

                return (
                  <div key={summary.document_id} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-medium text-white">
                        {summary.company} (FY{summary.fiscal_year})
                      </span>
                      <span className="font-mono text-zinc-300">{formatCurrency(rev)}</span>
                    </div>

                    <div className="h-3 w-full rounded bg-zinc-950 border border-zinc-800 overflow-hidden">
                      <div
                        style={{ width: `${barWidth}%` }}
                        className="h-full bg-white transition-all duration-300"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Matrix Table */}
          <div className="rounded-lg border border-zinc-800 bg-[#0e0e11] overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-zinc-800 bg-zinc-950 text-zinc-400 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Core Metric</th>
                  {activeSummaries.map((s) => (
                    <th
                      key={s.document_id}
                      className="px-4 py-2.5 font-medium text-right text-white"
                    >
                      {s.company} (FY{s.fiscal_year})
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800 font-mono">
                <tr className="hover:bg-zinc-900/40">
                  <td className="px-4 py-2.5 font-sans font-medium text-zinc-300">
                    Total Revenue
                  </td>
                  {activeSummaries.map((s) => (
                    <td key={s.document_id} className="px-4 py-2.5 text-right text-white">
                      {formatCurrency(s.raw_metrics.total_revenue?.value)}
                    </td>
                  ))}
                </tr>

                <tr className="hover:bg-zinc-900/40">
                  <td className="px-4 py-2.5 font-sans font-medium text-zinc-300">
                    Gross Profit
                  </td>
                  {activeSummaries.map((s) => (
                    <td key={s.document_id} className="px-4 py-2.5 text-right text-white">
                      {formatCurrency(s.raw_metrics.gross_profit?.value)}
                    </td>
                  ))}
                </tr>

                <tr className="hover:bg-zinc-900/40">
                  <td className="px-4 py-2.5 font-sans font-medium text-zinc-300">
                    Operating Income (EBIT)
                  </td>
                  {activeSummaries.map((s) => (
                    <td key={s.document_id} className="px-4 py-2.5 text-right text-white">
                      {formatCurrency(s.raw_metrics.operating_income?.value)}
                    </td>
                  ))}
                </tr>

                <tr className="hover:bg-zinc-900/40">
                  <td className="px-4 py-2.5 font-sans font-medium text-zinc-300">
                    Net Income
                  </td>
                  {activeSummaries.map((s) => (
                    <td key={s.document_id} className="px-4 py-2.5 text-right text-white">
                      {formatCurrency(s.raw_metrics.net_income?.value)}
                    </td>
                  ))}
                </tr>

                <tr className="hover:bg-zinc-900/40">
                  <td className="px-4 py-2.5 font-sans font-medium text-zinc-300">
                    Free Cash Flow (FCF)
                  </td>
                  {activeSummaries.map((s) => (
                    <td key={s.document_id} className="px-4 py-2.5 text-right text-white">
                      {formatCurrency(s.ratios.free_cash_flow)}
                    </td>
                  ))}
                </tr>

                <tr className="hover:bg-zinc-900/40">
                  <td className="px-4 py-2.5 font-sans font-medium text-zinc-300">
                    Gross Margin (%)
                  </td>
                  {activeSummaries.map((s) => (
                    <td key={s.document_id} className="px-4 py-2.5 text-right text-zinc-200">
                      {formatPercent(s.ratios.gross_margin_pct)}
                    </td>
                  ))}
                </tr>

                <tr className="hover:bg-zinc-900/40">
                  <td className="px-4 py-2.5 font-sans font-medium text-zinc-300">
                    Operating Margin (%)
                  </td>
                  {activeSummaries.map((s) => (
                    <td key={s.document_id} className="px-4 py-2.5 text-right text-zinc-200">
                      {formatPercent(s.ratios.operating_margin_pct)}
                    </td>
                  ))}
                </tr>

                <tr className="hover:bg-zinc-900/40">
                  <td className="px-4 py-2.5 font-sans font-medium text-zinc-300">
                    Debt-to-Equity
                  </td>
                  {activeSummaries.map((s) => (
                    <td key={s.document_id} className="px-4 py-2.5 text-right text-zinc-200">
                      {formatRatio(s.ratios.debt_to_equity)}
                    </td>
                  ))}
                </tr>

                <tr className="hover:bg-zinc-900/40">
                  <td className="px-4 py-2.5 font-sans font-medium text-zinc-300">
                    Return on Equity (ROE %)
                  </td>
                  {activeSummaries.map((s) => (
                    <td key={s.document_id} className="px-4 py-2.5 text-right text-zinc-200">
                      {formatPercent(s.ratios.return_on_equity_pct)}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};
