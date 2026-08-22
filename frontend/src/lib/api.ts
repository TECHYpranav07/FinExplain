export interface Product {
  id: string;
  name: string;
  issuer: string;
  effective_date?: string;
  user_id?: string;
  created_at?: string;
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
  status?: "EXPLICIT" | "CONDITIONAL" | "MIXED" | "NOT_SPECIFIED";
  source_document?: string;
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
  condition?: string;
  status?: string;
  evidence?: { document?: string; page?: number };
}

export interface BeforeConfirmationResponse {
  checklist_text?: string;
  checklist?: ChecklistItem[];
  risk_factors?: RiskFactor[];
  cost_drivers?: CostDriver[];
  key_facts?: StructuredFact[];
  missing_information?: MissingInformation[];
  questions?: string[];
}

export interface DocumentUploadResponse {
  message: string;
  chunks_count: number;
  document_id?: string;
  product_id?: string;
}

export interface HealthResponse {
  status: string;
  environment?: string;
}

const STORAGE_API_KEY = "finexplain_api_base_url";

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem(STORAGE_API_KEY);
    if (saved) return saved;
  }
  return import.meta.env.VITE_API_URL || window.location.origin;
}

export function setApiBaseUrl(url: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_API_KEY, url.replace(/\/+$/, ""));
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const base = getApiBaseUrl();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
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
};
