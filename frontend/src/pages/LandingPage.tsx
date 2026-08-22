import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/authContext";
import {
  FileText,
  ShieldCheck,
  AlertTriangle,
  Calculator,
  Search,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Sparkles,
  Layers,
  FileSpreadsheet,
  FileCheck2,
  ChevronRight,
  Info,
  Scale,
  Lock,
  User,
  LogOut,
} from "lucide-react";

const NAV_LINKS = [
  { label: "How It Works", href: "#how-it-works" },
  { label: "Why FinExplain", href: "#why-finexplain" },
  { label: "Features", href: "#features" },
  { label: "Examples", href: "#examples" },
  { label: "Scenarios", href: "#scenarios" },
];

const CAPABILITIES = [
  {
    num: "01",
    title: "Multi-Document Analysis",
    description: "Synthesizes clauses across KFS, sanction letters, contracts, and schedules without information silos.",
  },
  {
    num: "02",
    title: "Evidence-Based Answers",
    description: "Every answer is strictly grounded in retrieved evidence. If not in the document, we state it clearly.",
  },
  {
    num: "03",
    title: "Citation-Level Verification",
    description: "Claim-by-claim traceability with exact document names, page numbers, and clause sections.",
  },
  {
    num: "04",
    title: "Calculation Safety",
    description: "Deterministic financial math for EMIs, prepayment, and fees rather than unreliable LLM arithmetic.",
  },
];

const DOC_TYPES = [
  "Key Facts Statements (KFS)",
  "Loan Agreements",
  "Sanction Letters",
  "Repayment Schedules",
  "Terms & Conditions (MITC)",
  "Amendments & Addenda",
];

const FEATURE_CARDS = [
  {
    icon: FileCheck2,
    title: "Key Facts Statements (KFS)",
    desc: "Understand headline APR, interest rates, processing charges, and delayed-payment penalties.",
  },
  {
    icon: FileText,
    title: "Loan Agreements",
    desc: "Uncover covenants, default remedies, accelerated repayment clauses, and discretionary fees.",
  },
  {
    icon: FileSpreadsheet,
    title: "Repayment Schedules",
    desc: "Audit monthly EMI breakdowns, principal vs interest splits, and outstanding balance trajectories.",
  },
  {
    icon: Scale,
    title: "Cross-Document Conflicts",
    desc: "Detect discrepancies between summaries and agreements instead of silently averaging or guessing.",
  },
  {
    icon: Calculator,
    title: "Verified Calculations",
    desc: "Run deterministic mathematical formulas with verifiable inputs and zero hallucinated numbers.",
  },
  {
    icon: Search,
    title: "Claim-Level Citations",
    desc: "Inspect the exact source passage, page number, and section title for every factual statement.",
  },
];

const SCENARIOS = [
  { id: "01", question: "What is my total borrowing cost including all upfront fees?" },
  { id: "02", question: "What happens if I prepay or foreclose after 12 months?" },
  { id: "03", question: "What are the exact penal consequences if I miss two EMIs?" },
  { id: "04", question: "Does the interest rate in my KFS match the operative loan agreement?" },
  { id: "05", question: "Which conditional fees and administrative charges apply to my loan?" },
  { id: "06", question: "Show me exactly where the balance transfer restriction is stated." },
];

