# FINEXPLAIN — COMPLETE FRONTEND DESIGN + IMPLEMENTATION PROMPT

You are building the complete frontend for **FinExplain**, an enterprise-grade, evidence-first AI platform for financial and loan document analysis.

The repository already contains the backend architecture and API definitions, but **there is currently no completed frontend application**.

Your job is to:

1. Study the existing repository structure and backend implementation.
2. Understand the actual FinExplain product and its backend APIs.
3. Build the complete frontend from scratch.
4. Use the supplied visual landing-page specification as the **primary visual design language**.
5. Extend that visual language consistently across the authenticated application and all required product pages.
6. Connect the frontend to the existing FastAPI backend.
7. Do not invent backend APIs when an existing API is available.
8. Do not modify or break the backend architecture.
9. Produce a polished, production-quality frontend rather than a simple prototype.

---

# 1. FIRST: UNDERSTAND THE EXISTING PROJECT

Before creating any frontend code, inspect the entire repository.

Pay particular attention to:

```text
backend/app/main.py

backend/app/api/
backend/app/api/routes/v1/

backend/app/core/
backend/app/db/
backend/app/external/
backend/app/ingestion/
backend/app/rag/
backend/app/tools/

backend/tests/
```

The existing backend contains functionality for:

```text
Document upload
Document ingestion
Hybrid retrieval
Evidence-first Q&A
Proactive document review
Before-confirmation analysis
Financial product management
Human-in-the-loop review
Feedback
Risk analysis
Deterministic financial calculations
Citation verification
Confidence scoring
```

The backend documentation describes the frontend as a modern Vanilla HTML5/CSS3/JavaScript dark-mode console with zero build step. Follow the actual repository implementation if it differs, but do not introduce a framework merely for convenience.

For this repository, the default frontend implementation should therefore be:

```text
HTML5
CSS3
Vanilla JavaScript
```

If the actual repository contains a newer explicit frontend stack, preserve that stack instead.

---

# 2. FRONTEND STACK DECISION RULE

Use this priority:

```text
1. Existing repository frontend stack
2. Explicit project documentation
3. Existing dependencies/configuration
4. If absolutely no frontend stack exists → Tailwind CSS fallback
```

Do NOT automatically create React.

Do NOT automatically create Next.js.

Do NOT automatically create Tailwind.

The supplied visual reference describes the desired design and behavior. It does not override the project's architecture.

For the current FinExplain project, use:

```text
Vanilla HTML
CSS
JavaScript
```

unless repository inspection proves otherwise.

---

# 3. PRODUCT UNDERSTANDING

FinExplain is NOT a generic chatbot.

It is an:

**Evidence-First AI system for financial and loan decisions.**

The frontend must clearly communicate that the system provides:

- Evidence-first verification
- Deterministic financial calculations
- Claim-level citations
- Conflict detection
- Missing-information detection
- Risk scoring
- Confidence scoring
- Proactive loan agreement analysis
- Before-confirmation checklists
- Financial product comparison
- Human-in-the-loop review
- Grounded AI question answering

Do not design it like a generic ChatGPT clone.

The UI should feel like:

```text
Enterprise AI
+
Financial Intelligence
+
Document Intelligence
+
Auditability
+
Evidence
+
Risk Analysis
```

---

# 4. DESIGN DIRECTION

Use the supplied landing-page design specification as the **visual source of truth**.

The overall visual language must be:

```text
Black / near-black
White typography
Muted gray secondary text
Soft dark translucent surfaces
Subtle borders
Soft shadows
Retro dot-matrix display typography
Modern Inter UI typography
Minimal futuristic enterprise aesthetic
```

The landing page must retain the supplied:

```text
Full-viewport video background
Circular brand logo
White navigation pill
Dark Sign In pill
Enterprise trust indicators
Retro dot-matrix headline
White CTA
Four bottom metrics
Mobile hamburger menu
```

However, the **application console must NOT literally copy the landing page layout**.

Instead, use the same:

