/**
 * intent-parser.ts
 * Lightweight deterministic intent parser — runs BEFORE the LLM agent.
 *
 * Priority:
 *   0. DOM_ACTION — click/interact a named UI element (checked first)
 *   1. NAVIGATE   — instant redirect, zero LLM
 *   2. QA         — instant answer from knowledge base, zero LLM
 *   3. AGENT      — fallback to Ollama for complex tasks
 */

import { resolveElement } from "./element-registry";

export type Intent =
  | { kind: "NAVIGATE"; route: string; label: string }
  | { kind: "QA"; answer: string }
  | { kind: "DOM_ACTION"; selector: string; action: "click" | "submit"; label: string; blocked?: boolean }
  | { kind: "AGENT" };

// ── Route registry ─────────────────────────────────────────────────────────────

const ROUTES: Record<string, { path: string; label: string }> = {
  dashboard:          { path: "/dashboard",     label: "Dashboard" },
  trading:            { path: "/trading",        label: "Trading" },
  agents:             { path: "/agents",         label: "Signal Lab" },
  "signal lab":       { path: "/agents",         label: "Signal Lab" },
  signals:            { path: "/agents",         label: "Signal Lab" },
  analytics:          { path: "/analytics",      label: "Analytics" },
  reports:            { path: "/reports",        label: "Reports" },
  "strategy tutor":   { path: "/strategy-tutor", label: "Strategy Tutor" },
  "strategy-tutor":   { path: "/strategy-tutor", label: "Strategy Tutor" },
  tutor:              { path: "/strategy-tutor", label: "Strategy Tutor" },
  backtesting:        { path: "/backtesting",    label: "Backtesting" },
  backtest:           { path: "/backtesting",    label: "Backtesting" },
  monitoring:         { path: "/monitoring",     label: "Monitoring" },
  settings:           { path: "/settings",       label: "Settings" },
  login:              { path: "/login",          label: "Login" },
  signin:             { path: "/login",          label: "Login" },
  "sign in":          { path: "/login",          label: "Login" },
  register:           { path: "/register",       label: "Register" },
  signup:             { path: "/register",       label: "Register" },
  "sign up":          { path: "/register",       label: "Register" },
  home:               { path: "/",              label: "Home" },
  landing:            { path: "/",              label: "Landing Page" },
};

// ── Navigation verb pattern ────────────────────────────────────────────────────
const NAV_PATTERN =
  /^(?:click(?:\s+on)?|open|go\s+to|navigate\s+to|take\s+me\s+to|show\s+me|head\s+to|bring\s+me\s+to|move\s+to|switch\s+to|redirect\s+to|visit|access|let'?s(?:\s+(?:go\s+to|try|open|visit|go))?|i\s+(?:want|need|wanna)\s+to\s+(?:go\s+to\s+|see\s+|visit\s+|access\s+|open\s+)?|i\s*'?d\s+like\s+to\s+(?:go\s+to\s+|see\s+|visit\s+|access\s+|open\s+)?|wanna(?:\s+go\s+to)?)\s+(?:the\s+|la\s+|le\s+)?(.+?)(?:\s+(?:page|section|tab))?\s*$/i;

// Words that indicate the user wants to interact with a DOM element, NOT navigate
const BUTTON_WORDS = /\b(btn|button|link|submit|field|input|form|icon|element)\b/i;

function resolveRoute(target: string): { path: string; label: string } | null {
  const t = target.toLowerCase().trim();
  // If the target contains UI-element words, it's a DOM action — not navigation
  if (BUTTON_WORDS.test(t)) return null;
  if (ROUTES[t]) return ROUTES[t];
  for (const [key, val] of Object.entries(ROUTES)) {
    if (t.includes(key) || key.includes(t)) return val;
  }
  return null;
}

// ── Q&A knowledge base ────────────────────────────────────────────────────────

