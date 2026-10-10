"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Upload,
  Calendar,
  Building2,
  FileCheck,
  Hash,
  AlertCircle,
  Loader2,
  Trash2,
} from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { UploadModal } from "@/components/UploadModal";
import { KpiCardsGrid } from "@/components/KpiCardsGrid";
import { FinancialStatementsTable } from "@/components/FinancialStatementsTable";
import { InteractiveFinancialCharts } from "@/components/InteractiveFinancialCharts";
import { MultiCompanyComparison } from "@/components/MultiCompanyComparison";
import { ChatAssistant } from "@/components/ChatAssistant";
import { ProvenanceModal } from "@/components/ProvenanceModal";
import {
  checkApiHealth,
  getDocuments,
  getDocumentFinancials,
  getCompanyHistory,
  deleteDocument,
  clearAllDocuments,
} from "@/lib/api";
import {
  CitationItem,
  CompanyFinancialSummary,
  DocumentItem,
  RawMetric,
} from "@/types";

export default function HomePage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [financials, setFinancials] = useState<CompanyFinancialSummary | null>(null);
  const [companyHistory, setCompanyHistory] = useState<CompanyFinancialSummary[]>([]);
  const [allSummaries, setAllSummaries] = useState<Record<number, CompanyFinancialSummary>>({});
  const [activeTab, setActiveTab] = useState<"overview" | "compare" | "chat">("overview");
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Provenance Modal state
  const [provenanceModal, setProvenanceModal] = useState<{
    isOpen: boolean;
    metricData?: { key: string; raw: RawMetric } | null;
    citationData?: CitationItem | null;
  }>({
    isOpen: false,
    metricData: null,
    citationData: null,
  });

  const loadInitialData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    const health = await checkApiHealth();
    setIsBackendHealthy(!!health);

    try {
      const docs = await getDocuments();
      setDocuments(docs);

      if (docs.length > 0) {
        setSelectedDocId(docs[0].id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load documents.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  const loadDocumentDetails = useCallback(async (docId: number) => {
    try {
      const summary = await getDocumentFinancials(docId);
      if (!summary) {
        setFinancials(null);
        return;
      }
      setFinancials(summary);
      setAllSummaries((prev) => ({ ...prev, [docId]: summary }));

      if (summary.company) {
        const history = await getCompanyHistory(summary.company);
        setCompanyHistory(history);
        const mapUpdate: Record<number, CompanyFinancialSummary> = {};
        history.forEach((h) => {
          mapUpdate[h.document_id] = h;
        });
        setAllSummaries((prev) => ({ ...prev, ...mapUpdate }));
      }
    } catch (err: unknown) {
      console.error("Error loading financials:", err);
    }
  }, []);

  useEffect(() => {
    if (selectedDocId) {
      loadDocumentDetails(selectedDocId);
    }
  }, [selectedDocId, loadDocumentDetails]);

  const handleSelectDocId = (id: number) => {
    setSelectedDocId(id);
  };

  const handleUploadSuccess = (newDoc: DocumentItem) => {
    setDocuments((prev) => [newDoc, ...prev.filter((d) => d.id !== newDoc.id)]);
    setSelectedDocId(newDoc.id);
  };

  const handleInspectMetric = (metricKey: string, rawMetric?: RawMetric) => {
    if (rawMetric) {
      setProvenanceModal({
        isOpen: true,
        metricData: { key: metricKey, raw: rawMetric },
        citationData: null,
      });
    }
  };

  const handleOpenCitation = (citation: CitationItem) => {
    setProvenanceModal({
      isOpen: true,
      metricData: null,
      citationData: citation,
    });
  };

  const handleDeleteDoc = async (docId: number) => {
    if (!confirm("Are you sure you want to delete this filing and all its parsed metrics and vectors?")) {
      return;
    }
    try {
      await deleteDocument(docId);
      const remaining = documents.filter((d) => d.id !== docId);
      setDocuments(remaining);
      if (remaining.length > 0) {
        setSelectedDocId(remaining[0].id);
      } else {
        setSelectedDocId(null);
        setFinancials(null);
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete filing.");
    }
  };

  const handleClearAll = async () => {
    if (!confirm("Are you sure you want to reset and clear ALL ingested filings, metrics, and vector chunks from the database?")) {
      return;
    }
    try {
      await clearAllDocuments();
      setDocuments([]);
      setSelectedDocId(null);
      setFinancials(null);
      setCompanyHistory([]);
      setAllSummaries({});
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to reset database.");
    }
  };

  const selectedDoc = documents.find((d) => d.id === selectedDocId) || null;

  return (
    <div className="flex min-h-screen flex-col bg-black text-white selection:bg-white selection:text-black">
      {/* Top Navbar */}
      <Navbar
        documents={documents}
        selectedDocId={selectedDocId}
        onSelectDocId={handleSelectDocId}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onOpenUpload={() => setIsUploadOpen(true)}
        onClearAll={handleClearAll}
        isBackendHealthy={isBackendHealthy}
      />

      {/* Main Container */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-5 sm:px-6">
        {/* Loading */}
        {isLoading && (
          <div className="flex min-h-[350px] flex-col items-center justify-center space-y-3">
            <Loader2 className="h-6 w-6 animate-spin text-white" />
            <p className="text-xs text-zinc-400">Loading workspace...</p>
          </div>
        )}

        {/* Backend Disconnected */}
        {!isLoading && errorMessage && (
          <div className="rounded-lg border border-red-900/40 bg-red-950/20 p-5 text-center space-y-2">
            <AlertCircle className="mx-auto h-6 w-6 text-red-400" />
            <h3 className="text-sm font-semibold text-white">Backend Offline</h3>
            <p className="text-xs text-zinc-400 max-w-md mx-auto">{errorMessage}</p>
            <button
              onClick={loadInitialData}
              className="mt-2 rounded-md bg-zinc-800 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-zinc-700 transition-colors"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !errorMessage && documents.length === 0 && (
          <div className="flex min-h-[400px] flex-col items-center justify-center rounded-lg border border-dashed border-zinc-800 bg-[#0a0a0c] p-8 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 text-white mb-3">
              <Upload className="h-5 w-5" />
            </div>
            <h2 className="text-sm font-semibold text-white">No Financial Filings Ingested Yet</h2>
            <p className="mt-1 max-w-sm text-xs text-zinc-400 leading-relaxed">
              Upload a corporate 10-K, 10-Q, or 20-F PDF report to begin automated layout parsing,
              metric extraction, calculated ratios, and citation RAG.
            </p>
            <button
              onClick={() => setIsUploadOpen(true)}
              className="mt-5 flex items-center space-x-1.5 rounded-md bg-white px-4 py-2 text-xs font-medium text-black hover:bg-zinc-200 transition-colors"
            >
              <Upload className="h-3.5 w-3.5" />
              <span>Upload Filing</span>
            </button>
          </div>
        )}

        {/* Populated State */}
        {!isLoading && !errorMessage && documents.length > 0 && (
          <div className="space-y-4">
            {/* Document Header Banner */}
            {selectedDoc && (
              <div className="rounded-lg border border-zinc-800 bg-[#0e0e11] p-3.5">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="flex items-center space-x-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-zinc-900 border border-zinc-800 text-white">
                      <Building2 className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <h1 className="text-sm font-bold text-white">{selectedDoc.company}</h1>
                        <span className="rounded bg-zinc-800 px-1.5 py-0.2 text-[10px] font-mono text-zinc-300">
                          {selectedDoc.form_type}
                        </span>
                        <span className="text-xs text-zinc-400">
                          FY{selectedDoc.fiscal_year}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-x-3 text-[11px] text-zinc-400 mt-0.5">
                        {selectedDoc.fiscal_year_end && (
                          <span className="flex items-center space-x-1">
                            <Calendar className="h-3 w-3 text-zinc-500" />
                            <span>FYE: {selectedDoc.fiscal_year_end}</span>
                          </span>
                        )}
                        <span className="flex items-center space-x-1">
                          <FileCheck className="h-3 w-3 text-zinc-500" />
                          <span>{selectedDoc.filename}</span>
                        </span>
                        <span className="font-mono text-[10px] text-zinc-500">
                          SHA: {selectedDoc.content_hash.slice(0, 10)}...
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 text-xs">
                    {financials && (
                      <div className="rounded border border-zinc-800 bg-zinc-950 px-2.5 py-1 text-[11px] text-zinc-300 font-mono">
                        {companyHistory.length || 1} Filing{companyHistory.length > 1 ? "s" : ""} Available
                      </div>
                    )}
                    <button
                      onClick={() => handleDeleteDoc(selectedDoc.id)}
                      className="flex items-center space-x-1 rounded border border-zinc-800 bg-zinc-950 px-2 py-1 text-[11px] text-zinc-400 hover:border-red-800 hover:bg-red-950/30 hover:text-red-300 transition-colors"
                      title="Delete this filing and reset its data"
                    >
                      <Trash2 className="h-3 w-3" />
                      <span>Delete</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 1: Overview & Statements */}
            {activeTab === "overview" && financials && (
              <div className="space-y-4">
                <KpiCardsGrid
                  financials={financials}
                  onSelectMetric={handleInspectMetric}
                />

                <InteractiveFinancialCharts
                  financials={financials}
                  history={companyHistory}
                />

                <FinancialStatementsTable
                  financials={financials}
                  onInspectProvenance={handleInspectMetric}
                />
              </div>
            )}

            {/* TAB 2: Multi-Company Compare */}
            {activeTab === "compare" && (
              <MultiCompanyComparison
                documents={documents}
                allSummaries={allSummaries}
                onFetchDocFinancials={loadDocumentDetails}
              />
            )}

            {/* TAB 3: Conversational RAG */}
            {activeTab === "chat" && (
              <ChatAssistant
                selectedDoc={selectedDoc}
                onOpenCitation={handleOpenCitation}
              />
            )}
          </div>
        )}
      </main>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />

      {/* Provenance Modal */}
      <ProvenanceModal
        isOpen={provenanceModal.isOpen}
        onClose={() =>
          setProvenanceModal({
            isOpen: false,
            metricData: null,
            citationData: null,
          })
        }
        metricData={provenanceModal.metricData}
        citationData={provenanceModal.citationData}
      />

      {/* Footer */}
      <footer className="mt-auto border-t border-zinc-900 bg-black py-3 text-xs text-zinc-500">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-1">
          <span>Investor Intelligence Platform</span>
          <span className="font-mono text-[10px]">Dual-Path RAG • Deterministic Math</span>
        </div>
      </footer>
    </div>
  );
}