```text
Typography
Color system
Spacing philosophy
Rounded geometry
Border treatment
Motion language
Logo treatment
Dark futuristic aesthetic
```

to create a practical enterprise application.

---

# 5. GLOBAL DESIGN SYSTEM

Create a reusable design system.

Use these core variables:

```css
--bg: #000000;
--surface: #111111;
--surface-2: #171717;
--surface-3: #202020;

--text: #ffffff;
--muted: #8e8e8e;

--border: rgba(255,255,255,0.12);
--border-strong: rgba(255,255,255,0.22);

--pill-dark: #28282a;

--success: #7ee787;
--warning: #f2cc60;
--danger: #ff7b72;

--font-sans:
    "Inter",
    "Segoe UI",
    system-ui,
    sans-serif;

--font-display:
    "BubbledotICG-FinePos",
    "Geist Pixel Circle",
    monospace;
```

Do not overuse colors.

Risk states may use restrained semantic colors, but the overall application should remain monochrome/dark.

---

# 6. REQUIRED FONTS

Load Inter:

```html
<link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap"
    rel="stylesheet"
/>
```

Load:

```html
<link
    href="https://db.onlinewebfonts.com/c/8cb707a9b8a73f8a7403336b861c3074?family=BubbledotICG-FinePos"
    rel="stylesheet"
/>
```

Use the exact family:

```text
BubbledotICG-FinePos
```

Do NOT substitute another Bubbledot font.

Use the local fallback:

```text
fonts/GeistPixel-Circle.woff2
```

with:

```css
@font-face {
    font-family: "Geist Pixel Circle";
    src: url("./fonts/GeistPixel-Circle.woff2")
         format("woff2");
    font-weight: 400;
    font-display: swap;
}
```

Load Font Awesome 6.5.2 using the supplied CDN and integrity hash.

---

# 7. FRONTEND INFORMATION ARCHITECTURE

Create the following application structure.

## Public pages

```text
/
    Landing page

/app
    Main application dashboard

/app/documents
    Document library

/app/documents/:id
    Document detail / analysis workspace

/app/query
    Evidence-first AI Q&A

/app/review
    Proactive document review

/app/before-confirmation
    Before You Confirm checklist

/app/products
    Financial products

/app/products/:id
    Product detail

/app/compare
    Product / loan comparison

/app/hitl
    Human-in-the-loop review queue

/app/feedback
    Feedback

/app/settings
    Application settings
```

If the backend does not currently expose a specific operation required by one of these pages, create the UI structure but do not invent a fake API implementation.

Clearly distinguish:

```text
UI ready
```

from:

```text
API connected
```

where necessary.

---

# 8. LANDING PAGE

The landing page must follow the supplied specification extremely closely.

## Background

Use this exact CloudFront video:

```text
https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260809_012548_ef22562c-c0ae-4816-ad9d-f8922af4e6a7.mp4
```

Use:

```html
<video
    autoplay
    muted
    loop
    playsinline
>
```

with:

```css
position: absolute;
inset: 0;
width: 100%;
height: 100%;
object-fit: cover;
pointer-events: none;
z-index: 0;
```

---

# 9. LANDING PAGE HEADER

Desktop:

```text
[FinExplain Logo] [Home Product Case Studies Contact] [Sign in]
```

Logo:

```text
assets/logo.webp
```

Circular white background.

Soft shadow:

```css
0 4px 14px rgba(0, 0, 0, 0.16)
```

Navigation is a white pill.

Active Home state has three black dots.

Sign in is a dark pill.

Mobile:

```text
[Logo]                         [☰]
```

Use a circular 48×48 burger.

Opening it creates:

```text
dark blurred overlay
+
white rounded menu sheet
```

Menu:

```text
Home
Product
Case Studies
Contact
Sign in
```

Support:

```text
Escape
overlay click
link click
resize >720px
aria-expanded
body.menu-open
```

---

# 10. LANDING HERO

Exact headline:

```text
Intelligence
Designed To Evolve
```

Use:

```text
BubbledotICG-FinePos
```

White only.

No gradient.

No shimmer.

