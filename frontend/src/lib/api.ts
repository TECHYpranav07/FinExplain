export interface Product {
  id: string;
  name: string;
  issuer: string;
  effective_date?: string;
  user_id?: string;
  created_at?: string;
}

export interface DocumentUploadResponse {
  status?: string;
  document_id?: string;
  task_id?: string;
  total_chunks?: number;
  chunks_count?: number;
  document_metadata?: Record<string, any>;
  message?: string;
}

export interface RiskFactor {
  category?: string;
  title?: string;
  description?: string;
  severity: "HIGH" | "MEDIUM" | "LOW" | "CRITICAL";
  impact?: string;
  source?: string;
}

export interface StructuredFact {
  field?: string;
  category?: string;
  value?: any;
  unit?: string;
  currency?: string;
  condition?: string;
  illustrative_only?: boolean;
  status?: "EXPLICIT" | "CONDITIONAL" | "PARTIAL" | "CONFLICTED" | "MIXED" | "NOT_SPECIFIED";
  source_document?: string;
  product_name?: string;
  page?: number;
  section?: string;
  source_text?: string;
  confidence?: number;
}

export interface MissingInformation {
  field?: string;
  category?: string;
  reason?: string;
  status?: string;
}

export interface CostDriver {
  field?: string;
  category?: string;
  value?: any;
  priority?: "HIGH" | "MEDIUM" | "LOW";
  condition?: string;
  clause?: string;
}

export interface Citation {
  document_name?: string;
  page_number?: number;
  page?: number;
  section_title?: string;
  section?: string;
  text?: string;
  score?: number;
  verified?: boolean;
}

export interface QueryResponse {
  answer: string;
  why_this_answer?: string;
  plain_language_explanation?: string;
  evidence_score?: number;
  confidence_score?: number;
  confidence_label?: string;
  evidence_status?: "EXPLICIT" | "CONDITIONAL" | "MIXED" | "NOT_SPECIFIED";
  claim_coverage?: number;
  risk_score?: number;
  risk_level?: "HIGH" | "MEDIUM" | "LOW";
  risk_factors?: RiskFactor[];
  key_facts?: StructuredFact[];
  missing_information?: MissingInformation[];
  questions_to_ask_provider?: string[];
  what_to_verify?: string[];
  conditions?: Array<StructuredFact | string>;
  citations?: Citation[];
  retrieved_chunks?: any[];
  conflicts?: any[];
  intent?: string;
  calculation_results?: any;
  hitl_required?: boolean;
  hitl_reason?: string;
  hitl_type?: "CONFLICT_REVIEW" | "RISK_ACCEPTANCE" | "DISCLOSURE_GAP" | "GENERAL";
  hitl_status?: "PENDING" | "APPROVED" | "REJECTED";
  hitl_reviewer_note?: string;
  hitl_resolved_at?: string;
}

export interface LoanReviewResponse {
  review_text?: string;
  review?: string | any;
  structured_facts?: StructuredFact[];
  missing_information?: MissingInformation[];
  cost_drivers?: CostDriver[];
  conflicts?: any[];
  risk_factors?: RiskFactor[];
  risk_score?: number;
  risk_level?: string;
  checklist?: ChecklistItem[];
}

export interface ChecklistItem {
  marker?: string;
  item?: string;
  title?: string;
  value?: string;
  category?: string;
  priority?: "HIGH" | "MEDIUM" | "LOW" | string;
  condition?: string;
  status?: string;
  action_guidance?: string;
  suggested_question?: string;
  evidence?: { document?: string; page?: number; section?: string; chunk_id?: string };
}

export interface BeforeConfirmationResponse {
  checklist_text?: string;
  checklist?: ChecklistItem[];
  summary?: {
    total_items?: number;
    verified_items?: number;
    caution_items?: number;
    missing_items?: number;
    conflict_items?: number;
    total_facts_reviewed?: number;
  };
  risk_factors?: RiskFactor[];
  cost_drivers?: CostDriver[];
  key_facts?: StructuredFact[];
  missing_information?: MissingInformation[];
  questions?: string[];
}

export interface ComparisonFieldItem {
  field: string;
  product_a?: { value?: any; unit?: string; condition?: string };
  product_b?: { value?: any; unit?: string; condition?: string };
  status_a?: string;
  status_b?: string;
  winner?: string;
  [key: string]: any;
}

