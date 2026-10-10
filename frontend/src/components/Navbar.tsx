"use client";

import React from "react";
import {
  TrendingUp,
  Upload,
  Bot,
  BarChart3,
  GitCompare,
  Activity,
  FileText,
  Trash2,
} from "lucide-react";
import { DocumentItem } from "@/types";

interface NavbarProps {
  documents: DocumentItem[];
  selectedDocId: number | null;
  onSelectDocId: (id: number) => void;
  activeTab: "overview" | "compare" | "chat";
  onSelectTab: (tab: "overview" | "compare" | "chat") => void;
  onOpenUpload: () => void;
  onClearAll?: () => void;
  isBackendHealthy: boolean | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  documents,
  selectedDocId,
  onSelectDocId,
  activeTab,
  onSelectTab,
  onOpenUpload,
  onClearAll,
  isBackendHealthy,
}) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-zinc-800/80 bg-black/95 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-2.5 sm:px-6">
        {/* Brand */}
        <div className="flex items-center space-x-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-white text-black">
            <TrendingUp className="h-4 w-4" />
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-sm font-semibold tracking-tight text-white">
              Investor Intelligence
            </span>
            <span className="hidden sm:inline text-[11px] text-zinc-400">
              RAG Analytics
            </span>
          </div>
        </div>

        {/* Center Nav Tabs */}
        <nav className="hidden md:flex items-center space-x-1 rounded-lg bg-zinc-950 p-1 border border-zinc-800">
          <button
            onClick={() => onSelectTab("overview")}
            className={`flex items-center space-x-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "overview"
                ? "bg-zinc-800 text-white shadow-sm"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <BarChart3 className="h-3.5 w-3.5" />
            <span>Overview & Statements</span>
          </button>
          <button
            onClick={() => onSelectTab("compare")}
            className={`flex items-center space-x-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "compare"
                ? "bg-zinc-800 text-white shadow-sm"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <GitCompare className="h-3.5 w-3.5" />
            <span>Peer Comparison</span>
          </button>
          <button
            onClick={() => onSelectTab("chat")}
            className={`flex items-center space-x-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "chat"
                ? "bg-zinc-800 text-white shadow-sm"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <Bot className="h-3.5 w-3.5" />
            <span>AI Copilot</span>
          </button>
        </nav>

        {/* Right Section */}
        <div className="flex items-center space-x-2.5">
          {/* Document Dropdown */}
          {documents.length > 0 && (
            <div className="flex items-center space-x-1.5">
              <FileText className="hidden sm:block h-3.5 w-3.5 text-zinc-400" />
              <select
                value={selectedDocId || ""}
                onChange={(e) => onSelectDocId(Number(e.target.value))}
                aria-label="Select filing"
                className="rounded-md border border-zinc-800 bg-zinc-950 px-2.5 py-1 text-xs text-zinc-200 focus:border-zinc-500 focus:outline-none transition-colors max-w-[170px] sm:max-w-[210px]"
              >
                {documents.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.company} (FY{doc.fiscal_year} • {doc.form_type})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Upload Button */}
          <button
            onClick={onOpenUpload}
            className="flex items-center space-x-1.5 rounded-md bg-white px-3 py-1 text-xs font-medium text-black hover:bg-zinc-200 transition-colors shadow-sm"
          >
            <Upload className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Upload Filing</span>
            <span className="sm:hidden">Upload</span>
          </button>

          {/* Reset All Data Button */}
          {documents.length > 0 && onClearAll && (
            <button
              onClick={onClearAll}
              className="flex items-center space-x-1 rounded-md border border-zinc-800 bg-zinc-950 px-2.5 py-1 text-xs text-zinc-400 hover:border-red-900 hover:bg-red-950/40 hover:text-red-300 transition-colors"
              title="Reset all filings and clear backend database"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Reset All</span>
            </button>
          )}

          {/* Health Status Indicator */}
          <div
            title={isBackendHealthy ? "Backend Connected" : "Backend Disconnected"}
            className="flex items-center space-x-1 rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1"
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                isBackendHealthy ? "bg-emerald-400" : "bg-red-400"
              }`}
            />
            <Activity className="h-3 w-3 text-zinc-400" />
          </div>
        </div>
      </div>

      {/* Mobile Tab Bar */}
      <div className="flex md:hidden border-t border-zinc-800 bg-black px-2 py-1 justify-around text-xs">
        <button
          onClick={() => onSelectTab("overview")}
          className={`px-3 py-1 rounded-md ${
            activeTab === "overview" ? "text-white font-medium" : "text-zinc-400"
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => onSelectTab("compare")}
          className={`px-3 py-1 rounded-md ${
            activeTab === "compare" ? "text-white font-medium" : "text-zinc-400"
          }`}
        >
          Compare
        </button>
        <button
          onClick={() => onSelectTab("chat")}
          className={`px-3 py-1 rounded-md ${
            activeTab === "chat" ? "text-white font-medium" : "text-zinc-400"
          }`}
        >
          Copilot
        </button>
      </div>
    </header>
  );
};
