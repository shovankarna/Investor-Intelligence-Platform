"use client";

import React, { useState } from "react";
import { BarChart, PieChart, Layers } from "lucide-react";
import { CompanyFinancialSummary } from "@/types";
import { formatCurrency, formatPercent } from "@/lib/formatters";

interface InteractiveFinancialChartsProps {
  financials: CompanyFinancialSummary;
  history?: CompanyFinancialSummary[];
}

export const InteractiveFinancialCharts: React.FC<InteractiveFinancialChartsProps> = ({
  financials,
  history = [],
}) => {
  const [activeChart, setActiveChart] = useState<"trends" | "margins" | "cash_flow">("trends");

  const series = history.length > 0 ? history : [financials];
  const maxRevenue = Math.max(
    ...series.map((s) => Number(s.raw_metrics.total_revenue?.value || 0)),
    1
  );

  return (
    <div className="rounded-lg border border-zinc-800 bg-[#0e0e11] p-4">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-zinc-800 pb-3 gap-3">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-white">
            Visual Analytics
          </h3>
          <p className="text-[11px] text-zinc-400">
            {series.length > 1
              ? `Historical trajectory across ${series.length} fiscal years`
              : `Core performance metrics for FY${financials.fiscal_year}`}
          </p>
        </div>

        {/* View Switcher */}
        <div className="flex items-center rounded-md bg-zinc-950 p-0.5 border border-zinc-800 text-xs">
          <button
            onClick={() => setActiveChart("trends")}
            className={`flex items-center space-x-1 rounded px-2.5 py-1 font-medium transition-colors ${
              activeChart === "trends"
                ? "bg-zinc-800 text-white"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <BarChart className="h-3 w-3" />
            <span>Revenue & Profit</span>
          </button>
          <button
            onClick={() => setActiveChart("margins")}
            className={`flex items-center space-x-1 rounded px-2.5 py-1 font-medium transition-colors ${
              activeChart === "margins"
                ? "bg-zinc-800 text-white"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <PieChart className="h-3 w-3" />
            <span>Margins</span>
          </button>
          <button
            onClick={() => setActiveChart("cash_flow")}
            className={`flex items-center space-x-1 rounded px-2.5 py-1 font-medium transition-colors ${
              activeChart === "cash_flow"
                ? "bg-zinc-800 text-white"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <Layers className="h-3 w-3" />
            <span>Cash Flow</span>
          </button>
        </div>
      </div>

      {/* Chart Body */}
      <div className="mt-4">
        {/* VIEW 1: Revenue & Net Income Trends */}
        {activeChart === "trends" && (
          <div className="space-y-4">
            <div className="flex items-center justify-end space-x-4 text-[11px] text-zinc-400">
              <span className="flex items-center space-x-1.5">
                <span className="h-2 w-2 rounded-sm bg-zinc-400" />
                <span>Total Revenue</span>
              </span>
              <span className="flex items-center space-x-1.5">
                <span className="h-2 w-2 rounded-sm bg-white" />
                <span>Net Income</span>
              </span>
            </div>

            <div className="space-y-3">
              {series.map((item) => {
                const rev = Number(item.raw_metrics.total_revenue?.value || 0);
                const net = Number(item.raw_metrics.net_income?.value || 0);
                const revPct = Math.max(Math.min((rev / maxRevenue) * 100, 100), 4);
                const netPct = Math.max(Math.min((net / maxRevenue) * 100, 100), 2);

                return (
                  <div key={item.document_id} className="space-y-1">
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-zinc-300 font-sans">
                        {item.company} FY{item.fiscal_year}
                      </span>
                      <span className="text-zinc-400">
                        Rev: <strong className="text-white">{formatCurrency(rev)}</strong> | Net:{" "}
                        <strong className="text-white">{formatCurrency(net)}</strong>
                      </span>
                    </div>

                    <div className="relative h-4 w-full rounded bg-zinc-950 overflow-hidden border border-zinc-800">
                      <div
                        style={{ width: `${revPct}%` }}
                        className="absolute left-0 top-0 bottom-0 bg-zinc-600 transition-all duration-300"
                      />
                      <div
                        style={{ width: `${netPct}%` }}
                        className="absolute left-0 top-0 bottom-0 bg-white transition-all duration-300"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* VIEW 2: Margins Breakdown */}
        {activeChart === "margins" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3.5 text-center">
              <span className="text-[11px] text-zinc-400 font-medium">Gross Margin</span>
              <div className="mt-1.5 text-xl font-bold text-white">
                {formatPercent(financials.ratios.gross_margin_pct)}
              </div>
              <p className="mt-1 text-[10px] text-zinc-400">
                Retention after direct production costs
              </p>
            </div>

            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3.5 text-center">
              <span className="text-[11px] text-zinc-400 font-medium">Operating Margin</span>
              <div className="mt-1.5 text-xl font-bold text-white">
                {formatPercent(financials.ratios.operating_margin_pct)}
              </div>
              <p className="mt-1 text-[10px] text-zinc-400">
                Profitability before taxes and debt servicing
              </p>
            </div>

            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3.5 text-center">
              <span className="text-[11px] text-zinc-400 font-medium">Net Margin</span>
              <div className="mt-1.5 text-xl font-bold text-white">
                {formatPercent(financials.ratios.net_margin_pct)}
              </div>
              <p className="mt-1 text-[10px] text-zinc-400">
                Bottom-line net earnings conversion rate
              </p>
            </div>
          </div>
        )}

        {/* VIEW 3: Cash Flow vs CapEx */}
        {activeChart === "cash_flow" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3.5">
              <span className="text-[11px] text-zinc-400 font-medium">Operating Cash Flow</span>
              <div className="mt-1.5 text-lg font-bold text-white font-mono">
                {formatCurrency(financials.raw_metrics.operating_cash_flow?.value)}
              </div>
              <p className="mt-1 text-[10px] text-zinc-400">Direct core operational cash inflow</p>
            </div>

            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3.5">
              <span className="text-[11px] text-zinc-400 font-medium">Capital Expenditures (CapEx)</span>
              <div className="mt-1.5 text-lg font-bold text-white font-mono">
                {formatCurrency(financials.raw_metrics.capital_expenditures?.value)}
              </div>
              <p className="mt-1 text-[10px] text-zinc-400">Capital asset investments</p>
            </div>

            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3.5">
              <span className="text-[11px] text-zinc-400 font-medium">Free Cash Flow (FCF)</span>
              <div className="mt-1.5 text-lg font-bold text-white font-mono">
                {formatCurrency(financials.ratios.free_cash_flow)}
              </div>
              <p className="mt-1 text-[10px] text-zinc-400">Operating Cash Flow minus CapEx</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