export interface LoanCompareRequest {
  product_ids: string[];
  scenario?: {
    loan_amount?: number;
    tenure_months?: number;
    prepayment_month?: number;
    [key: string]: any;
  };
}

export interface LoanCompareResponse {
  comparison_text?: string;
  field_comparisons?: ComparisonFieldItem[];
  products?: Product[];
  summary?: {
    total_products?: number;
    comparison_complete?: boolean;
    comparison_summary?: string;
  };
  winner_summary?: {
    known_cost_a?: number;
    known_cost_b?: number;
  };
}

export interface HealthResponse {
  status: string;
  environment?: string;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role?: string;
  picture?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

const STORAGE_API_KEY = "finexplain_api_base_url";
const STORAGE_AUTH_TOKEN = "finexplain_auth_token";

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem(STORAGE_API_KEY);
    if (saved) return saved.replace(/\/+$/, "");
  }
  const envUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;
  if (envUrl) {
    return envUrl.replace(/\/+$/, "");
  }
  return typeof window !== "undefined" ? window.location.origin : "";
}

export function setApiBaseUrl(url: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_API_KEY, url.replace(/\/+$/, ""));
  }
}

export function getStoredToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem(STORAGE_AUTH_TOKEN);
  }
  return null;
}

export function setStoredToken(token: string | null): void {
  if (typeof window !== "undefined") {
    if (token) {
      localStorage.setItem(STORAGE_AUTH_TOKEN, token);
    } else {
      localStorage.removeItem(STORAGE_AUTH_TOKEN);
    }
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const base = getApiBaseUrl();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const token = getStoredToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(url, { ...options, headers });
  
  let data: any;
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      data = await res.json();
    } catch {
      data = { detail: "Invalid JSON response from server" };
    }
  } else {
    const text = await res.text();
    data = { detail: text || `HTTP ${res.status} ${res.statusText}` };
  }

  if (!res.ok) {
    throw new Error(data.detail || `Request failed with status ${res.status}`);
  }

  return data as T;
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  // Products
  listProducts: () => request<Product[]>("/api/v1/products/"),
  getProduct: (id: string) => request<Product>(`/api/v1/products/${id}`),
  createProduct: (data: Partial<Product>) =>
    request<Product>("/api/v1/products/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteProduct: (id: string) =>
    request<{ message: string }>(`/api/v1/products/${id}`, {
      method: "DELETE",
    }),

  // Documents
  uploadDocument: async (file: File, productId: string) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("product_id", productId);
    formData.append("use_async", "false");
    return request<DocumentUploadResponse>("/api/v1/documents/upload", {
      method: "POST",
      body: formData,
    });
  },
  listDocuments: () => request<any[]>("/api/v1/documents/"),
  deleteDocument: (id: string) =>
    request<{ message: string }>(`/api/v1/documents/${id}`, {
      method: "DELETE",
    }),

  // RAG Analysis & Q&A
  ask: (payload: { question: string; product_ids?: string[] }) =>
    request<QueryResponse>("/api/v1/queries/ask", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  review: (payload: { product_ids?: string[] }) =>
    request<LoanReviewResponse>("/api/v1/analysis/review", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  beforeConfirmation: (payload: { product_ids?: string[] }) =>
    request<BeforeConfirmationResponse>("/api/v1/analysis/before-confirmation", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  compare: (payload: LoanCompareRequest) =>
    request<LoanCompareResponse>("/api/v1/analysis/compare", {
      method: "POST",
      body: JSON.stringify(payload),
    }),


  // HITL & Feedback
  listHitlTasks: () => request<any[]>("/api/v1/hilt/tasks"),
  resolveHitlTask: (taskId: string, data: any) =>
    request<any>(`/api/v1/hilt/tasks/${taskId}/resolve`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  submitFeedback: (data: any) =>
    request<any>("/api/v1/feedback/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Auth
  login: (credentials: { email: string; password: string }) =>
    request<AuthResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    }),
  register: (data: { email: string; password: string; name?: string }) =>
    request<AuthResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  googleAuth: (data: { credential?: string; email?: string; name?: string; google_id?: string; picture?: string }) =>
    request<AuthResponse>("/api/v1/auth/google", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getMe: () => request<{ user: AuthUser }>("/api/v1/auth/me"),
};