const QA_KB: Array<{ patterns: RegExp[]; answer: string }> = [
  {
    patterns: [/^\s*(?:hi|hello|hey|bonjour|salut|yo)\s*[!?.]?\s*$/i],
    answer:
      "Hi! I'm the Trady AI Copilot.\n\nI can:\n• Navigate instantly — \"click dashboard\", \"go to agents\"\n• Answer questions about Trady — features, agents, team, metrics\n• Run complex AI tasks — guided tour, live signals, strategy explanations\n\nWhat would you like to do?",
  },
  {
    patterns: [
      /what\s+(?:can\s+you\s+do|are\s+your\s+capabilities)/i,
      /^help\s*[?]?\s*$/i,
      /how\s+(?:do\s+you\s+work|does\s+this\s+(?:copilot\s+)?work)/i,
    ],
    answer:
      "I work in 3 modes:\n\n1. Instant navigation — \"click dashboard\", \"go to trading\", \"open agents\"\n2. Instant Q&A — ask anything about Trady (features, team, performance)\n3. AI agent (Ollama) — guided tours, fetch live signals, complex explanations\n\nNavigation and simple Q&A are answered instantly without AI delay.",
  },
  {
    patterns: [
      /what\s+is\s+trady/i,
      /what'?s\s+trady/i,
      /tell\s+me\s+about\s+(?:trady|this\s+platform|the\s+platform)/i,
      /explain\s+(?:trady|this\s+app|this\s+platform)/i,
    ],
    answer:
      "Trady is a multi-agent forex intelligence platform by DATAMINDS (ESPRIT 2025).\n\nIt uses 3 AI agents — Technical, Macro & Sentiment — coordinated by a meta-orchestrator to generate BUY/SELL/HOLD signals for 4 major currency pairs.\n\n5-year backtest: Sharpe 1.73 · Win Rate 57% · 120 features",
  },
  {
    patterns: [
      /what\s+(?:currency\s+)?pairs/i,
      /which\s+pairs/i,
      /what\s+(?:forex\s+)?currencies/i,
      /supported\s+pairs/i,
    ],
    answer:
      "Trady supports 4 major forex pairs:\n• EUR/USD — Euro / US Dollar\n• USD/JPY — US Dollar / Japanese Yen\n• GBP/USD — British Pound / US Dollar\n• USD/CHF — US Dollar / Swiss Franc",
  },
  {
    patterns: [
      /how\s+many\s+agents/i,
      /what\s+(?:are\s+the\s+)?agents/i,
      /which\s+agents/i,
      /tell\s+me\s+about\s+(?:the\s+)?agents/i,
      /explain\s+(?:the\s+)?agents/i,
    ],
    answer:
      "3 specialized AI agents power Trady:\n\n• Technical Agent (40%) — RSI, MACD, Bollinger Bands, ATR across 120 features\n• Macro Agent (35%) — FRED data: CPI, GDP, policy rates, carry trade signals\n• Sentiment Agent (25%) — FinBERT NLP on Reuters financial news\n\nA Coordinator combines them via weighted vote → BUY / SELL / HOLD",
  },
  {
    patterns: [
      /who\s+(?:are|made|built|created|developed)\s+(?:trady|this|the\s+team)/i,
      /team\s+(?:members?|dataminds)?/i,
      /dataminds/i,
    ],
    answer:
      "Team DATAMINDS — ESPRIT 2025:\n\n• Ines Chtioui — Project Lead\n• Amine Manai — Project Manager\n• Mariem Fersi — Solution Architect\n• Malek Chairat — Data Scientist\n• Maha Aloui — Data Scientist",
  },
  {
    patterns: [
      /(?:win\s+rate|sharpe(?:\s+ratio)?|performance|backtest(?:ing)?\s+results?)/i,
      /how\s+(?:well|good)\s+does\s+it\s+perform/i,
      /what\s+are\s+the\s+(?:results?|metrics?|numbers?)/i,
    ],
    answer:
      "5-year backtest results:\n• Win Rate: 57%\n• Sharpe Ratio: 1.73\n• Max Drawdown controlled via Kelly Criterion + ATR sizing\n• Walk-forward validated across 4 pairs",
  },
  {
    patterns: [
      /what\s+(?:pages?|sections?|features?)\s+(?:are\s+there|do\s+you\s+have|exist|can\s+i\s+(?:see|access))/i,
      /what\s+can\s+i\s+(?:do|see|access)\s+(?:here|on\s+this\s+platform)?/i,
      /show\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?(?:pages?|sections?|menu)/i,
    ],
    answer:
      "7 sections on Trady:\n\n• Dashboard — portfolio & KPI overview\n• Trading — live charts + order panel\n• Signal Lab (Agents) — AI signals with XAI breakdowns\n• Analytics — performance metrics & drawdown\n• Reports — signal history & AI explanations\n• Strategy Tutor — RAG-powered forex learning\n• Backtesting — walk-forward strategy validation",
  },
  {
    patterns: [/what\s+is\s+(?:the\s+)?dashboard/i, /explain\s+(?:the\s+)?dashboard/i],
    answer:
      "The Dashboard is your main overview — live portfolio KPIs, open positions P&L, active signals, and system health across all 4 currency pairs.",
  },
  {
    patterns: [
      /what\s+is\s+(?:the\s+)?(?:signal\s+lab|agents?\s+page)/i,
      /explain\s+(?:the\s+)?(?:signal\s+lab|agents?)/i,
    ],
    answer:
      "The Signal Lab shows real-time BUY/SELL/HOLD signals from the 3 AI agents, with confidence scores (0–100%), risk levels (LOW/MEDIUM/HIGH), and full XAI breakdowns explaining each signal.",
  },
  {
    patterns: [
      /what\s+is\s+(?:the\s+)?strategy\s+tutor/i,
      /explain\s+(?:the\s+)?(?:strategy\s+)?tutor/i,
      /what\s+is\s+(?:the\s+)?rag/i,
    ],
    answer:
      "The Strategy Tutor is a RAG (Retrieval-Augmented Generation) chatbot. Ask any forex strategy question and it retrieves answers from curated trading documents with source citations — powered by LangChain + HuggingFace.",
  },
  {
    patterns: [/what\s+is\s+(?:the\s+)?analytics/i, /explain\s+(?:the\s+)?analytics/i],
    answer:
      "The Analytics page shows detailed performance metrics: Sharpe Ratio, Max Drawdown, Win Rate by pair, cumulative P&L charts, and agent contribution breakdowns.",
  },
  {
    patterns: [/what\s+(?:is|are)\s+(?:the\s+)?backtesting/i],
    answer:
      "The Backtesting module runs walk-forward validation with Kelly Criterion position sizing and ATR-based risk controls to verify strategy robustness over 5 years of historical data.",
  },
  {
    patterns: [/what\s+(?:is|are)\s+(?:the\s+)?monitoring/i],
    answer:
      "Monitoring tracks system health: data pipeline freshness, inference latency, PSI drift detection, and safety guard alerts.",
  },
  {
    patterns: [/what\s+is\s+(?:2fa|two.factor|face\s+recognition|face\s+auth)/i],
    answer:
      "Trady supports 3 two-factor authentication methods:\n• Face Recognition (DeepFace + ArcFace, 512-d embeddings)\n• Email OTP (6-digit code via Gmail SMTP)\n• SMS OTP (via Twilio)\n\nAll face embeddings are Fernet-encrypted at rest.",
  },
  {
    patterns: [
      /what\s+(?:llm|model|ai|technology|tech(?:nology)?|stack)\s+(?:do\s+you|does\s+trady|is\s+used)/i,
      /what\s+powers?\s+(?:trady|this)/i,
    ],
    answer:
      "Trady's tech stack:\n• AI Agents — LangGraph + LangChain orchestration\n• LLM — HuggingFace flan-t5-base (explainability only)\n• NLP — FinBERT (sentiment) + sentence-transformers\n• Backend — Django 5 + DRF (Python)\n• Frontend — Next.js 16 + React 19 + TailwindCSS\n• Data — InfluxDB (OHLCV) + PostgreSQL (macro/news)",
  },
];

