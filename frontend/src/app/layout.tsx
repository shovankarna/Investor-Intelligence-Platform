import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Investor Intelligence Platform | Dual-Path RAG & Financial Analytics",
  description:
    "AI-powered financial statement analysis, ratio computation, and citation-backed conversational RAG for SEC 10-K, 10-Q, and 20-F filings.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark h-full antialiased">
      <body className="min-h-full flex flex-col bg-slate-950 text-slate-100 selection:bg-cyan-500 selection:text-slate-950">
        {children}
      </body>
    </html>
  );
}