No LED scan effect.

No animated color effect.

Desktop size:

```css
clamp(28px, 6.2vw, 80px)
```

Use the supplied responsive letter spacing and line heights.

---

# 11. LANDING SUBHEAD

Exact text:

```text
Build applications that reason, adapt and collaborate using a modular
AI platform designed for production.
```

Style according to the supplied specification.

---

# 12. LANDING CTA

Exact text:

```text
Get Started
```

This should navigate to:

```text
/app
```

Use the supplied white pill design and glow.

Hover:

```text
translateY(-2px)
scale(1.02)
```

---

# 13. LANDING TRUST ROW

Create the exact trust row:

```text
Microsoft
Amazon
Google

Trusted by 2000+ Enterprises
```

Use Font Awesome brand icons.

Do not use full white circles.

Each company logo must appear inside:

```text
dark outer ring
+
white inner circle
```

with the specified overlap.

---

# 14. LANDING STATS

Use exactly:

```text
<    120 ms       Inference Time
%    99.99 %      Platform Uptime
*    24 /7        Autonomous Runtime
#    2.4 M        Context Windows
```

Use the supplied display font for the symbols.

Use count-up animations.

Implement the supplied:

```text
easeOutCubic
1500ms + index*80ms
start offset 480ms + index*90ms
IntersectionObserver
threshold 0.25
```

---

# 15. LANDING ANIMATIONS

Implement:

```text
slideDown
headlineFade
reveal
revealPulse
overlayIn
menuIn
linkIn
```

Use the supplied cubic-bezier:

```text
cubic-bezier(0.22, 1, 0.36, 1)
```

Support:

```css
@media (prefers-reduced-motion: reduce)
```

When reduced motion is enabled:

- remove animations
- show final state
- keep headline solid white
- preserve functionality

---

# 16. APPLICATION SHELL

The `/app` experience should transition naturally from the landing page.

Use a persistent dark enterprise application shell.

Desktop layout:

```text
┌─────────────────────────────────────────────────────────────┐
│ FinExplain logo          Search        Notifications  User │
├───────────────┬─────────────────────────────────────────────┤
│               │                                             │
│ Dashboard     │                                             │
│ Documents     │              MAIN CONTENT                   │
│ Ask AI        │                                             │
│ Review        │                                             │
│ Before        │                                             │
│ Confirmation  │                                             │
│ Products      │                                             │
│ Compare       │                                             │
│ HITL Review   │                                             │
│ Feedback      │                                             │
│ Settings      │                                             │
│               │                                             │
└───────────────┴─────────────────────────────────────────────┘
```

Sidebar should be compact and premium.

Do not make it visually heavy.

Use subtle borders.

---

# 17. APPLICATION DASHBOARD

Create `/app` as the main FinExplain dashboard.

Show:

```text
Good morning

Your financial intelligence workspace
```

Then summary metrics such as:

```text
Documents
Analyses completed
Risk findings
Pending reviews
```

Use the backend where data is available.

Do not fabricate live metrics.

If the backend does not expose a dashboard metric, show an appropriate empty state rather than fake numbers.

---

# 18. DOCUMENTS PAGE

Route:

```text
/app/documents
```

This is one of the most important pages.

Provide:

```text
Upload document
Search documents
Filter
Sort
Document list
Status
Risk
Date
```

Each document should display useful metadata such as:

```text
Document name
Document type
Upload date
Processing status
Risk status
Pages
```

Primary action:

```text
Open analysis
```

Upload should connect to:

```text
POST /api/v1/documents/upload
```

Do not invent another upload endpoint.

Support:

```text
drag and drop
file picker
upload progress
processing state
success state
error state
```

---

# 19. DOCUMENT ANALYSIS PAGE

Route:

```text
/app/documents/:id
```

Design this as the central FinExplain intelligence workspace.

Suggested structure:

