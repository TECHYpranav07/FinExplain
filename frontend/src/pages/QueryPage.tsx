import React, { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api, type QueryResponse } from "@/lib/api";
import { ProductPicker } from "@/components/finex/ProductSelect";
import { useAuth } from "@/lib/authContext";
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
import { downloadPdf, type PdfSection } from "@/lib/pdfExporter";
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
  AlertTriangle,
  Check,
  Layers,
  HelpCircle,
} from "lucide-react";

const QUICK_PROMPTS = [
  "What is the processing fee and APR calculation?",
  "What are the prepayment penalties and lock-in period?",
  "What happens if payment is delayed by 15 days?",
  "Calculate the total interest cost for ₹500,000 over 24 months at standard rate.",
  "Are there any hidden costs, insurance bundling, or reset clauses?",
];

export function QueryPage() {
  const { user } = useAuth();
  const userId = user?.id;

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);
  const [showProductPicker, setShowProductPicker] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [productError, setProductError] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load sessions on mount or when user changes
  useEffect(() => {
    const loaded = loadChatSessions(userId);
    if (loaded.length > 0) {
      setSessions(loaded);
      const savedActiveId = getActiveSessionId(userId);
      const validActive = loaded.find((s) => s.id === savedActiveId);
      if (validActive) {
        setActiveId(validActive.id);
        setSelectedProducts(validActive.selectedProductIds || []);
      } else {
        setActiveId(loaded[0].id);
        setSelectedProducts(loaded[0].selectedProductIds || []);
        setActiveSessionId(loaded[0].id, userId);
      }
    } else {
      const initial = createNewSession([], userId);
      setSessions([initial]);
      setActiveId(initial.id);
    }
  }, [userId]);

  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];

  const [searchParams, setSearchParams] = useSearchParams();
  const initialQueryParam = searchParams.get("q");

  // Handle incoming query param from Navbar Global Search
  useEffect(() => {
    if (initialQueryParam && initialQueryParam.trim()) {
      setQuestion(initialQueryParam.trim());
      setSearchParams({}, { replace: true });
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
    }
  }, [initialQueryParam]);

  const handleProductChange = (newSelected: string[]) => {
    setSelectedProducts(newSelected);
    if (newSelected.length > 0) {
      setProductError(false);
    }
    if (activeSession) {
      const updated: ChatSession = {
        ...activeSession,
        selectedProductIds: newSelected,
        updatedAt: new Date().toISOString(),
      };
      updateSession(updated, userId);
      setSessions(loadChatSessions(userId));
    }
  };

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
      const hasUserMessage = cleanedMessages.some(
        (m) => m.role === "user" && m.content.trim() === variables.q.trim()
      );
      const updatedMessages = hasUserMessage
        ? [...cleanedMessages, assistantMessage]
        : [...cleanedMessages, userMessage, assistantMessage];

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

      updateSession(updatedSession, userId);
      setSessions(loadChatSessions(userId));
    },
    onError: (error: any) => {
      if (!activeSession) return;
      // Clear pending state
      const cleaned = activeSession.messages.filter((m) => !m.isPending);
      const updatedSession = { ...activeSession, messages: cleaned };
      updateSession(updatedSession, userId);
      setSessions(loadChatSessions(userId));
    },
  });

  const handleSend = (textToSend?: string) => {
    const queryText = (textToSend || question).trim();
    if (!queryText || askMutation.isPending) return;

    // Check if products are selected
    if (selectedProducts.length === 0) {
      setProductError(true);
      setShowProductPicker(true);
      return;
    }

    if (!activeSession) return;

    setProductError(false);

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

    updateSession(updatedSession, userId);
    setSessions(loadChatSessions(userId));
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
    const newSession = createNewSession(selectedProducts, userId);
    setSessions(loadChatSessions(userId));
    setActiveId(newSession.id);
    setMobileSidebarOpen(false);
    setQuestion("");
    setProductError(false);
  };

  const handleSelectSession = (id: string) => {
    setActiveId(id);
    setActiveSessionId(id, userId);
    const target = sessions.find((s) => s.id === id);
    if (target && target.selectedProductIds) {
      setSelectedProducts(target.selectedProductIds);
    }
    setMobileSidebarOpen(false);
    setProductError(false);
  };

  const handleDeleteSession = (id: string) => {
    const updated = deleteSession(id, userId);
    setSessions(updated);
    const newActiveId = getActiveSessionId(userId);
    if (newActiveId) {
      setActiveId(newActiveId);
    } else {
      handleNewChat();
    }
  };

  const handleClearAll = () => {
    if (window.confirm("Are you sure you want to delete all saved conversations?")) {
      clearAllSessions(userId);
      handleNewChat();
    }
  };

  const handleRenameSession = (id: string, newTitle: string) => {
    const target = sessions.find((s) => s.id === id);
    if (target) {
      const updated = { ...target, title: newTitle };
      updateSession(updated, userId);
      setSessions(loadChatSessions(userId));
    }
  };

  const handleClearCurrentMessages = () => {
    if (!activeSession) return;
    const updated = { ...activeSession, messages: [] };
    updateSession(updated, userId);
    setSessions(loadChatSessions(userId));
  };

  const handleResolveHitl = (
    messageId: string,
    action: "APPROVED" | "REJECTED",
    note?: string
  ) => {
    if (!activeSession) return;
    const updatedMessages = activeSession.messages.map((m) => {
      if (m.id === messageId && m.response) {
        return {
          ...m,
          response: {
            ...m.response,
            hitl_status: action,
            hitl_reviewer_note: note,
            hitl_resolved_at: new Date().toISOString(),
          },
        };
      }
      return m;
    });

    const updatedSession: ChatSession = {
      ...activeSession,
      messages: updatedMessages,
      updatedAt: new Date().toISOString(),
    };
    updateSession(updatedSession, userId);
    setSessions(loadChatSessions(userId));
  };

  const handleExportChat = () => {
    if (!activeSession || activeSession.messages.length === 0) return;

    const sections: PdfSection[] = [];

    activeSession.messages.forEach((msg, idx) => {
      if (msg.role === "user") {
        sections.push({
          title: `Inquiry #${Math.ceil((idx + 1) / 2)}: ${msg.content}`,
        });
      } else {
        const resp = msg.response;
        const answerText = resp?.answer || msg.content || "No response recorded.";
        const citations = resp?.citations || [];
        const facts = resp?.key_facts || [];

        const bulletPoints: string[] = [];
        if (citations.length > 0) {
          citations.forEach((c) => {
            bulletPoints.push(
              `Citation: [${c.document || "Loan Agreement"}, Page ${c.page || 1}${
                c.section ? `, Section: ${c.section}` : ""
              }] ${c.text ? `"${c.text.slice(0, 100)}..."` : ""}`
            );
          });
        }
        if (facts.length > 0) {
          facts.forEach((f) => {
            bulletPoints.push(
              `Fact: ${f.field || f.category} = ${f.value} ${f.unit || ""} (${
                f.status || "VERIFIED"
              })`
            );
          });
        }

        sections.push({
          subtitle: `FinExplain AI Precision Response (${
            msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : "Verified"
          })`,
          content: answerText,
          bulletPoints: bulletPoints.length > 0 ? bulletPoints : undefined,
        });
      }
    });

    downloadPdf({
      filename: `FinExplain_Chat_${activeSession.title.replace(/[^a-zA-Z0-9_-]/g, "_")}.pdf`,
      title: "FinExplain AI Precision Q&A Transcript",
      subtitle: `Audit Session: ${activeSession.title}`,
      metadata: {
        "Session ID": activeSession.id,
        "Total Messages": String(activeSession.messages.length),
        "Products Consulted":
          activeSession.selectedProductIds?.join(", ") || "Active Workspace Facility",
      },
      sections,
    });
  };

  return (
    <div className="w-full flex flex-col md:flex-row gap-5 h-[calc(100vh-130px)]">
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
            <div className="flex items-center gap-2 mt-0.5 text-[11px] text-muted-foreground">
              <span>Evidence-First RAG</span>
              <span>•</span>
              <span>
                {selectedProducts.length > 0 ? (
                  <span className="text-emerald-400 font-medium">
                    {selectedProducts.length} product{selectedProducts.length > 1 ? "s" : ""} selected
                  </span>
                ) : (
                  <span className="text-amber-400 font-medium flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" /> No product selected
                  </span>
                )}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowProductPicker(!showProductPicker)}
              className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all ${
                selectedProducts.length === 0
                  ? "border-amber-500/50 bg-amber-500/15 text-amber-300 animate-pulse shadow-sm"
                  : "border-white/10 bg-white/5 text-white hover:bg-white/10"
              }`}
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              <span>
                {selectedProducts.length === 0
                  ? "Select Product First"
                  : `${selectedProducts.length} Product${selectedProducts.length > 1 ? "s" : ""}`}
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
          <div className="p-4 border-b border-white/10 bg-surface-3 animate-in fade-in duration-200 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white">Target Loan Products for this Chat:</span>
              <span className="text-[11px] text-white/60">Select 1 or more products</span>
            </div>
            <ProductPicker
              selected={selectedProducts}
              onChange={handleProductChange}
              multiple={true}
            />
          </div>
        )}

        {/* Scrollable Message History Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 custom-scrollbar">
          {(!activeSession || activeSession.messages.length === 0) && (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-xl mx-auto py-8 space-y-5 animate-in fade-in duration-300">
              <div className="h-12 w-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-white">
                <Sparkles className="h-6 w-6 text-primary-light" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Ask Evidence-First AI</h3>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  Analyze loan agreements with claim-level citations, mathematical verification, and risk auditing.
                </p>
              </div>

              {/* Step 1: Prominent Product Selection Card */}
              <div
                className={`w-full rounded-2xl border p-4 sm:p-5 text-left transition-all ${
                  selectedProducts.length === 0
                    ? "border-amber-500/40 bg-amber-500/10 shadow-lg shadow-amber-500/5"
                    : "border-emerald-500/30 bg-emerald-500/5"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold ${
                        selectedProducts.length === 0
                          ? "bg-amber-400 text-black"
                          : "bg-emerald-400 text-black"
                      }`}
                    >
                      1
                    </span>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-white">
                      Step 1: Choose Target Loan Product(s)
                    </h4>
                  </div>
                  <span className="text-[10px] uppercase font-mono tracking-wider text-white/60">
                    {selectedProducts.length > 0 ? "Multi-Select Active" : "Action Required"}
                  </span>
                </div>

                <p className="text-xs text-white/70 leading-relaxed mb-3">
                  Select <strong className="text-white">1 product</strong> for a focused single-loan audit, or select <strong className="text-white">2+ products</strong> to compare terms and detect cross-document conflicts.
                </p>

                <div className="pt-1">
                  <ProductPicker
                    selected={selectedProducts}
                    onChange={handleProductChange}
                    multiple={true}
                  />
                </div>

                {selectedProducts.length === 0 ? (
                  <p className="text-[11px] text-amber-300 font-medium flex items-center gap-1.5 pt-3 mt-3 border-t border-amber-500/20">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    <span>Please select at least one product above before asking a question.</span>
                  </p>
                ) : (
                  <p className="text-[11px] text-emerald-400 font-medium flex items-center gap-1.5 pt-3 mt-3 border-t border-emerald-500/20">
                    <Check className="h-3.5 w-3.5 shrink-0" />
                    <span>{selectedProducts.length} product(s) selected. You can now submit inquiries below.</span>
                  </p>
                )}
              </div>

              {/* Step 2: Suggested Auditing Prompts */}
              <div className="w-full space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground text-left">
                  Step 2: Pick a Common Query or Type Your Own
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
              onResolveHitl={handleResolveHitl}
            />
          ))}

          <div ref={messagesEndRef} />
        </div>

        {/* Sticky Bottom Input Area */}
        <footer className="p-3 sm:p-4 border-t border-white/10 bg-surface-2 space-y-3 shrink-0">
          {/* Missing Product Warning Banner */}
          {productError && selectedProducts.length === 0 && (
            <div className="flex items-center justify-between rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300 animate-in fade-in duration-200">
              <span className="flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                <span>Please select at least one loan product above before submitting your query.</span>
              </span>
              <button
                type="button"
                onClick={() => setShowProductPicker(true)}
                className="underline font-semibold hover:text-white ml-2 shrink-0"
              >
                Choose Product
              </button>
            </div>
          )}

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
          <div
            className={`relative flex items-end gap-2 rounded-xl border bg-surface p-2 shadow-inner transition-colors ${
              productError && selectedProducts.length === 0
                ? "border-amber-500/50"
                : "border-white/15 focus-within:border-white/30"
            }`}
          >
            <textarea
              ref={textareaRef}
              rows={2}
              value={question}
              onChange={(e) => {
                setQuestion(e.target.value);
                if (selectedProducts.length > 0) setProductError(false);
              }}
              onKeyDown={handleKeyDown}
              placeholder={
                selectedProducts.length === 0
                  ? "Choose a product above first, then ask about loan terms, interest rates, reset clauses..."
                  : `Ask a question about ${
                      selectedProducts.length === 1 ? "this loan document" : "these loan products"
                    } (e.g. What is the prepayment fee? Is APR disclosed?)...`
              }
              disabled={askMutation.isPending}
              className="flex-1 bg-transparent px-2 py-1 text-xs sm:text-sm text-white placeholder:text-muted-foreground focus:outline-none resize-none leading-relaxed"
            />

            <button
              type="button"
              onClick={() => handleSend()}
              disabled={askMutation.isPending || !question.trim()}
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg font-bold transition-all shadow-sm ${
                selectedProducts.length === 0
                  ? "bg-amber-400 text-black hover:bg-amber-300"
                  : "bg-white text-black hover:bg-white/90 disabled:opacity-30"
              }`}
              title={selectedProducts.length === 0 ? "Select Product First" : "Send (Enter)"}
            >
              {askMutation.isPending ? (
                <i className="fa-solid fa-spinner fa-spin text-xs" />
              ) : selectedProducts.length === 0 ? (
                <AlertTriangle className="h-4 w-4" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>
          <div className="flex items-center justify-between px-1 text-[10px] text-muted-foreground">
            <span>
              Press <kbd className="bg-white/10 px-1 py-0.5 rounded text-white font-mono">Enter</kbd> to send, <kbd className="bg-white/10 px-1 py-0.5 rounded text-white font-mono">Shift+Enter</kbd> for new line
            </span>
            <span>
              {selectedProducts.length > 0 ? (
                <span className="text-emerald-400/90 font-medium">✓ {selectedProducts.length} Product{selectedProducts.length > 1 ? "s" : ""} Bound</span>
              ) : (
                <span className="text-amber-400 font-medium">⚠️ Select product first</span>
              )}
            </span>
          </div>
        </footer>
      </main>
    </div>
  );
}
