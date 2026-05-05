/**
 * workflows.ts
 * Pre-built high-value use cases exposed as single-call helpers.
 * Each workflow wraps agent.execute() with a well-crafted task string.
 */
import { getAgentController } from "./agent-controller";
import type { ExecutionResult } from "@page-agent/core";

type WorkflowResult = Promise<ExecutionResult>;

/**
 * Onboarding tour — introduces the user to Trady step by step.
 */
export async function runOnboardingTour(): WorkflowResult {
  const agent = await getAgentController();
  return agent.execute(`
    Give me a guided tour of the Trady platform.
    1. Navigate to the Dashboard and highlight the key KPI cards, explaining each one.
    2. Navigate to the Agents page, highlight the agent signal cards and explain the XAI breakdown.
    3. Navigate to the Trading page and point out the chart, order panel, and indicators — WITHOUT touching any BUY/SELL buttons.
    4. Navigate to the Analytics page and explain the performance metrics.
    5. Ask the user if they want to explore any other section.
    Keep explanations concise (2-3 sentences each).
  `.trim());
}

/**
 * Feature discovery — user asks "where is [feature]?".
 */
export async function discoverFeature(query: string): WorkflowResult {
  const agent = await getAgentController();
  return agent.execute(
    `The user wants to find: "${query}". ` +
      `Navigate to the correct page, highlight the relevant element(s), and explain what the feature does in 2 sentences.`
  );
}

/**
 * Show signals with filter — navigates to agents, applies pair + risk filter.
 */
export async function showSignalsWithFilter(
  pair: "EURUSD" | "USDJPY" | "USDCHF" | "GBPUSD",
  riskLevel: "LOW" | "MEDIUM" | "HIGH"
): WorkflowResult {
  const agent = await getAgentController();
  return agent.execute(
    `Navigate to the Agents (Signal Lab) page. ` +
      `Once there, fetch and display the latest signal for ${pair} using the fetch_market_signals tool. ` +
      `Then highlight any filter or selector for "${riskLevel}" risk level if it exists on the page. ` +
      `Explain the signal result to the user (direction, confidence, reasoning).`
  );
}

/**
 * Autofill trading parameters — fills Lot Size, SL & TP selectors.
 * Always calls request_confirmation before touching the form.
 */
export async function autofillTradingParams(params: {
  lotSize?: number;
  slPips?: number;
  tpPips?: number;
}): WorkflowResult {
  const agent = await getAgentController();
  const description = [
    params.lotSize !== undefined ? `Lot Size: ${params.lotSize}` : null,
    params.slPips !== undefined ? `Stop Loss: ${params.slPips} pips` : null,
    params.tpPips !== undefined ? `Take Profit: ${params.tpPips} pips` : null,
  ]
    .filter(Boolean)
    .join(", ");

  return agent.execute(
    `Use request_confirmation to ask the user to approve autofilling the trading form with: ${description}. ` +
      `Only after approval, navigate to the Trading page and select the correct values in the Lot Size, Stop Loss, and Take Profit dropdowns. ` +
      `Do NOT click BUY or SELL.`
  );
}

/**
 * Explain risk analysis — navigates to analytics and explains risk metrics.
 */
export async function explainRiskAnalysis(): WorkflowResult {
  const agent = await getAgentController();
  return agent.execute(
    `Navigate to the Analytics page. ` +
      `Highlight the Max Drawdown, Sharpe Ratio, and Win Rate cards. ` +
      `Explain each metric in simple terms for a forex trader. ` +
      `Then highlight the performance chart if visible.`
  );
}