```text
┌──────────────────────────────────────────────────────────────┐
│ Document name                                      Risk: HIGH│
├──────────────────────┬───────────────────────────────────────┤
│                      │                                       │
│ Document viewer      │ AI Analysis                           │
│                      │                                       │
│ Page / section       │ Key Facts                             │
│                      │ Risk Findings                         │
│                      │ Evidence                               │
│                      │ Conflicts                             │
│                      │ Missing Information                   │
│                      │ Confidence                            │
│                      │                                       │
└──────────────────────┴───────────────────────────────────────┘
```

The page should make evidence visible.

Every extracted fact should visually distinguish:

```text
EXPLICIT
CONDITIONAL
INFERRED
NOT SPECIFIED
CONFLICTING
```

Where citation data exists, show:

```text
Page 4
Section: Prepayment
```

and allow the user to inspect the corresponding evidence.

---

# 20. EVIDENCE UI

Evidence is one of the defining features of FinExplain.

Do not hide citations.

For every grounded claim, provide a clear evidence treatment.

Example:

```text
Prepayment penalty
5%

Evidence
Page 12 · Section 4.2
[View source]
```

Use subtle visual hierarchy.

Do not create excessive colorful badges.

The evidence UI should feel like an audit trail.

---

# 21. ASK AI PAGE

Route:

```text
/app/query
```

This is the evidence-first Q&A interface.

Design it differently from generic ChatGPT.

User asks:

```text
What happens if I repay the loan early?
```

Response should support:

```text
Answer
Evidence
Confidence
Claim status
Source page
```

The frontend must integrate with:

```text
POST /api/v1/queries
```

Use the actual request/response schema from the backend.

Do not invent the payload structure.

Display citations directly beside claims wherever possible.

---

# 22. PROACTIVE REVIEW PAGE

Route:

```text
/app/review
```

This page should connect to:

```text
POST /api/v1/analysis/review
```

Display:

```text
Risk overview

High-risk findings
Medium-risk findings
Low-risk findings

Cost drivers
Missing disclosures
Conditional clauses
Conflicts
```

Use a clear severity hierarchy:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

The design should emphasize that FinExplain proactively finds problems before the user signs.

---

# 23. BEFORE YOU CONFIRM PAGE

Route:

```text
/app/before-confirmation
```

Connect to:

```text
POST /api/v1/analysis/before-confirmation
```

Display a prioritized checklist.

Example structure:

```text
Before You Confirm

01  Verify prepayment penalty
02  Confirm floating-rate benchmark
03  Clarify late-payment cap
04  Confirm processing fee
...
```

Every checklist item should show:

```text
Risk
Reason
Evidence
Suggested lender question
```

Do not make it look like a generic todo list.

It is a financial decision-support interface.

---

# 24. PRODUCTS PAGE

Route:

```text
/app/products
```

Connect to:

```text
GET /api/v1/products
POST /api/v1/products
```

Display financial products in a clean data-oriented interface.

Possible fields:

```text
Product
Lender
Interest rate
APR
Fees
Tenure
Risk
Status
```

Provide:

```text
View
Compare
Create
```

only when corresponding backend functionality exists.

---

# 25. PRODUCT DETAIL

Route:

```text
/app/products/:id
```

Display:

```text
Product overview
Financial terms
Fees
Interest
Conditions
Risk
Documents
Analysis
```

Reuse the same evidence-first visual language.

---

# 26. COMPARISON PAGE

Route:

```text
/app/compare
```

Allow users to compare multiple financial products.

Use a clear comparison layout.

Highlight:

```text
Interest
APR
Fees
Total cost
Prepayment
Late payment
Risk
```

If deterministic calculations are returned by the backend, display them clearly.

Never perform critical financial calculations in the frontend when the backend's deterministic calculator is intended to provide them.

---

# 27. HUMAN-IN-THE-LOOP PAGE

Route:

```text
/app/hitl
```

Connect to:

```text
GET /api/v1/hilt/tasks
```

Create a review queue.

Show:

```text
Task
Document
Priority
Risk
Status
Created
Review
```

This should feel like an enterprise operations console.

---

# 28. FEEDBACK PAGE

Route:

```text
/app/feedback
```

Connect to:

