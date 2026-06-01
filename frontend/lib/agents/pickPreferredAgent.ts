import type { AgentId, AgentInfo } from "@/lib/api/agents";

const AGENT_PRIORITY: AgentId[] = ["gemini", "polza", "mimo", "ollama"];

export function pickPreferredAgent(agents: AgentInfo[]): AgentId | null {
  for (const id of AGENT_PRIORITY) {
    const agent = agents.find((item) => item.id === id && item.available);
    if (agent) {
      return agent.id;
    }
  }
  const any = agents.find((item) => item.available);
  return any?.id ?? null;
}
