# agents/reasoning_agent.py
import ollama
from typing import Dict

def reasoning_agent(state: Dict) -> Dict:
    """
    Uses Ollama (Phi3) to reason about the summary and decide the next action.
    The agent will set:
      - "both" if the summary mentions both a meeting and an invoice,
      - "reply" if only a reply is needed,
      - "schedule" if only scheduling is required.
    """
    summary = state.get("summary", "").lower()
    prompt = (
        f"Analyze the following email summary and decide whether to reply, schedule a meeting, or both:\n{summary}\n"
        "Answer with one of: reply, schedule, or both."
    )
    result = ollama.chat(model="phi3", messages=[{"role": "user", "content": prompt}])
    decision = result.get("text", "reply").strip().lower()
    if decision not in ["reply", "schedule", "both"]:
        decision = "reply"
    state["action"] = decision
    state["reasoning"] = f"Decided action: {decision} based on summary."
    print("State after Reasoning:", state)
    return state