```text
POST /api/v1/feedback
```

Allow users to provide feedback on:

```text
Answer quality
Evidence quality
Citation correctness
Analysis quality
```

Keep the interface minimal.

---

# 29. SETTINGS PAGE

Route:

```text
/app/settings
```

Provide reasonable UI for:

```text
Profile
Application preferences
Display
Notifications
API/backend status
```

Do not invent backend persistence for settings unless APIs exist.

---

# 30. EMPTY STATES

Every page must have polished empty states.

Examples:

```text
No documents yet

Upload your first loan agreement
and let FinExplain analyze the risk.
```

CTA:

```text
Upload document
```

Avoid generic:

```text
No data found.
```

Make empty states product-specific.

---

# 31. LOADING STATES

Every API-driven page must have proper loading states.

Use:

```text
skeletons
subtle shimmer
progress indicators
```

but do NOT introduce the forbidden animated gradient effect into the landing-page headline.

Loading animations must remain subtle.

---

# 32. ERROR STATES

API errors must be handled gracefully.

Example:

```text
We couldn't complete the analysis.

The document is still safe.
Try again in a moment.
```

Provide:

```text
Retry
```

when appropriate.

Never expose raw Python stack traces to users.

---

# 33. API INTEGRATION

Use the existing backend API.

Base API URL should be configurable.

Do not hard-code secrets.

For development, support the existing FastAPI server:

```text
http://localhost:8000
```

Use the backend's existing endpoints.

Known endpoints:

```text
POST /api/v1/queries
POST /api/v1/analysis/review
POST /api/v1/analysis/before-confirmation
POST /api/v1/documents/upload

GET /api/v1/products
POST /api/v1/products

GET /api/v1/hilt/tasks

POST /api/v1/feedback

GET /health
```

Before implementing API calls, inspect the actual FastAPI route definitions and Pydantic schemas.

The backend implementation is the source of truth for:

```text
request body
response body
parameters
errors
IDs
status fields
```

Do not guess them.

---

# 34. SECURITY

Never expose:

```text
SUPABASE_KEY
PINECONE_API_KEY
GROQ_API_KEY
HUGGINGFACE_API_KEY
REDIS credentials
```

in frontend JavaScript.

All sensitive API keys remain server-side.

The frontend communicates with the FastAPI backend.

---

# 35. RESPONSIVE DESIGN

Desktop:

```text
Sidebar + content
```

Tablet:

```text
Collapsible sidebar
```

Mobile:

```text
Top bar
Drawer navigation
Full-width content
```

The landing page must follow the supplied exact mobile behavior.

Application pages should be responsive and usable on:

```text
1440px
1280px
1024px
768px
480px
390px
```

Do not simply shrink desktop layouts.

Reflow the UI properly.

---

# 36. ACCESSIBILITY

Implement:

```text
semantic HTML
aria-label
aria-expanded
aria-hidden
keyboard navigation
visible focus states
Escape handling
accessible buttons
accessible form controls
```

Do not rely only on color to communicate risk.

---

# 37. PERFORMANCE

Optimize for fast first load.

Do not introduce unnecessary dependencies.

Lazy-load heavy application components where appropriate.

The landing video should remain background-only.

Do not block the page unnecessarily while the video loads.

Provide a black fallback background.

---

# 38. NAVIGATION

The landing page navigation should work:

```text
Home → /
Product → relevant product section/page
Case Studies → relevant section/page
Contact → relevant section/page
Sign in → existing auth if available
```

If these routes do not yet exist in the backend/application, create sensible frontend routes or anchor sections without inventing backend functionality.

Main CTA:

```text
Get Started → /app
```

---

# 39. IMPORTANT VISUAL RESTRICTIONS

DO NOT:

```text
Create hero cards
Create a generic SaaS dashboard aesthetic
Use purple AI gradients
Use excessive glassmorphism
Use neon colors everywhere
Use gradient headline animation
Use shimmer/LED effects on headline
Replace the logo with text
Use fake company logos
Use full white trust circles
Use heavy navigation shadows
Use giant dashboard cards everywhere
```

