"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import PageHeader from "@/components/PageHeader";
import Badge from "@/components/Badge";
import { api } from "@/lib/api";
import type { RAGMessage, RAGSession, RAGSource } from "@/lib/types";

/* ─────────────────────────── Source pill ─────────────────────────────── */

function SourceChip({ source }: { source: RAGSource }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1 rounded-md border border-indigo-800/40 bg-indigo-950/30 px-2 py-0.5 text-[10px] font-medium text-indigo-300 transition-colors hover:bg-indigo-900/40"
      >
        <svg
          className="h-3 w-3"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        {source.source}
        {source.page ? ` p.${source.page}` : ""}
      </button>
      {open && (
        <div className="absolute bottom-full left-0 z-50 mb-1 w-72 rounded-lg border border-zinc-700/60 bg-zinc-900 p-3 shadow-lg">
          <p className="text-[11px] leading-relaxed text-zinc-300">
            {source.snippet}
          </p>
          <div className="mt-1 text-[10px] text-zinc-500">
            Relevance: {Math.round(source.relevance * 100)}%
          </div>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────── Typing dots ─────────────────────────────── */

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      <span className="h-2 w-2 animate-bounce rounded-full bg-indigo-400 [animation-delay:0ms]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-indigo-400 [animation-delay:150ms]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-indigo-400 [animation-delay:300ms]" />
    </div>
  );
}

/* ═══════════════════════════ Main page ═══════════════════════════════ */

export default function DocChatPage() {
  // Session state
  const [sessions, setSessions] = useState<RAGSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<RAGMessage[]>([]);

  // UI state
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadInfo, setUploadInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Fetch sessions on mount ──────────────────────────────────────
  const fetchSessions = useCallback(async () => {
    try {
      const list = await api.ragListSessions();
      setSessions(list);
    } catch {
      /* ignore on cold start */
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // ── Load messages when session changes ───────────────────────────
  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      return;
    }
    (async () => {
      try {
        const msgs = await api.ragGetMessages(activeSessionId);
        setMessages(msgs);
      } catch {
        setMessages([]);
      }
    })();
  }, [activeSessionId]);

  // ── Auto-scroll ──────────────────────────────────────────────────
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // ── Create session ───────────────────────────────────────────────
  const handleNewChat = async () => {
    try {
      const res = await api.ragCreateSession();
      setActiveSessionId(res.session_id);
      setMessages([]);
      setUploadInfo(null);
      setError(null);
      await fetchSessions();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create session.");
    }
  };

  // ── Switch session ───────────────────────────────────────────────
  const handleSelectSession = async (id: string) => {
    setActiveSessionId(id);
    setUploadInfo(null);
    setError(null);
  };

  // ── Delete session ───────────────────────────────────────────────
  const handleDeleteSession = async (id: string) => {
    try {
      await api.ragDeleteSession(id);
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([]);
      }
      await fetchSessions();
    } catch {
      /* swallow */
    }
  };

  // ── Upload files ─────────────────────────────────────────────────
  const handleFileUpload = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0 || !activeSessionId) return;

    setUploading(true);
    setError(null);
    setUploadInfo(null);

    try {
      const files = Array.from(fileList);
      const res = await api.ragUploadFiles(activeSessionId, files);

      if (!res.success) {
        setError(res.errors?.join(", ") || "Upload failed.");
      } else {
        setUploadInfo(
          `Processed ${res.processed} file(s) → ${res.chunks} chunks indexed.`,
        );
        if (res.errors.length > 0) {
          setUploadInfo(
            (prev) => `${prev} Warnings: ${res.errors.join(", ")}`,
          );
        }
      }
      await fetchSessions();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // ── Ask question ─────────────────────────────────────────────────
  const handleAsk = async () => {
    const q = question.trim();
    if (!q || !activeSessionId || loading) return;

    // Optimistic update
    const userMsg: RAGMessage = {
      role: "user",
      content: q,
      sources: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setQuestion("");
    setLoading(true);
    setError(null);

    try {
      const res = await api.ragQuery({
        session_id: activeSessionId,
        question: q,
      });
      const assistantMsg: RAGMessage = {
        role: "assistant",
        content: res.answer,
        sources: res.sources,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to get an answer.");
    } finally {
      setLoading(false);
    }
  };

  // ── Active session info ──────────────────────────────────────────
  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return (
    <div className="flex h-[calc(100vh-120px)] min-h-[500px] gap-0 px-2 md:px-4">
      {/* ── Sidebar ────────────────────────────────────────────────── */}
      <aside
        className={`shrink-0 overflow-y-auto rounded-l-2xl border border-zinc-800/70 bg-zinc-900/80 backdrop-blur-sm transition-all ${
          sidebarOpen ? "w-64" : "w-0 border-0 overflow-hidden"
        }`}
      >
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-[12px] font-semibold uppercase tracking-widest text-zinc-500">
              Chats
            </h3>
            <button
              onClick={() => setSidebarOpen(false)}
              className="rounded-md p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 transition-colors md:hidden"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* New chat button */}
          <button
            onClick={handleNewChat}
            className="mb-4 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-zinc-700/60 bg-zinc-950/50 px-3 py-2.5 text-[12px] font-semibold text-zinc-300 transition-colors hover:border-indigo-500/40 hover:bg-indigo-950/20 hover:text-indigo-300"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 4v16m8-8H4"
              />
            </svg>
            New chat
          </button>

          {/* Session list */}
          <div className="space-y-1.5">
            {sessions.map((s) => (
              <div
                key={s.id}
                className={`group flex items-center gap-2 rounded-lg border px-3 py-2 text-[12px] transition-colors cursor-pointer ${
                  activeSessionId === s.id
                    ? "border-indigo-700/40 bg-indigo-950/30 text-indigo-200"
                    : "border-zinc-800/60 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-800/40 hover:text-zinc-200"
                }`}
                onClick={() => handleSelectSession(s.id)}
              >
                <svg
                  className="h-3.5 w-3.5 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
                <span className="flex-1 truncate">{s.name}</span>
                {s.document_count > 0 && (
                  <span className="rounded-full bg-zinc-800 px-1.5 py-0.5 text-[9px] font-bold text-zinc-400">
                    {s.document_count}
                  </span>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteSession(s.id);
                  }}
                  className="hidden rounded p-0.5 text-zinc-600 hover:bg-red-900/30 hover:text-red-400 group-hover:block transition-colors"
                  title="Delete session"
                >
                  <svg
                    className="h-3 w-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            ))}
            {sessions.length === 0 && (
              <p className="px-2 text-[11px] text-zinc-600">
                No chats yet. Create one to start.
              </p>
            )}
          </div>
        </div>
      </aside>

      {/* ── Main chat area ─────────────────────────────────────────── */}
      <div className="flex min-w-0 flex-1 flex-col rounded-r-2xl border border-l-0 border-zinc-800/70 bg-zinc-950/60 backdrop-blur-sm">
        {/* Header bar */}
        <div className="flex items-center gap-3 border-b border-zinc-800/60 px-5 py-3">
          {!sidebarOpen && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="rounded-md border border-zinc-700/60 p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
          )}
          <PageHeader
            title="DocChat"
            subtitle={
              activeSession
                ? `${activeSession.name} · ${activeSession.document_count} document(s)`
                : "Upload documents and chat with them using AI"
            }
          />
        </div>

        {!activeSessionId ? (
          /* ── Empty state ──────────────────────────────────────────── */
          <div className="flex flex-1 items-center justify-center">
            <div className="text-center space-y-4">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-zinc-800/60 bg-zinc-900/80">
                <svg
                  className="h-8 w-8 text-indigo-400/60"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                  />
                </svg>
              </div>
              <div>
                <h3 className="text-[15px] font-semibold text-zinc-200">
                  Start a conversation
                </h3>
                <p className="mt-1 text-[12px] text-zinc-500">
                  Create a new chat, upload your documents, and ask questions.
                </p>
              </div>
              <button
                onClick={handleNewChat}
                className="mx-auto rounded-xl bg-indigo-600 px-5 py-2.5 text-[13px] font-semibold text-white transition hover:bg-indigo-500"
              >
                New Chat
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* ── Upload bar ──────────────────────────────────────── */}
            <div className="border-b border-zinc-800/50 bg-zinc-900/40 px-5 py-3">
              <div className="flex flex-wrap items-center gap-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt"
                  multiple
                  onChange={(e) => handleFileUpload(e.target.files)}
                  className="hidden"
                  id="doc-chat-file-upload"
                />
                <label
                  htmlFor="doc-chat-file-upload"
                  className={`flex cursor-pointer items-center gap-2 rounded-xl border border-dashed px-4 py-2 text-[12px] font-medium transition-colors ${
                    uploading
                      ? "border-zinc-700 text-zinc-600 cursor-wait"
                      : "border-zinc-700/60 text-zinc-400 hover:border-indigo-500/40 hover:bg-indigo-950/20 hover:text-indigo-300"
                  }`}
                >
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                  {uploading ? "Processing…" : "Upload PDF / DOCX / TXT"}
                </label>
                {uploadInfo && (
                  <Badge tone="success">{uploadInfo}</Badge>
                )}
              </div>
            </div>

            {/* ── Messages ────────────────────────────────────────── */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {messages.length === 0 && !loading && (
                <div className="flex h-full items-center justify-center">
                  <p className="text-[13px] text-zinc-600">
                    Upload documents and ask your first question.
                  </p>
                </div>
              )}

              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      msg.role === "user"
                        ? "bg-indigo-600/80 text-white"
                        : "border border-zinc-800/60 bg-zinc-900/80 text-zinc-200"
                    }`}
                  >
                    <p className="whitespace-pre-line text-[13px] leading-[1.7]">
                      {msg.content}
                    </p>
                    {/* Source chips for assistant messages */}
                    {msg.role === "assistant" &&
                      msg.sources &&
                      msg.sources.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5 border-t border-zinc-700/40 pt-2">
                          <span className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mr-1">
                            Sources:
                          </span>
                          {msg.sources.map((src, si) => (
                            <SourceChip key={si} source={src} />
                          ))}
                        </div>
                      )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="rounded-2xl border border-zinc-800/60 bg-zinc-900/80">
                    <TypingIndicator />
                  </div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            {/* ── Input bar ───────────────────────────────────────── */}
            <div className="border-t border-zinc-800/60 bg-zinc-900/50 px-5 py-3">
              {error && (
                <div className="mb-2 rounded-lg border border-red-800/40 bg-red-950/30 px-3 py-2 text-[12px] text-red-300">
                  {error}
                </div>
              )}
              <div className="flex items-end gap-3">
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleAsk();
                    }
                  }}
                  placeholder="Ask about your documents…"
                  rows={1}
                  className="flex-1 resize-none rounded-xl border border-zinc-700/60 bg-zinc-950 px-4 py-2.5 text-[13px] font-medium text-zinc-200 placeholder:text-zinc-600 focus:border-indigo-500/60 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-colors"
                />
                <button
                  onClick={handleAsk}
                  disabled={!question.trim() || loading}
                  className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white transition hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <svg
                    className="h-5 w-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M13 5l7 7-7 7M5 5l7 7-7 7"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
