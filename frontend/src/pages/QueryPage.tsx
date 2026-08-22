import React, { useState, useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, type QueryResponse } from "@/lib/api";
import { ProductPicker } from "@/components/finex/ProductSelect";
import {
  type ChatSession,
  type ChatMessage,
  loadChatSessions,
  saveChatSessions,
  getActiveSessionId,
  setActiveSessionId,
  createNewSession,
  updateSession,
  deleteSession,
  clearAllSessions,
  generateSessionTitle,
} from "@/lib/chatStorage";
import { ChatSidebar } from "@/components/finex/ChatSidebar";
import { ChatMessageItem } from "@/components/finex/ChatMessageItem";
import {
  Send,
  Sparkles,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  Download,
  Trash2,
  Menu,
  X,
} from "lucide-react";

const QUICK_PROMPTS = [
  "What is the processing fee and APR calculation?",
  "What are the prepayment penalties and lock-in period?",
  "What happens if payment is delayed by 15 days?",
  "Calculate the total interest cost for ₹500,000 over 24 months at standard rate.",
  "Are there any hidden costs, insurance bundling, or reset clauses?",
];

export function QueryPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);
  const [showProductPicker, setShowProductPicker] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load sessions on mount
  useEffect(() => {
    const loaded = loadChatSessions();
    if (loaded.length > 0) {
      setSessions(loaded);
      const savedActiveId = getActiveSessionId();
      const validActive = loaded.find((s) => s.id === savedActiveId);
      if (validActive) {
        setActiveId(validActive.id);
        setSelectedProducts(validActive.selectedProductIds || []);
      } else {
        setActiveId(loaded[0].id);
        setSelectedProducts(loaded[0].selectedProductIds || []);
        setActiveSessionId(loaded[0].id);
      }
    } else {
      const initial = createNewSession();
      setSessions([initial]);
      setActiveId(initial.id);
    }
  }, []);

  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeSession?.messages, activeSession?.messages.length]);

  const askMutation = useMutation({
    mutationFn: async ({
      q,
      targetProducts,
    }: {
      q: string;
      targetProducts: string[];
    }) => {
      return api.ask({
        question: q,
        product_ids: targetProducts,
      });
    },
    onSuccess: (data: QueryResponse, variables) => {
      if (!activeSession) return;

      const userMsgId = `${Date.now()}-user`;
      const assistantMsgId = `${Date.now()}-assistant`;

      const userMessage: ChatMessage = {
        id: userMsgId,
        role: "user",
        timestamp: new Date().toISOString(),
        content: variables.q,
        selectedProductIds: variables.targetProducts,
      };

      const assistantMessage: ChatMessage = {
        id: assistantMsgId,
        role: "assistant",
        timestamp: new Date().toISOString(),
        response: data,
        selectedProductIds: variables.targetProducts,
      };

      // Remove any pending temporary message
      const cleanedMessages = activeSession.messages.filter((m) => !m.isPending);

      const updatedMessages = [...cleanedMessages, userMessage, assistantMessage];

      // Auto-title if it was the first query
      const newTitle =
        activeSession.title === "New Conversation" && activeSession.messages.length === 0
          ? generateSessionTitle(variables.q)
          : activeSession.title;

      const updatedSession: ChatSession = {
        ...activeSession,
        title: newTitle,
        selectedProductIds: variables.targetProducts,
        messages: updatedMessages,
        updatedAt: new Date().toISOString(),
      };

      updateSession(updatedSession);
      setSessions(loadChatSessions());
    },
    onError: (error: any) => {
      if (!activeSession) return;
      // Clear pending state
      const cleaned = activeSession.messages.filter((m) => !m.isPending);
      const updatedSession = { ...activeSession, messages: cleaned };
      updateSession(updatedSession);
      setSessions(loadChatSessions());
    },
  });

  const handleSend = (textToSend?: string) => {
    const queryText = (textToSend || question).trim();
    if (!queryText || askMutation.isPending) return;

    if (!activeSession) return;

    // Immediately insert optimistic pending state
    const pendingAssistantMessage: ChatMessage = {
      id: `pending-${Date.now()}`,
      role: "assistant",
      timestamp: new Date().toISOString(),
      isPending: true,
      selectedProductIds: selectedProducts,
    };

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      timestamp: new Date().toISOString(),
      content: queryText,
      selectedProductIds: selectedProducts,
    };

    const updatedSession: ChatSession = {
      ...activeSession,
      messages: [...activeSession.messages, userMessage, pendingAssistantMessage],
    };

    updateSession(updatedSession);
    setSessions(loadChatSessions());
    setQuestion("");

    // Execute query
    askMutation.mutate({
      q: queryText,
      targetProducts: selectedProducts,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    const newSession = createNewSession(selectedProducts);
    setSessions(loadChatSessions());
    setActiveId(newSession.id);
    setMobileSidebarOpen(false);
    setQuestion("");
  };

  const handleSelectSession = (id: string) => {
    setActiveId(id);
    setActiveSessionId(id);
    const target = sessions.find((s) => s.id === id);
    if (target && target.selectedProductIds) {
      setSelectedProducts(target.selectedProductIds);
    }
    setMobileSidebarOpen(false);
  };

  const handleDeleteSession = (id: string) => {
    const updated = deleteSession(id);
    setSessions(updated);
    const newActiveId = getActiveSessionId();
    if (newActiveId) {
      setActiveId(newActiveId);
    } else {
      handleNewChat();
    }
  };

  const handleClearAll = () => {
    if (window.confirm("Are you sure you want to delete all saved conversations?")) {
      clearAllSessions();
      handleNewChat();
    }
  };

  const handleRenameSession = (id: string, newTitle: string) => {
    const target = sessions.find((s) => s.id === id);
    if (target) {
      const updated = { ...target, title: newTitle };
      updateSession(updated);
      setSessions(loadChatSessions());
    }
  };

  const handleClearCurrentMessages = () => {
    if (!activeSession) return;
    const updated = { ...activeSession, messages: [] };
    updateSession(updated);
    setSessions(loadChatSessions());
  };

  const handleExportChat = () => {
    if (!activeSession || activeSession.messages.length === 0) return;
    const dataStr =
      "data:text/json;charset=utf-8," +
      encodeURIComponent(JSON.stringify(activeSession, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute(
      "download",
      `FinExplain_Audit_${activeSession.title.replace(/\s+/g, "_")}.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="max-w-7xl mx-auto flex flex-col md:flex-row gap-5 h-[calc(100vh-120px)]">
      {/* Mobile Sidebar Toggle */}
      <div className="md:hidden flex items-center justify-between bg-surface p-3 rounded-xl border border-white/10">
        <button
          type="button"
          onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)}
          className="flex items-center gap-2 text-xs font-semibold text-white"
        >
          {mobileSidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          <span>{activeSession?.title || "Conversations"}</span>
        </button>
        <button
          type="button"
          onClick={handleNewChat}
          className="text-xs bg-white text-black px-3 py-1.5 rounded-lg font-bold"
        >
          + New
        </button>
      </div>

      {/* Left Sidebar (Desktop & Mobile Drawer) */}
      <div
        className={`${
          mobileSidebarOpen ? "block" : "hidden"
        } md:block shrink-0 z-20 md:z-auto`}
      >
        <ChatSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onNewChat={handleNewChat}
          onDeleteSession={handleDeleteSession}
          onClearAll={handleClearAll}
          onRenameSession={handleRenameSession}
        />
      </div>

      {/* Main Conversational Window */}
      <main className="flex-1 flex flex-col h-full rounded-2xl border border-white/10 bg-surface overflow-hidden min-w-0">
        {/* Chat Header */}
        <header className="p-4 border-b border-white/10 bg-surface-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
          <div className="min-w-0">
            <h2 className="text-sm font-bold text-white truncate flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary-light shrink-0" />
              <span>{activeSession?.title || "New Conversation"}</span>
            </h2>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Evidence-First RAG • {activeSession?.messages.length || 0} turn
              {activeSession?.messages.length !== 1 ? "s" : ""}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowProductPicker(!showProductPicker)}
              className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 text-xs text-white/80 hover:bg-white/10 transition-colors"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              <span>
                {selectedProducts.length > 0
                  ? `${selectedProducts.length} Product${selectedProducts.length > 1 ? "s" : ""}`
                  : "All Products"}
              </span>
              {showProductPicker ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>

            {activeSession && activeSession.messages.length > 0 && (
              <>
                <button
                  type="button"
                  title="Export Chat"
                  onClick={handleExportChat}
                  className="p-1.5 rounded-lg border border-white/10 bg-white/5 text-white/60 hover:text-white transition-colors"
                >
                  <Download className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title="Clear Chat"
                  onClick={handleClearCurrentMessages}
                  className="p-1.5 rounded-lg border border-white/10 bg-white/5 text-white/60 hover:text-rose-400 transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </>
            )}
          </div>
        </header>

        {/* Collapsible Target Products Picker */}
        {showProductPicker && (
          <div className="p-4 border-b border-white/10 bg-surface-3 animate-in fade-in duration-200">
            <p className="text-xs font-semibold text-white mb-2">Target Loan Products for this Chat:</p>
            <ProductPicker
              selected={selectedProducts}
              onChange={setSelectedProducts}
              multiple={true}
            />
          </div>
        )}

        {/* Scrollable Message History Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 custom-scrollbar">
          {(!activeSession || activeSession.messages.length === 0) && (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto py-12 space-y-4 animate-in fade-in duration-300">
              <div className="h-12 w-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-white">
                <Sparkles className="h-6 w-6 text-primary-light" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Ask Evidence-First AI</h3>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  Ask multiple consecutive questions about interest rates, hidden fee structures, prepayment conditions, and floating rate benchmarks.
                </p>
              </div>

              <div className="w-full pt-4 space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground text-left">
                  Suggested Auditing Prompts:
                </p>
                <div className="grid grid-cols-1 gap-2 text-left">
                  {QUICK_PROMPTS.map((p, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleSend(p)}
                      className="rounded-xl border border-white/10 bg-surface-2 p-3 text-xs text-white/90 hover:bg-white/10 hover:border-white/20 transition-all text-left flex items-center justify-between gap-3 group"
                    >
                      <span className="leading-snug">{p}</span>
                      <Send className="h-3 w-3 text-muted-foreground group-hover:text-white opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeSession?.messages.map((msg) => (
            <ChatMessageItem
              key={msg.id}
              message={msg}
              onAskQuestion={(followUp) => handleSend(followUp)}
            />
          ))}

          <div ref={messagesEndRef} />
        </div>

        {/* Sticky Bottom Input Area */}
        <footer className="p-3 sm:p-4 border-t border-white/10 bg-surface-2 space-y-3 shrink-0">
          {/* Quick Preset Buttons (if active chat has messages) */}
          {activeSession && activeSession.messages.length > 0 && (
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 custom-scrollbar text-[11px]">
              <span className="text-muted-foreground uppercase tracking-wider font-semibold mr-1 text-[10px] shrink-0">
                Auditor Presets:
              </span>
              {QUICK_PROMPTS.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSend(p)}
                  disabled={askMutation.isPending}
                  className="shrink-0 rounded-full border border-white/10 bg-surface-3 px-3 py-1 text-white/70 hover:text-white hover:border-white/20 transition-colors disabled:opacity-40"
                >
                  {p}
                </button>
              ))}
            </div>
          )}

          {/* Textarea Input Container */}
          <div className="relative flex items-end gap-2 rounded-xl border border-white/15 bg-surface p-2 shadow-inner focus-within:border-white/30 transition-colors">
            <textarea
              ref={textareaRef}
              rows={2}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your loan document (e.g. What is the prepayment fee? Is APR disclosed?)..."
              disabled={askMutation.isPending}
              className="flex-1 bg-transparent px-2 py-1 text-xs sm:text-sm text-white placeholder:text-muted-foreground focus:outline-none resize-none leading-relaxed"
            />

            <button
              type="button"
              onClick={() => handleSend()}
              disabled={askMutation.isPending || !question.trim()}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white text-black hover:bg-white/90 disabled:opacity-30 transition-all shadow-sm"
              title="Send (Enter)"
            >
              {askMutation.isPending ? (
                <i className="fa-solid fa-spinner fa-spin text-xs" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>
          <div className="flex items-center justify-between px-1 text-[10px] text-muted-foreground">
            <span>Press <kbd className="bg-white/10 px-1 py-0.5 rounded text-white font-mono">Enter</kbd> to send, <kbd className="bg-white/10 px-1 py-0.5 rounded text-white font-mono">Shift+Enter</kbd> for new line</span>
            <span>All responses grounded with claim-level evidence</span>
          </div>
        </footer>
      </main>
    </div>
  );
}
