import ollama
from typing import Dict
def reasoning_agent(state: Dict) -> Dict:
    """
    Uses Ollama (Phi3) to reason about the summary and decide the next action.
    The agent will set:
      - "both" if the summary mentions both a meeting and an invoice,
      - "reply" if only a reply is needed,
      - "schedule" if only scheduling is required,
      - "suggest_time" if a time was proposed but needs rescheduling.
    """
    summary = state.get("summary", "").lower()
    prompt = (
        f"Analyze the following email summary and decide the next action.\n"
        "Possible actions:\n"
        "- reply: if the email needs a response but no scheduling.\n"
        "- schedule: if the email asks to set up a meeting without a specific time.\n"
        "- suggest_time: if the sender proposed a meeting time, but we need to suggest another time.\n"
        "- both: if the email involves both a meeting and a business topic like invoice or budget.\n\n"
        f"Summary:\n{summary}\n"
        "Return only one of: reply, schedule, suggest_time, or both."
    )

    result = ollama.chat(model="phi3", messages=[{"role": "user", "content": prompt}])
    decision = result.get("text", "reply").strip().lower()

    if decision not in ["reply", "schedule", "suggest_time", "both"]:
        decision = "reply"

    state["action"] = decision
    state["reasoning"] = f"Decided action: {decision} based on summary."
    print("📌 State after ReasoningAgent:", state)
    return state