// ── Public API ─────────────────────────────────────────────────────────────────

// Verbs that signal the user wants to click/interact with a DOM element
const CLICK_VERBS =
  /^(?:click(?:\s+on)?|press|hit|tap|submit|push|select|toggle|open|activate|trigger|use|do|run|execute|launch|fire)\s+(?:the\s+|a\s+|on\s+the\s+)?(.+?)(?:\s+(?:btn|button|link|icon|toggle))?\s*$/i;

// Bare element names (no verb) — user just types a button label
const BARE_ELEMENT_PATTERNS =
  /^(?:sign[\s-]?in|log(?:\s+)?in|logout|log(?:\s+)?out|sign(?:\s+)?out|generate\s+signal|ingest\s+data|refresh\s+(?:news|ohlcv|macro|all)|export\s+csv|save\s+settings|enroll\s+face|enable\s+2fa)\s*(?:btn|button|now|please|me)?\s*$/i;

export function parseIntent(input: string): Intent {
  const text = input.trim();
  if (!text) return { kind: "AGENT" };

  // ── 0a. Direct click verb + element name ──────────────────────────────────
  const clickMatch = text.match(CLICK_VERBS);
  if (clickMatch) {
    const elementName = clickMatch[1].trim();
    const entry = resolveElement(elementName);
    if (entry) {
      return {
        kind: "DOM_ACTION",
        selector: entry.selectors[0],
        action: "click",
        label: entry.label,
        blocked: entry.blocked,
      };
    }
    // If verb+name looks like nav and resolveRoute works, fall through to nav below
  }

  // ── 0b. Bare element name (no click verb needed) ──────────────────────────
  if (BARE_ELEMENT_PATTERNS.test(text)) {
    const entry = resolveElement(text.replace(/\s*(?:btn|button|now|please|me)\s*$/i, "").trim());
    if (entry) {
      return {
        kind: "DOM_ACTION",
        selector: entry.selectors[0],
        action: "click",
        label: entry.label,
        blocked: entry.blocked,
      };
    }
  }

  // ── 0c. Direct element registry lookup (exact / fuzzy) ───────────────────
  // Handles: "sign in btn", "generate signal btn", "refresh news", etc.
  {
    const clean = text
      .toLowerCase()
      .replace(/^(?:click(?:\s+on)?|press|hit|tap|push)\s+(?:the\s+|on\s+the\s+)?/, "")
      .replace(/\s+(?:button|btn|link|icon|toggle)$/, "")
      .trim();
    const entry = resolveElement(clean);
    if (entry) {
      // Only treat as DOM_ACTION if the original text has a click verb OR element words
      const hasClickSignal =
        /\b(?:click|press|hit|tap|btn|button|link|toggle|submit|icon)\b/i.test(text) ||
        BARE_ELEMENT_PATTERNS.test(text);
      if (hasClickSignal) {
        return {
          kind: "DOM_ACTION",
          selector: entry.selectors[0],
          action: "click",
          label: entry.label,
          blocked: entry.blocked,
        };
      }
    }
  }

  // 1. Bare page name — user just types "dashboard", "trading", etc.
  const bareRoute = ROUTES[text.toLowerCase()];
  if (bareRoute) return { kind: "NAVIGATE", route: bareRoute.path, label: bareRoute.label };

  // 2. Navigation verb pattern
  const navMatch = text.match(NAV_PATTERN);
  if (navMatch) {
    const resolved = resolveRoute(navMatch[1].trim());
    if (resolved) return { kind: "NAVIGATE", route: resolved.path, label: resolved.label };
  }

  // 3. Knowledge base Q&A
  for (const entry of QA_KB) {
    if (entry.patterns.some((p) => p.test(text))) {
      return { kind: "QA", answer: entry.answer };
    }
  }

  // 4. Off-topic question guard — don't send general knowledge questions to LLM
  const TRADY_KEYWORDS =
    /trady|dashboard|trading|agent|signal|analytic|report|backtest|monitor|tutor|strategy|2fa|pair|currency|currencies|forex|eur|usd|gbp|jpy|chf|sharpe|drawdown|win\s*rate|rag|finbert|sentiment|technical|macro|coordinator|kpi|position|ollama|llm|chart|candlestick|indicator|rsi|macd|bollinger|atr|cpi|gdp|fred|pair|ohlcv|langchain|huggingface|deepface/i;

  const IS_GENERIC_QUESTION =
    /^(?:what|how|why|when|where|who|which|explain|define|tell\s+me\s+about|describe)\b/i;

  if (IS_GENERIC_QUESTION.test(text) && !TRADY_KEYWORDS.test(text)) {
    return {
      kind: "QA",
      answer:
        "I'm Trady's AI Copilot — I only assist with the Trady forex platform.\n\nFor general knowledge questions, please use a general-purpose assistant.\n\nFor Trady, I can help with:\n• Features & navigation — \"click dashboard\", \"go to agents\"\n• Platform Q&A — \"what is Trady?\", \"what pairs do you support?\"\n• Complex tasks — \"run the onboarding tour\", \"fetch EUR/USD signals\"\n\nSay \"help\" to see all options.",
    };
  }

  // 5. Fallback → Ollama LLM for complex Trady tasks
  return { kind: "AGENT" };
}
