import React, { useState } from "react";
import {
  type ChatSession,
} from "@/lib/chatStorage";
import { Plus, MessageSquare, Trash2, Edit2, Check, X, Search } from "lucide-react";

interface ChatSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  onClearAll: () => void;
  onRenameSession: (id: string, newTitle: string) => void;
  isOpen?: boolean;
  onCloseMobile?: () => void;
}

export function ChatSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onClearAll,
  onRenameSession,
}: ChatSidebarProps) {
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(search.toLowerCase())
  );

  const handleStartRename = (s: ChatSession, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(s.id);
    setEditTitle(s.title);
  };

  const handleSaveRename = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      onRenameSession(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  return (
    <aside className="w-full md:w-72 shrink-0 flex flex-col h-[calc(100vh-140px)] rounded-2xl border border-white/10 bg-surface p-3.5 space-y-3">
      {/* New Chat Button */}
      <button
        type="button"
        onClick={onNewChat}
        className="w-full flex items-center justify-center gap-2 rounded-xl bg-white px-4 py-2.5 text-xs font-bold text-black hover:bg-white/90 transition-all shadow-sm group"
      >
        <Plus className="h-4 w-4 transition-transform group-hover:rotate-90 duration-200" />
        <span>New Conversation</span>
      </button>

      {/* Search Input */}
      {sessions.length > 3 && (
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search conversations..."
            className="w-full rounded-lg border border-white/10 bg-surface-2 pl-8 pr-3 py-1.5 text-xs text-white placeholder:text-muted-foreground focus:border-white/20 focus:outline-none transition-colors"
          />
        </div>
      )}

      {/* Session List */}
      <div className="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
        {filteredSessions.length === 0 ? (
          <div className="py-8 text-center text-xs text-muted-foreground">
            {search ? "No conversations match your search." : "No saved conversations yet."}
          </div>
        ) : (
          filteredSessions.map((s) => {
            const isActive = s.id === activeSessionId;
            const isEditing = s.id === editingId;

            return (
              <div
                key={s.id}
                onClick={() => onSelectSession(s.id)}
                className={`group relative flex items-center justify-between gap-2 rounded-xl px-3 py-2.5 text-xs cursor-pointer transition-all ${
                  isActive
                    ? "bg-white/15 text-white font-medium shadow-sm border border-white/15"
                    : "text-white/70 hover:bg-white/5 hover:text-white border border-transparent"
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <MessageSquare
                    className={`h-3.5 w-3.5 shrink-0 ${
                      isActive ? "text-primary-light" : "text-muted-foreground"
                    }`}
                  />
                  {isEditing ? (
                    <div
                      className="flex items-center gap-1 flex-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        autoFocus
                        className="w-full bg-black/40 border border-white/20 rounded px-1.5 py-0.5 text-xs text-white focus:outline-none"
                      />
                      <button
                        type="button"
                        onClick={(e) => handleSaveRename(s.id, e)}
                        className="text-emerald-400 hover:text-emerald-300 p-0.5"
                      >
                        <Check className="h-3 w-3" />
                      </button>
                      <button
                        type="button"
                        onClick={handleCancelRename}
                        className="text-white/40 hover:text-white p-0.5"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ) : (
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs leading-snug">{s.title}</p>
                      <div className="flex items-center gap-2 mt-0.5 text-[10px] text-muted-foreground">
                        <span>{s.messages.length} msg{s.messages.length !== 1 ? "s" : ""}</span>
                        <span>•</span>
                        <span>
                          {new Date(s.updatedAt).toLocaleDateString([], {
                            month: "short",
                            day: "numeric",
                          })}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {!isEditing && (
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                    <button
                      type="button"
                      title="Rename"
                      onClick={(e) => handleStartRename(s, e)}
                      className="p-1 text-white/40 hover:text-white rounded transition-colors"
                    >
                      <Edit2 className="h-3 w-3" />
                    </button>
                    <button
                      type="button"
                      title="Delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(s.id);
                      }}
                      className="p-1 text-white/40 hover:text-rose-400 rounded transition-colors"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Clear All Footer */}
      {sessions.length > 0 && (
        <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px]">
          <span className="text-muted-foreground">
            {sessions.length} session{sessions.length !== 1 ? "s" : ""} saved
          </span>
          <button
            type="button"
            onClick={onClearAll}
            className="text-white/40 hover:text-rose-400 transition-colors flex items-center gap-1"
          >
            <Trash2 className="h-3 w-3" />
            <span>Clear all</span>
          </button>
        </div>
      )}
    </aside>
  );
}
