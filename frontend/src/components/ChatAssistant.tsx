"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Bot,
  Send,
  Sparkles,
  BookOpen,
  Database,
  FileText,
  Loader2,
} from "lucide-react";
import { ChatMessage, CitationItem, DocumentItem } from "@/types";
import { queryChatAssistant } from "@/lib/api";

interface ChatAssistantProps {
  selectedDoc: DocumentItem | null;
  onOpenCitation: (citation: CitationItem) => void;
}

export const ChatAssistant: React.FC<ChatAssistantProps> = ({
  selectedDoc,
  onOpenCitation,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-1",
      role: "assistant",
      content:
        "Welcome to the **Investor Intelligence Copilot**. I am a dual-path RAG assistant equipped with verified SQL financial line items and cross-encoder reranked narrative embeddings.\n\nAsk any financial ratio question, comparative lookup, or qualitative question regarding corporate filings.",
      query_type: "HYBRID",
      timestamp: "Just now",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async (queryText: string) => {
    if (!queryText.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: queryText.trim(),
      timestamp: "Just now",
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      const response = await queryChatAssistant(queryText.trim(), {
        documentId: selectedDoc?.id,
        company: selectedDoc?.company,
        fiscalYear: selectedDoc?.fiscal_year,
      });

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.answer,
        query_type: response.query_type,
        citations: response.citations,
        timestamp: "Just now",
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: unknown) {
      const errText =
        err instanceof Error ? err.message : "Failed to retrieve response from RAG service.";
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: `⚠️ **Error communicating with RAG assistant**: ${errText}`,
          timestamp: "Just now",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const samplePrompts = [
    `Why did operating profit margin change in ${selectedDoc?.fiscal_year || "recent"} filing?`,
    `What are the primary operational risk factors discussed in Item 1A?`,
    `Summarize Free Cash Flow vs Net Income conversion.`,
  ];

  return (
    <div className="flex flex-col h-[600px] rounded-lg border border-zinc-800 bg-[#0e0e11] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-3 bg-zinc-950">
        <div className="flex items-center space-x-2.5">
          <Bot className="h-4 w-4 text-white" />
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-white">
              Conversational RAG Analyst
            </h3>
            {selectedDoc && (
              <span className="text-[11px] text-zinc-400">
                Scope: {selectedDoc.company} (FY{selectedDoc.fiscal_year})
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg) => {
          const isUser = msg.role === "user";

          return (
            <div
              key={msg.id}
              className={`flex ${isUser ? "justify-end" : "justify-start"} animate-fade-in`}
            >
              <div
                className={`max-w-[85%] rounded-lg p-3.5 text-xs leading-relaxed ${
                  isUser
                    ? "bg-white text-black font-medium"
                    : "border border-zinc-800 bg-zinc-950 text-zinc-200"
                }`}
              >
                {!isUser && msg.query_type && (
                  <div className="mb-2 flex items-center justify-between border-b border-zinc-800 pb-1.5 text-[10px] text-zinc-400">
                    <span className="font-semibold text-white">AI Analyst</span>
                    <span className="rounded bg-zinc-800 px-1.5 py-0.2 font-mono text-[9px] text-zinc-300">
                      {msg.query_type}
                    </span>
                  </div>
                )}

                <div className="whitespace-pre-wrap font-sans">{msg.content}</div>

                {/* Citations */}
                {!isUser && msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-zinc-800">
                    <div className="mb-1.5 text-[10px] uppercase font-semibold text-zinc-400">
                      Citations ({msg.citations.length})
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.citations.map((cite, idx) => (
                        <button
                          key={idx}
                          onClick={() => onOpenCitation(cite)}
                          className="flex items-center space-x-1 rounded border border-zinc-700 bg-zinc-900 px-2 py-0.5 text-[10px] text-zinc-300 hover:border-zinc-500 hover:text-white transition-colors"
                        >
                          <BookOpen className="h-3 w-3 text-zinc-400" />
                          <span>Pg. {cite.page_number}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-center space-x-2 rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-white" />
              <span>Synthesizing response with pgvector & cross-encoder...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompts */}
      <div className="border-t border-zinc-800 bg-zinc-950 px-4 py-2">
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-0.5 text-[11px] no-scrollbar">
          <span className="shrink-0 text-zinc-400 flex items-center space-x-1">
            <Sparkles className="h-3 w-3 text-zinc-400" />
            <span>Prompt:</span>
          </span>
          {samplePrompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(prompt)}
              disabled={isLoading}
              className="shrink-0 rounded border border-zinc-800 bg-zinc-900 px-2.5 py-0.5 text-zinc-300 hover:border-zinc-600 hover:text-white transition-colors"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendMessage(inputValue);
        }}
        className="flex items-center space-x-2 border-t border-zinc-800 bg-black p-2.5"
      >
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Ask a question about this financial filing..."
          disabled={isLoading}
          className="flex-1 rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-white placeholder-zinc-400 focus:border-zinc-600 focus:outline-none transition-colors"
        />
        <button
          type="submit"
          disabled={isLoading || !inputValue.trim()}
          className="flex h-8 w-8 items-center justify-center rounded-md bg-white text-black hover:bg-zinc-200 disabled:opacity-40 transition-all"
        >
          <Send className="h-3.5 w-3.5" />
        </button>
      </form>
    </div>
  );
};
