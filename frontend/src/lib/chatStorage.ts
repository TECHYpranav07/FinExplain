import { type QueryResponse } from "./api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  timestamp: string;
  content?: string;
  response?: QueryResponse;
  selectedProductIds?: string[];
  isPending?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  selectedProductIds: string[];
  messages: ChatMessage[];
}

function getStorageKey(userId?: string): string {
  const safeUser = userId ? userId.replace(/[^\w-]/g, "_") : "guest";
  return `finexplain_chat_sessions_${safeUser}_v1`;
}

function getActiveSessionKey(userId?: string): string {
  const safeUser = userId ? userId.replace(/[^\w-]/g, "_") : "guest";
  return `finexplain_active_session_${safeUser}_v1`;
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export function loadChatSessions(userId?: string): ChatSession[] {
  try {
    const raw = localStorage.getItem(getStorageKey(userId));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    console.error("[ChatStorage] Failed to load sessions:", err);
    return [];
  }
}

export function saveChatSessions(sessions: ChatSession[], userId?: string): void {
  try {
    localStorage.setItem(getStorageKey(userId), JSON.stringify(sessions));
  } catch (err) {
    console.error("[ChatStorage] Failed to save sessions:", err);
  }
}

export function getActiveSessionId(userId?: string): string | null {
  try {
    return localStorage.getItem(getActiveSessionKey(userId));
  } catch {
    return null;
  }
}

export function setActiveSessionId(id: string, userId?: string): void {
  try {
    localStorage.setItem(getActiveSessionKey(userId), id);
  } catch {}
}

export function createNewSession(selectedProductIds: string[] = [], userId?: string): ChatSession {
  const newSession: ChatSession = {
    id: generateId(),
    title: "New Conversation",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    selectedProductIds,
    messages: [],
  };

  const sessions = loadChatSessions(userId);
  const updated = [newSession, ...sessions];
  saveChatSessions(updated, userId);
  setActiveSessionId(newSession.id, userId);
  return newSession;
}

export function updateSession(session: ChatSession, userId?: string): void {
  const sessions = loadChatSessions(userId);
  const index = sessions.findIndex((s) => s.id === session.id);
  if (index >= 0) {
    sessions[index] = {
      ...session,
      updatedAt: new Date().toISOString(),
    };
  } else {
    sessions.unshift(session);
  }
  saveChatSessions(sessions, userId);
}

export function deleteSession(id: string, userId?: string): ChatSession[] {
  const sessions = loadChatSessions(userId).filter((s) => s.id !== id);
  saveChatSessions(sessions, userId);
  const activeId = getActiveSessionId(userId);
  if (activeId === id) {
    if (sessions.length > 0) {
      setActiveSessionId(sessions[0].id, userId);
    } else {
      localStorage.removeItem(getActiveSessionKey(userId));
    }
  }
  return sessions;
}

export function clearAllSessions(userId?: string): void {
  localStorage.removeItem(getStorageKey(userId));
  localStorage.removeItem(getActiveSessionKey(userId));
}

export function generateSessionTitle(firstPrompt: string): string {
  const clean = firstPrompt.replace(/[^\w\s₹$%.,?-]/gi, "").trim();
  if (clean.length <= 40) return clean;
  return clean.substring(0, 37) + "...";
}

