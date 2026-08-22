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

const STORAGE_KEY = "finexplain_chat_sessions_v1";
const ACTIVE_SESSION_KEY = "finexplain_active_session_id_v1";

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export function loadChatSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    console.error("[ChatStorage] Failed to load sessions:", err);
    return [];
  }
}

export function saveChatSessions(sessions: ChatSession[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (err) {
    console.error("[ChatStorage] Failed to save sessions:", err);
  }
}

export function getActiveSessionId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_SESSION_KEY);
  } catch {
    return null;
  }
}

export function setActiveSessionId(id: string): void {
  try {
    localStorage.setItem(ACTIVE_SESSION_KEY, id);
  } catch {}
}

export function createNewSession(selectedProductIds: string[] = []): ChatSession {
  const newSession: ChatSession = {
    id: generateId(),
    title: "New Conversation",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    selectedProductIds,
    messages: [],
  };

  const sessions = loadChatSessions();
  const updated = [newSession, ...sessions];
  saveChatSessions(updated);
  setActiveSessionId(newSession.id);
  return newSession;
}

export function updateSession(session: ChatSession): void {
  const sessions = loadChatSessions();
  const index = sessions.findIndex((s) => s.id === session.id);
  if (index >= 0) {
    sessions[index] = {
      ...session,
      updatedAt: new Date().toISOString(),
    };
  } else {
    sessions.unshift(session);
  }
  saveChatSessions(sessions);
}

export function deleteSession(id: string): ChatSession[] {
  const sessions = loadChatSessions().filter((s) => s.id !== id);
  saveChatSessions(sessions);
  const activeId = getActiveSessionId();
  if (activeId === id) {
    if (sessions.length > 0) {
      setActiveSessionId(sessions[0].id);
    } else {
      localStorage.removeItem(ACTIVE_SESSION_KEY);
    }
  }
  return sessions;
}

export function clearAllSessions(): void {
  localStorage.removeItem(STORAGE_KEY);
  localStorage.removeItem(ACTIVE_SESSION_KEY);
}

export function generateSessionTitle(firstPrompt: string): string {
  const clean = firstPrompt.replace(/[^\w\s₹$%.,?-]/gi, "").trim();
  if (clean.length <= 40) return clean;
  return clean.substring(0, 37) + "...";
}
