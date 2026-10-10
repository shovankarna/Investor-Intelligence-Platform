"use client";

import React from "react";
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Percent,
  Wallet,
  Scale,
  ShieldCheck,
  Award,
  Sparkles,
} from "lucide-react";
import { CompanyFinancialSummary, RawMetric } from "@/types";
import { formatCurrency, formatPercent, formatRatio } from "@/lib/formatters";

interface KpiCardsGridProps {
  financials: CompanyFinancialSummary;
  onSelectMetric?: (metricKey: string, rawMetric?: RawMetric) => void;
}

export const KpiCardsGrid: React.FC<KpiCardsGridProps> = ({
  financials,
  onSelectMetric,
}) => {
  const { raw_metrics, ratios, yoy_growth } = financials;

  const cards = [
    {
      key: "total_revenue",
      title: "Total Revenue",
      value: formatCurrency(raw_metrics.total_revenue?.value),
      yoy: yoy_growth?.total_revenue,
      icon: DollarSign,
      description: "Top-line gross recognized turnover",
      raw: raw_metrics.total_revenue,
    },
    {
      key: "net_income",
      title: "Net Income",
      value: formatCurrency(raw_metrics.net_income?.value),
      yoy: yoy_growth?.net_income,
      icon: Award,
      description: "Bottom-line net profit after taxes & expenses",
      raw: raw_metrics.net_income,
    },
    {
      key: "operating_cash_flow",
      title: "Operating Cash Flow",
      value: formatCurrency(raw_metrics.operating_cash_flow?.value),
      yoy: yoy_growth?.operating_cash_flow,
      icon: Wallet,
      description: "Cash generated directly from core operations",
      raw: raw_metrics.operating_cash_flow,
    },
    {
      key: "free_cash_flow",
      title: "Free Cash Flow (FCF)",
      value: formatCurrency(ratios.free_cash_flow),
      yoy: yoy_growth?.free_cash_flow,
      icon: Sparkles,
      description: "Operating Cash Flow minus CapEx (Pure Code Math)",
      isCalculated: true,
    },
    {
      key: "gross_margin_pct",
      title: "Gross Margin",
      value: formatPercent(ratios.gross_margin_pct),
      yoy: null,
      icon: Percent,
      description: "(Gross Profit / Total Revenue) × 100",
      isCalculated: true,
    },
    {
      key: "operating_margin_pct",
      title: "Operating Margin",
      value: formatPercent(ratios.operating_margin_pct),
      yoy: null,
      icon: Percent,
      description: "(Operating Income / Total Revenue) × 100",
      isCalculated: true,
    },
    {
      key: "debt_to_equity",
      title: "Debt-to-Equity",
      value: formatRatio(ratios.debt_to_equity),
      yoy: null,
      icon: Scale,
      description: "Total Liabilities / Stockholders' Equity",
      isCalculated: true,
    },
    {
      key: "return_on_equity_pct",
      title: "Return on Equity (ROE)",
      value: formatPercent(ratios.return_on_equity_pct),
      yoy: null,
      icon: ShieldCheck,
      description: "(Net Income / Stockholders' Equity) × 100",
      isCalculated: true,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => {
        const Icon = card.icon;
        const hasYoY = card.yoy !== null && card.yoy !== undefined;
        const isPositiveYoY = hasYoY && (card.yoy ?? 0) >= 0;

        return (
          <div
            key={card.key}
            onClick={() => onSelectMetric?.(card.key, card.raw)}
            className="group flex flex-col justify-between rounded-lg border border-zinc-800 bg-[#0e0e11] p-4 transition-colors hover:border-zinc-700 hover:bg-[#131317] cursor-pointer"
          >
            {/* Top row */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-zinc-400">
                {card.title}
              </span>
              <Icon className="h-3.5 w-3.5 text-zinc-400 group-hover:text-white transition-colors" />
            </div>

            {/* Middle: Value & YoY */}
            <div className="mt-3 flex items-baseline justify-between">
              <span className="text-xl font-bold tracking-tight text-white">
                {card.value}
              </span>

              {hasYoY && (
                <div
                  className={`flex items-center space-x-1 text-[11px] font-medium ${
                    isPositiveYoY ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  {isPositiveYoY ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : (
                    <TrendingDown className="h-3 w-3" />
                  )}
                  <span>{formatPercent(card.yoy)} YoY</span>
                </div>
              )}
            </div>

            {/* Bottom Info */}
            <div className="mt-2.5 flex items-center justify-between pt-2 border-t border-zinc-800/80 text-[10px] text-zinc-400">
              <span className="truncate">{card.description}</span>
              {card.raw?.verified && (
                <span className="rounded bg-zinc-800 px-1.5 py-0.2 text-[9px] text-zinc-300">
                  Verified
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
