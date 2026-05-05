/**
 * element-registry.ts
 * Central registry of every named interactive element in the Trady app.
 * Keys are lowercase natural-language names the user might say.
 * Values describe how to find and interact with the element.
 */

export interface ElementEntry {
  /** CSS selectors to try in order */
  selectors: string[];
  /** Human-readable name shown in the copilot */
  label: string;
  /** Page(s) where this element exists */
  page?: string;
  /** Whether this element is blocked from AI automation */
  blocked?: boolean;
  /** Optional description for the LLM */
  description?: string;
}

export const ELEMENT_REGISTRY: Record<string, ElementEntry> = {

  // ── AUTH ──────────────────────────────────────────────────────────────────
  "sign in": {
    selectors: ["#sign-in-btn", "[data-testid='sign-in-btn']", "button[type='submit']"],
    label: "Sign in",
    page: "/login",
  },
  "sign in btn": {
    selectors: ["#sign-in-btn", "[data-testid='sign-in-btn']"],
    label: "Sign in",
    page: "/login",
  },
  "login btn": {
    selectors: ["#sign-in-btn", "[data-testid='sign-in-btn']"],
    label: "Sign in",
    page: "/login",
  },
  "submit login": {
    selectors: ["#login-form", "#sign-in-btn"],
    label: "Sign in",
    page: "/login",
  },
  "create account": {
    selectors: ["[data-testid='register-btn']", "form button[type='submit']"],
    label: "Create account",
    page: "/register",
  },
  "register btn": {
    selectors: ["[data-testid='register-btn']"],
    label: "Create account",
    page: "/register",
  },
  "show password": {
    selectors: ["button[aria-label='Show password']", "button[aria-label='Hide password']"],
    label: "Toggle password visibility",
  },
  "remember me": {
    selectors: ["input[type='checkbox']"],
    label: "Remember me",
    page: "/login",
  },

  // ── SIDEBAR ───────────────────────────────────────────────────────────────
  "logout": {
    selectors: ["[data-testid='sidebar-logout']", "button[data-testid='sidebar-logout']"],
    label: "Log out",
    description: "Sign out of the platform",
  },
  "log out": {
    selectors: ["[data-testid='sidebar-logout']"],
    label: "Log out",
  },
  "sign out": {
    selectors: ["[data-testid='sidebar-logout']"],
    label: "Log out",
  },
  "toggle sidebar": {
    selectors: ["[data-testid='sidebar-toggle']", "button[data-sidebar='trigger']"],
    label: "Toggle Sidebar",
  },

  // ── DASHBOARD ─────────────────────────────────────────────────────────────
  "view agents": {
    selectors: ["[data-testid='dashboard-view-agents']"],
    label: "View Agents",
    page: "/dashboard",
  },
  "monitoring dashboard": {
    selectors: ["[data-testid='dashboard-monitoring']"],
    label: "Monitoring Dashboard",
    page: "/dashboard",
  },
  "generate signal": {
    selectors: [
      "[data-testid='generate-signal-btn']",
      "button[data-testid='generate-signal-btn']",
    ],
    label: "Generate Signal",
    description: "Runs the multi-agent signal pipeline",
  },
  "retry": {
    selectors: ["[data-testid='signal-retry-btn']", "button[data-testid='signal-retry-btn']"],
    label: "Retry",
  },

  // ── SIGNAL LAB PAIR SELECTORS ─────────────────────────────────────────────
  "eurusd": {
    selectors: ["[data-testid='pair-EURUSD']"],
    label: "EUR/USD pair",
    page: "/agents",
  },
  "eur/usd": {
    selectors: ["[data-testid='pair-EURUSD']"],
    label: "EUR/USD pair",
  },
  "usdjpy": {
    selectors: ["[data-testid='pair-USDJPY']"],
    label: "USD/JPY pair",
  },
  "usd/jpy": {
    selectors: ["[data-testid='pair-USDJPY']"],
    label: "USD/JPY pair",
  },
  "gbpusd": {
    selectors: ["[data-testid='pair-GBPUSD']"],
    label: "GBP/USD pair",
  },
  "gbp/usd": {
    selectors: ["[data-testid='pair-GBPUSD']"],
    label: "GBP/USD pair",
  },
  "usdchf": {
    selectors: ["[data-testid='pair-USDCHF']"],
    label: "USD/CHF pair",
  },
  "usd/chf": {
    selectors: ["[data-testid='pair-USDCHF']"],
    label: "USD/CHF pair",
  },

  // ── INGEST DATA ───────────────────────────────────────────────────────────
  "ingest data": {
    selectors: ["[data-testid='ingest-data-btn']"],
    label: "Ingest Data",
    page: "/agents",
    description: "Opens the data ingestion dropdown",
  },
  "refresh news": {
    selectors: ["[data-testid='refresh-news-btn']"],
    label: "Refresh News",
    page: "/agents",
  },
  "refresh ohlcv": {
    selectors: ["[data-testid='refresh-ohlcv-btn']"],
    label: "Refresh OHLCV",
    page: "/agents",
  },
  "refresh macro": {
    selectors: ["[data-testid='refresh-macro-btn']"],
    label: "Refresh Macro",
    page: "/agents",
  },
  "refresh all": {
    selectors: ["[data-testid='refresh-all-btn']"],
    label: "Refresh All Sources",
    page: "/agents",
  },

  // ── TRADING ───────────────────────────────────────────────────────────────
  "buy": {
    selectors: ["[data-testid='trade-buy-btn']"],
    label: "BUY",
    page: "/trading",
    blocked: true,
    description: "Opens a long position — requires confirmation",
  },
  "sell": {
    selectors: ["[data-testid='trade-sell-btn']"],
    label: "SELL",
    page: "/trading",
    blocked: true,
    description: "Opens a short position — requires confirmation",
  },

  // ── ANALYTICS TABS ────────────────────────────────────────────────────────
  "performance tab": {
    selectors: ["[data-testid='analytics-tab-performance']"],
    label: "Performance",
    page: "/analytics",
  },
  "macro indicators tab": {
    selectors: ["[data-testid='analytics-tab-macro']"],
    label: "Macro Indicators",
    page: "/analytics",
  },
  "sentiment tab": {
    selectors: ["[data-testid='analytics-tab-sentiment']"],
    label: "Sentiment NLP",
    page: "/analytics",
  },

  // ── REPORTS ───────────────────────────────────────────────────────────────
  "export csv": {
    selectors: ["[data-testid='reports-export-csv']", "a[data-testid='reports-export-csv']"],
    label: "Export CSV",
    page: "/reports",
    description: "Download the signal history as CSV",
  },
  "filter all pairs": {
    selectors: ["[data-testid='reports-filter-all']"],
    label: "Filter: All",
    page: "/reports",
  },
  "filter eurusd": {
    selectors: ["[data-testid='reports-filter-eurusd']"],
    label: "Filter: EUR/USD",
    page: "/reports",
  },
  "filter usdjpy": {
    selectors: ["[data-testid='reports-filter-usdjpy']"],
    label: "Filter: USD/JPY",
    page: "/reports",
  },
  "filter gbpusd": {
    selectors: ["[data-testid='reports-filter-gbpusd']"],
    label: "Filter: GBP/USD",
    page: "/reports",
  },
  "filter usdchf": {
    selectors: ["[data-testid='reports-filter-usdchf']"],
    label: "Filter: USD/CHF",
    page: "/reports",
  },

  // ── STRATEGY TUTOR ────────────────────────────────────────────────────────
  "upload tab": {
    selectors: ["[data-testid='tutor-tab-upload']"],
    label: "Upload",
    page: "/strategy-tutor",
  },
  "my docs tab": {
    selectors: ["[data-testid='tutor-tab-docs']"],
    label: "My Docs",
    page: "/strategy-tutor",
  },

  // ── BACKTESTING TABS ──────────────────────────────────────────────────────
  "backtesting tab": {
    selectors: ["[data-testid='backtest-tab-backtest']"],
    label: "Backtesting",
    page: "/backtesting",
  },
  "position sizing tab": {
    selectors: ["[data-testid='backtest-tab-sizing']"],
    label: "Position Sizing",
    page: "/backtesting",
  },

  // ── MONITORING TABS ───────────────────────────────────────────────────────
  "data validation tab": {
    selectors: ["[data-testid='monitoring-tab-validation']"],
    label: "Data Validation",
    page: "/monitoring",
  },
  "mlflow tab": {
    selectors: ["[data-testid='monitoring-tab-mlflow']"],
    label: "MLflow Metrics",
    page: "/monitoring",
  },

  // ── SETTINGS ──────────────────────────────────────────────────────────────
  "api keys tab": {
    selectors: ["[data-testid='settings-tab-api']", "[data-value='api']"],
    label: "API Keys",
    page: "/settings",
  },
  "agent config tab": {
    selectors: ["[data-testid='settings-tab-agents']", "[data-value='agents']"],
    label: "Agent Config",
    page: "/settings",
  },
  "notifications tab": {
    selectors: ["[data-testid='settings-tab-notifications']", "[data-value='notifications']"],
    label: "Notifications",
    page: "/settings",
  },
  "risk management tab": {
    selectors: ["[data-testid='settings-tab-risk']", "[data-value='risk']"],
    label: "Risk Management",
    page: "/settings",
  },
  "security tab": {
    selectors: ["[data-testid='settings-tab-security']", "[data-value='security']"],
    label: "Security",
    page: "/settings",
  },
  "save settings": {
    selectors: ["[data-testid='settings-save-btn']"],
    label: "Save Settings",
    page: "/settings",
  },
  "enroll face": {
    selectors: ["[data-testid='settings-enroll-face-btn']"],
    label: "Enroll Face",
    page: "/settings",
  },
  "enable 2fa": {
    selectors: ["[data-testid='settings-2fa-toggle']"],
    label: "Enable 2FA",
    page: "/settings",
  },
};

/**
 * Resolve a natural-language element name to its ElementEntry.
 * Tries exact match, then prefix/contains.
 */
export function resolveElement(input: string): ElementEntry | null {
  const key = input.toLowerCase().trim();
  if (ELEMENT_REGISTRY[key]) return ELEMENT_REGISTRY[key];
  // Fuzzy: find a key that the input contains or vice-versa
  for (const [k, v] of Object.entries(ELEMENT_REGISTRY)) {
    if (key.includes(k) || k.includes(key)) return v;
  }
  return null;
}