The design should feel:

```text
minimal
intelligent
precise
premium
technical
financial
trustworthy
```

---

# 40. LANDING PAGE MUST REMAIN DISTINCT

The landing page should be visually impressive.

The application console should be functional.

Do NOT compromise the landing-page visual fidelity merely to make it look like the dashboard.

Think of the product as:

```text
PUBLIC EXPERIENCE
       ↓
FinExplain Landing Page
       ↓
Get Started
       ↓
APPLICATION
       ↓
Document Intelligence
       ↓
Evidence
       ↓
Risk
       ↓
Decision
```

---

# 41. COMPONENT / FILE ORGANIZATION

If using Vanilla HTML/CSS/JS, keep the structure clean.

Recommended:

```text
frontend/
├── index.html
├── styles.css
├── main.js
├── assets/
│   └── logo.webp
└── fonts/
    └── GeistPixel-Circle.woff2
```

If the implementation grows beyond what is practical for one JavaScript file, organize it cleanly without introducing an unnecessary framework.

If the repository already uses another stack, follow that stack's conventions.

---

# 42. DO NOT MODIFY BACKEND UNLESS REQUIRED

The task is frontend-first.

Do not rewrite:

```text
FastAPI
RAG pipeline
database layer
Pinecone integration
Groq integration
ingestion pipeline
financial calculator
verification engine
```

Only make backend changes if a genuine frontend integration blocker is discovered.

If a backend change is absolutely necessary:

1. Explain why.
2. Make the smallest possible change.
3. Preserve all existing APIs.
4. Do not break existing tests.

---

# 43. FINAL QUALITY BAR

The result should look like a real startup/enterprise product that could be shown to:

```text
Investors
Financial institutions
Loan teams
Enterprise customers
Technical reviewers
```

It must NOT look like:

```text
A generated template
A generic admin dashboard
A ChatGPT clone
A university demo
A collection of unrelated pages
```

---

# 44. FINAL VERIFICATION

Before considering the task complete, verify all of the following:

```text
[ ] Existing repository inspected
[ ] Backend APIs inspected
[ ] Existing frontend stack checked
[ ] Correct frontend technology selected
[ ] No unnecessary framework introduced
[ ] Landing page implemented
[ ] Exact background video used
[ ] Exact logo asset used
[ ] Exact display font used
[ ] Inter loaded
[ ] Font Awesome loaded
[ ] Desktop navigation implemented
[ ] Mobile navigation implemented
[ ] Hero implemented
[ ] Trust row implemented
[ ] Stats implemented
[ ] Count-up implemented
[ ] Reduced-motion implemented
[ ] /app implemented
[ ] Document library implemented
[ ] Document upload connected
[ ] Document analysis workspace implemented
[ ] Evidence UI implemented
[ ] Q&A implemented
[ ] Proactive review implemented
[ ] Before-confirmation implemented
[ ] Products implemented
[ ] Comparison implemented
[ ] HITL implemented
[ ] Feedback implemented
[ ] Settings implemented
[ ] Loading states implemented
[ ] Error states implemented
[ ] Empty states implemented
[ ] Responsive desktop/tablet/mobile layouts implemented
[ ] Accessibility implemented
[ ] No secrets exposed
[ ] Backend APIs not invented
[ ] Existing backend remains functional
[ ] No unnecessary dependencies
[ ] No broken routes
```

# FINAL INSTRUCTION

Do not stop after creating the landing page.

The goal is to create the **complete FinExplain frontend product experience**, using the supplied landing page as the visual foundation and the existing FastAPI backend as the functional source of truth.

First understand the repository.

Then build the frontend architecture.

Then implement the landing page.

Then implement the `/app` application shell.

Then implement the document intelligence, Q&A, review, evidence, product, comparison, HITL, feedback, and settings experiences.

Finally connect every available feature to the actual backend APIs and verify that the complete frontend works end-to-end.

**Prioritize correctness, visual consistency, backend compatibility, responsive behavior, accessibility, and production-quality UX.**