export function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"foreclosure" | "conflict">("conflict");
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <main id="top" className="relative min-h-screen overflow-x-hidden bg-black text-white selection:bg-white selection:text-black">
      {/* Background Video */}
      <video
        className="pointer-events-none fixed inset-0 h-full w-full object-cover opacity-60 z-0"
        autoPlay
        muted
        loop
        playsInline
        aria-hidden="true"
      >
        <source
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260809_012548_ef22562c-c0ae-4816-ad9d-f8922af4e6a7.mp4"
          type="video/mp4"
        />
      </video>
      <div
        className="pointer-events-none fixed inset-0 z-0"
        aria-hidden="true"
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0.40) 45%, rgba(0,0,0,0.92) 100%)",
        }}
      />

      <div className="relative z-10 flex flex-col max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* =========================================================================
            HEADER & NAVBAR
           ========================================================================= */}
        <header className="sticky top-4 z-50 mt-4 flex items-center justify-between gap-4 rounded-full border border-white/10 bg-black/60 px-5 py-3 backdrop-blur-xl shadow-2xl transition-all">
          <Link to="/" className="flex items-center gap-2.5 group">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white font-bold text-black text-xs shadow-[0_0_20px_rgba(255,255,255,0.4)] group-hover:scale-105 transition-transform">
              Fx
            </span>
            <span className="text-sm font-bold tracking-tight text-white">FinExplain</span>
          </Link>

          <nav className="hidden items-center gap-1 md:flex" aria-label="Primary Navigation">
            {NAV_LINKS.map((item) => (
              <a
                key={item.label}
                href={item.href}
                className="rounded-full px-3.5 py-1.5 text-xs font-medium text-white/70 hover:text-white hover:bg-white/5 transition-colors"
              >
                {item.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <div className="flex items-center gap-2.5">
                <Link
                  to="/app"
                  className="flex items-center gap-2 rounded-full bg-white text-black px-4 py-1.5 text-xs font-bold hover:bg-white/90 transition-all shadow-md"
                >
                  <span>Go to Console</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
                <button
                  type="button"
                  onClick={logout}
                  title="Sign Out"
                  className="flex h-8 w-8 items-center justify-center rounded-full border border-white/15 bg-white/5 text-white/70 hover:text-white hover:bg-white/10 transition-colors"
                >
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/auth"
                  className="rounded-full px-4 py-1.5 text-xs font-medium text-white/80 hover:text-white transition-colors"
                >
                  Sign in
                </Link>
                <Link
                  to="/auth"
                  className="rounded-full bg-white text-black px-4 py-1.5 text-xs font-bold hover:bg-white/90 transition-all shadow-[0_0_20px_rgba(255,255,255,0.3)]"
                >
                  Analyze Loan
                </Link>
              </div>
            )}

            {/* Mobile hamburger */}
            <button
              type="button"
              onClick={() => setMenuOpen(!menuOpen)}
              className="flex h-8 w-8 items-center justify-center rounded-full border border-white/15 bg-white/5 md:hidden"
            >
              <i className="fa-solid fa-bars text-xs" />
            </button>
          </div>
        </header>

        {/* =========================================================================
            SECTION 1: HERO SECTION
           ========================================================================= */}
        <section className="flex flex-col items-center justify-center pt-20 pb-16 sm:pt-28 sm:pb-24 text-center">
          {/* Evidence pill */}
          <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-1.5 text-xs font-medium text-white/90 backdrop-blur-md mb-8 shadow-sm">
            <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Evidence-First • Citation-Backed • Conflict-Aware</span>
          </div>

          <h1 className="max-w-4xl text-4xl font-extrabold tracking-tight text-white sm:text-6xl lg:text-7xl leading-[1.08]">
            Understand Your Loan <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-white/90 to-white/60">
              Before You Sign.
            </span>
          </h1>

          <p className="mt-6 max-w-2xl text-sm sm:text-base text-white/70 leading-relaxed">
            AI-powered loan document analysis built around <strong>verified evidence</strong> — not guesses.
            Upload your KFS, sanction letter, loan agreement, or repayment schedule to retrieve clauses, detect
            conflicts, and get plain-language answers with exact citations.
          </p>

          {/* Action CTAs */}
          <div className="mt-9 flex flex-wrap items-center justify-center gap-4">
            <Link
              to={isAuthenticated ? "/app/query" : "/auth"}
              className="inline-flex items-center gap-2.5 rounded-full bg-white px-8 py-3.5 text-sm font-bold text-black hover:bg-white/90 transition-all hover:scale-[1.02] shadow-[0_0_40px_rgba(255,255,255,0.35)]"
            >
              <span>Analyze My Loan</span>
              <ArrowRight className="h-4 w-4" />
            </Link>

            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-7 py-3.5 text-sm font-semibold text-white hover:bg-white/10 hover:border-white/25 transition-all"
            >
              <span>See How It Works</span>
              <ChevronRight className="h-4 w-4 text-white/60" />
            </a>
          </div>

          {/* Target Document Types Bar */}
          <div className="mt-16 w-full max-w-4xl border-t border-white/10 pt-6">
            <span className="text-[10px] uppercase tracking-[0.2em] font-semibold text-muted-foreground block mb-3">
              Built Specifically for Real Financial Documents
            </span>
            <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3">
              {DOC_TYPES.map((doc) => (
                <span
                  key={doc}
                  className="rounded-full border border-white/10 bg-surface/60 px-3.5 py-1 text-xs text-white/80 font-medium shadow-sm"
                >
                  {doc}
                </span>
              ))}
            </div>
          </div>

          {/* 4 Core Capabilities Grid (Replaces fake statistics) */}
          <div className="mt-16 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 w-full text-left">
            {CAPABILITIES.map((cap) => (
              <div
                key={cap.num}
                className="group rounded-2xl border border-white/10 bg-surface/40 p-5 backdrop-blur-md hover:border-white/25 hover:bg-surface/70 transition-all"
              >
                <span className="text-xs font-mono font-bold text-muted-foreground group-hover:text-white transition-colors">
                  {cap.num}
                </span>
                <h3 className="mt-2 text-sm font-bold text-white">{cap.title}</h3>
                <p className="mt-1.5 text-xs text-white/65 leading-relaxed">{cap.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* =========================================================================
            SECTION 2: HOW IT WORKS (VISUAL RAG WORKFLOW)
           ========================================================================= */}
        <section id="how-it-works" className="py-16 sm:py-24 border-t border-white/10">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Architecture & Traceability
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              From Loan Documents to Verified Answers
            </h2>
            <p className="text-xs sm:text-sm text-white/70">
              Unlike generic chatbot wrappers, FinExplain runs a deterministic pipeline with strict evidence scoring before any answer is synthesized.
            </p>
          </div>

          {/* Visual Architecture Flowchart */}
          <div className="mt-12 rounded-3xl border border-white/10 bg-surface/50 p-6 sm:p-10 backdrop-blur-xl shadow-2xl space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-center">
              {/* Step 1 */}
              <div className="rounded-2xl border border-white/10 bg-black/40 p-4 text-center space-y-2">
                <div className="flex h-10 w-10 mx-auto items-center justify-center rounded-xl bg-white/10 text-white font-bold text-sm">
                  1
                </div>
                <h4 className="text-xs font-bold text-white">Your Documents</h4>
                <p className="text-[11px] text-muted-foreground">KFS, Loan Agreements, Sanction Letters & Schedules</p>
              </div>

              {/* Arrow */}
              <div className="hidden md:flex justify-center text-white/30">
                <ChevronRight className="h-6 w-6" />
              </div>

              {/* Step 2 */}
              <div className="rounded-2xl border border-white/10 bg-black/40 p-4 text-center space-y-2">
                <div className="flex h-10 w-10 mx-auto items-center justify-center rounded-xl bg-white/10 text-white font-bold text-sm">
                  2
                </div>
                <h4 className="text-xs font-bold text-white">Hybrid Retrieval</h4>
                <p className="text-[11px] text-muted-foreground">BM25 + Dense Search & Reciprocal Rank Fusion</p>
              </div>

              {/* Arrow */}
              <div className="hidden md:flex justify-center text-white/30">
                <ChevronRight className="h-6 w-6" />
              </div>

              {/* Step 3 */}
              <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-center space-y-2">
                <div className="flex h-10 w-10 mx-auto items-center justify-center rounded-xl bg-amber-400 text-black font-bold text-sm shadow-md">
                  3
                </div>
                <h4 className="text-xs font-bold text-amber-300">Conflict Engine</h4>
                <p className="text-[11px] text-amber-200/70">Deterministic cross-document discrepancy detector</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-center">
              {/* Step 4 */}
              <div className="rounded-2xl border border-white/10 bg-black/40 p-4 text-center space-y-2">
                <div className="flex h-10 w-10 mx-auto items-center justify-center rounded-xl bg-white/10 text-white font-bold text-sm">
                  4
                </div>
                <h4 className="text-xs font-bold text-white">Evidence Scoring</h4>
                <p className="text-[11px] text-muted-foreground">Answerability threshold gate & PII sanitization</p>
              </div>

              {/* Arrow */}
              <div className="hidden md:flex justify-center text-white/30">
                <ChevronRight className="h-6 w-6" />
              </div>

              {/* Step 5 */}
              <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-center space-y-2">
                <div className="flex h-10 w-10 mx-auto items-center justify-center rounded-xl bg-emerald-400 text-black font-bold text-sm shadow-md">
                  5
                </div>
                <h4 className="text-xs font-bold text-emerald-300">Claim Verification</h4>
                <p className="text-[11px] text-emerald-200/70">Every numeric fact verified against source page & chunk</p>
              </div>

              {/* Arrow */}
              <div className="hidden md:flex justify-center text-white/30">
                <ChevronRight className="h-6 w-6" />
              </div>

              {/* Step 6 */}
              <div className="rounded-2xl border border-white/20 bg-white text-black p-4 text-center space-y-2 shadow-xl">
                <div className="flex h-10 w-10 mx-auto items-center justify-center rounded-xl bg-black text-white font-bold text-sm">
                  6
                </div>
                <h4 className="text-xs font-bold text-black">Verified Answer</h4>
                <p className="text-[11px] text-black/70">Clear explanation with exact citations and risk rating</p>
              </div>
            </div>
          </div>
        </section>

        {/* =========================================================================
            SECTION 3: WHY FINEXPLAIN? (ARCHITECTURAL COMPARISON)
           ========================================================================= */}
        <section id="why-finexplain" className="py-16 sm:py-24 border-t border-white/10">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Direct Comparison
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Evidence First. Explanation Second.
            </h2>
            <p className="text-xs sm:text-sm text-white/70">
              Most AI assistants focus solely on generating fluent answers. FinExplain focuses first on whether the available evidence actually supports that answer.
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left: Traditional PDF Chat */}
            <div className="rounded-3xl border border-rose-500/20 bg-rose-500/5 p-6 sm:p-8 space-y-5">
              <div className="flex items-center gap-2 text-rose-400">
                <XCircle className="h-5 w-5" />
                <h3 className="text-sm font-bold uppercase tracking-wider">Traditional "Chat With PDF"</h3>
              </div>

              <div className="space-y-3 text-xs text-white/80">
                <div className="flex items-start gap-2">
                  <span className="text-rose-400 font-bold">•</span>
                  <span><strong>Single-file blindspots:</strong> Cannot compare provisions across KFS, offer letters, and contracts simultaneously.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-rose-400 font-bold">•</span>
                  <span><strong>Silent contradiction resolution:</strong> If KFS says 3% and Agreement says 5%, generic LLMs pick one arbitrarily or average them.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-rose-400 font-bold">•</span>
                  <span><strong>LLM Arithmetic Errors:</strong> Uses probabilistic text generation to calculate compounding interest and fees.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-rose-400 font-bold">•</span>
                  <span><strong>Hallucinated Citations:</strong> Fabricates clause numbers to sound confident when evidence is absent.</span>
                </div>
              </div>
            </div>

            {/* Right: FinExplain Engine */}
            <div className="rounded-3xl border border-emerald-500/30 bg-emerald-500/5 p-6 sm:p-8 space-y-5 shadow-lg shadow-emerald-500/5">
              <div className="flex items-center gap-2 text-emerald-400">
                <CheckCircle2 className="h-5 w-5" />
                <h3 className="text-sm font-bold uppercase tracking-wider">FinExplain Evidence System</h3>
              </div>

              <div className="space-y-3 text-xs text-white/90">
                <div className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>Multi-Document Synthesis:</strong> Analyzes complete loan packages to ensure all terms align.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>Deterministic Conflict Surfacing:</strong> Highlights cross-document discrepancies with side-by-side tables and CONFLICTED badges.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>Python Math Offloading:</strong> EMI schedules and prepayment charges calculated via deterministic formulas.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>Verified Citations:</strong> Every material claim is mapped to an exact document, page number, and chunk.</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* =========================================================================
            SECTION 4: ASK YOUR LOAN ANYTHING (INTERACTIVE EXAMPLES)
           ========================================================================= */}
        <section id="examples" className="py-16 sm:py-24 border-t border-white/10">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Live Product Demo
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Ask Your Loan Anything
            </h2>
            <p className="text-xs sm:text-sm text-white/70">
              See how FinExplain handles complex conditional terms and cross-document discrepancies.
            </p>
          </div>

          <div className="mt-10 max-w-3xl mx-auto space-y-4">
            {/* Tab Selector */}
            <div className="flex rounded-2xl bg-surface p-1 border border-white/10 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setActiveTab("conflict")}
                className={`flex-1 py-2.5 rounded-xl transition-all ${
                  activeTab === "conflict"
                    ? "bg-white text-black shadow-md"
                    : "text-white/60 hover:text-white"
                }`}
              >
                ⚠️ Cross-Document Conflict (KFS vs Agreement)
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("foreclosure")}
                className={`flex-1 py-2.5 rounded-xl transition-all ${
                  activeTab === "foreclosure"
                    ? "bg-white text-black shadow-md"
                    : "text-white/60 hover:text-white"
                }`}
              >
                🟢 Conditional Prepayment Waiver
              </button>
            </div>

            {/* Interactive Showcase Card */}
            {activeTab === "conflict" ? (
              <div className="rounded-3xl border border-amber-500/30 bg-surface/80 p-6 sm:p-8 backdrop-blur-xl space-y-5 animate-in fade-in duration-300">
                <div className="space-y-1.5">
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono">
                    User Question:
                  </span>
                  <p className="text-sm font-semibold text-white">
                    "The KFS says 3% prepayment charge, but the loan agreement says 5%. Which one is correct?"
                  </p>
                </div>

                <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4 space-y-3 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-300 flex items-center gap-1.5">
                      <AlertTriangle className="h-4 w-4" />
                      <span>Conflict Detected Across Document Sources</span>
                    </span>
                    <span className="rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 px-2.5 py-0.5 font-mono text-[10px] font-bold">
                      CONFLICTED
                    </span>
                  </div>

                  <p className="text-white/90 leading-relaxed">
                    The provided documents contain materially inconsistent foreclosure-charge provisions. FinExplain surfaced the exact discrepancy rather than silently selecting one:
                  </p>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse border border-white/10 text-[11px]">
                      <thead>
                        <tr className="bg-white/5 text-white/70">
                          <th className="p-2 border border-white/10">Document</th>
                          <th className="p-2 border border-white/10">Page</th>
                          <th className="p-2 border border-white/10">Stated Foreclosure Charge</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td className="p-2 border border-white/10 font-mono">Key_Facts_Statement.pdf</td>
                          <td className="p-2 border border-white/10">Page 2</td>
                          <td className="p-2 border border-white/10 font-bold text-emerald-400">3.00%</td>
                        </tr>
                        <tr>
                          <td className="p-2 border border-white/10 font-mono">Loan_Agreement.pdf</td>
                          <td className="p-2 border border-white/10">Page 8 · Section 4.2</td>
                          <td className="p-2 border border-white/10 font-bold text-rose-400">5.00%</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <p className="text-white/70 italic text-[11px]">
                    Recommendation: Request a formal addendum or written clarification from the lender before signing.
                  </p>
                </div>
              </div>
            ) : (
              <div className="rounded-3xl border border-emerald-500/30 bg-surface/80 p-6 sm:p-8 backdrop-blur-xl space-y-5 animate-in fade-in duration-300">
                <div className="space-y-1.5">
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono">
                    User Question:
                  </span>
                  <p className="text-sm font-semibold text-white">
                    "What is the foreclosure charge on my retail loan?"
                  </p>
                </div>

                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 space-y-3 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-emerald-300 flex items-center gap-1.5">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Verified Contractual Term with Condition</span>
                    </span>
                    <span className="rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2.5 py-0.5 font-mono text-[10px] font-bold">
                      CONDITIONAL
                    </span>
                  </div>

                  <p className="text-white/90 leading-relaxed">
                    The loan agreement specifies a <strong>3.00% foreclosure charge</strong> calculated against the outstanding principal balance. However, this fee is subject to an active waiver condition:
                  </p>

                  <div className="rounded-xl bg-black/40 p-3 border border-white/10 font-mono text-[11px] text-white/80 space-y-1">
                    <div className="text-muted-foreground uppercase text-[10px]">Citation:</div>
                    <div>[Loan_Agreement.pdf · Page 12 · Section 7.3]</div>
                    <div className="text-emerald-300 italic">"Prepayment charge is completely waived after 12 consecutive EMI payments have been completed."</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* =========================================================================
            SECTION 5: BUILT FOR FINANCIAL DOCUMENTS (6-CARD GRID)
           ========================================================================= */}
        <section id="features" className="py-16 sm:py-24 border-t border-white/10">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Core Capabilities
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Built for Real Financial Documents
            </h2>
            <p className="text-xs sm:text-sm text-white/70">
              Purpose-built analyzers for retail loan agreements, credit sanction letters, and amortization schedules.
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURE_CARDS.map((f, i) => {
              const Icon = f.icon;
              return (
                <div
                  key={i}
                  className="rounded-3xl border border-white/10 bg-surface/50 p-6 backdrop-blur-md hover:border-white/25 hover:bg-surface/80 transition-all space-y-3"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10 text-white shadow-inner">
                    <Icon className="h-5 w-5 text-white/90" />
                  </div>
                  <h3 className="text-sm font-bold text-white">{f.title}</h3>
                  <p className="text-xs text-white/65 leading-relaxed">{f.desc}</p>
                </div>
              );
            })}
          </div>
        </section>

        {/* =========================================================================
            SECTION 6: REAL QUESTIONS. REAL EVIDENCE. (SCENARIOS)
           ========================================================================= */}
        <section id="scenarios" className="py-16 sm:py-24 border-t border-white/10">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Practical Audits
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Real Questions. Real Evidence.
            </h2>
            <p className="text-xs sm:text-sm text-white/70">
              Direct answers to the questions borrowers and auditors care about most.
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {SCENARIOS.map((s) => (
              <div
                key={s.id}
                className="group flex items-start gap-3.5 rounded-2xl border border-white/10 bg-surface/40 p-4 backdrop-blur-md hover:border-white/25 hover:bg-surface/70 transition-all"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/5 font-mono text-xs font-bold text-muted-foreground group-hover:text-white transition-colors">
                  {s.id}
                </span>
                <span className="text-xs font-semibold text-white/90 leading-snug group-hover:text-white transition-colors">
                  "{s.question}"
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* =========================================================================
            SECTION 7: RISK AWARENESS & LIMITATION GATE
           ========================================================================= */}
        <section className="py-16 sm:py-20 border-t border-white/10">
          <div className="rounded-3xl border border-white/15 bg-gradient-to-b from-surface/80 to-surface/30 p-8 sm:p-12 backdrop-blur-xl text-center space-y-6 max-w-4xl mx-auto shadow-2xl">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 text-white mx-auto shadow-inner">
              <Lock className="h-6 w-6" />
            </div>

            <div className="space-y-2">
              <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
                When FinExplain Can't Verify It, It Tells You.
              </h2>
              <p className="text-xs sm:text-sm text-white/70 max-w-xl mx-auto leading-relaxed">
                Financial agreements contain conditions, amendments, and gaps. We never pretend an unstated term does not exist.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono text-white/85">
              <div className="rounded-xl border border-white/10 bg-black/40 p-3.5">
                <span className="text-muted-foreground block mb-1">Strong Evidence</span>
                <span className="font-bold text-emerald-400">→ Verified Answer</span>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/40 p-3.5">
                <span className="text-muted-foreground block mb-1">Conflicting Documents</span>
                <span className="font-bold text-amber-400">→ Discrepancy Surfaced</span>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/40 p-3.5">
                <span className="text-muted-foreground block mb-1">Missing Info</span>
                <span className="font-bold text-rose-400">→ No Invented Numbers</span>
              </div>
            </div>

            <p className="text-xs text-white/60 font-semibold uppercase tracking-widest pt-2">
              No guessing • No fabricated citations • No hidden assumptions
            </p>
          </div>
        </section>

        {/* =========================================================================
            SECTION 8: FINAL CTA
           ========================================================================= */}
        <section className="py-16 text-center space-y-6">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Ready to Audit Your Loan Documents?
          </h2>
          <p className="text-xs sm:text-sm text-white/70 max-w-md mx-auto">
            Upload your documents now and get verifiable clause-level intelligence in seconds.
          </p>
          <div>
            <Link
              to={isAuthenticated ? "/app/query" : "/auth"}
              className="inline-flex items-center gap-2.5 rounded-full bg-white px-8 py-3.5 text-sm font-bold text-black hover:bg-white/90 transition-all hover:scale-[1.02] shadow-[0_0_40px_rgba(255,255,255,0.35)]"
            >
              <span>Analyze My Loan Now</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </section>

        {/* =========================================================================
            FOOTER
           ========================================================================= */}
        <footer className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 py-8 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white font-bold text-black text-[10px]">
              Fx
            </span>
            <span className="font-semibold text-white">FinExplain</span>
            <span>— Evidence-first loan document intelligence.</span>
          </div>

          <div className="flex items-center gap-6">
            <a href="mailto:contact@finexplain.ai" className="hover:text-white transition-colors">
              contact@finexplain.ai
            </a>
            <span>© {new Date().getFullYear()} FinExplain</span>
          </div>
        </footer>
      </div>

      {/* Mobile Drawer Menu */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            onClick={() => setMenuOpen(false)}
            className="absolute inset-0 bg-black/80 backdrop-blur-md"
          />
          <div className="absolute inset-x-4 top-4 rounded-3xl bg-surface border border-white/15 p-6 text-white shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <span className="font-bold text-sm">FinExplain</span>
              <button
                type="button"
                onClick={() => setMenuOpen(false)}
                className="p-1 rounded-lg text-white/60 hover:text-white"
              >
                <i className="fa-solid fa-xmark text-sm" />
              </button>
            </div>

            <nav className="flex flex-col gap-2 text-sm">
              {NAV_LINKS.map((item) => (
                <a
                  key={item.label}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  className="py-2 text-white/80 hover:text-white"
                >
                  {item.label}
                </a>
              ))}
            </nav>

            <div className="pt-2 border-t border-white/10">
              <Link
                to={isAuthenticated ? "/app" : "/auth"}
                onClick={() => setMenuOpen(false)}
                className="w-full flex items-center justify-center rounded-xl bg-white text-black py-2.5 font-bold text-xs shadow-md"
              >
                {isAuthenticated ? "Go to Console" : "Sign In / Analyze Loan"}
              </Link>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
