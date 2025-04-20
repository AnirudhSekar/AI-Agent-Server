# state_graph.py
from typing import Dict, TypedDict
from .agents.email_agent import email_summarization_agent, email_reply_agent
from .agents.calendar_agent import calendar_scheduler_agent
from .agents.budget_agent import budget_tracker_agent
from .agents.reasoning_agent import reasoning_agent
from langgraph.graph.state import StateGraph

# Define the full state schema for our assistant
class FullAssistantState(TypedDict):
    inbox: list
    summary: str
    action: str
    reply: str
    calendar_event: str
    budget_status: str
    reasoning: str
    memory: dict

def create_workflow() -> StateGraph:
    """
    Creates a workflow with all agents.
    Order:
      Email Summarization -> Reasoning Agent ->
      Conditional branch: if action is "reply" or "both", run Email Reply ->
      Then run Calendar Scheduler -> Budget Tracker.
    """
    workflow = StateGraph(state_schema=FullAssistantState)

    # Add agent nodes
    workflow.add_node("EmailSummarization", email_summarization_agent)
    workflow.add_node("ReasoningAgent", reasoning_agent)
    workflow.add_node("EmailReply", email_reply_agent)
    workflow.add_node("CalendarScheduler", calendar_scheduler_agent)
    workflow.add_node("BudgetTracker", budget_tracker_agent)

    # Set entry and finish points
    workflow.set_entry_point("EmailSummarization")
    workflow.set_finish_point("BudgetTracker")

    # Define edges:
    workflow.add_edge("EmailSummarization", "ReasoningAgent")
    # Conditional routing from Reasoning Agent based on state["action"]
    workflow.add_conditional_edges(
        "ReasoningAgent",
        lambda state: state["action"],
        {
            "reply": "EmailReply",
            "both": "EmailReply",
            "schedule": "CalendarScheduler"
        }
    )
    # After EmailReply, go to CalendarScheduler if needed
    workflow.add_edge("EmailReply", "CalendarScheduler")
    # Always go from CalendarScheduler to BudgetTracker.

    return workflow

def run_workflow(inbox_data: list) -> Dict:
    global latest_result  # make sure this is global if used across API endpoints

    initial_state: FullAssistantState = {
        "inbox": inbox_data,
        "summary": "",
        "action": "",
        "reply": "",
        "calendar_event": "",
        "budget_status": "",
        "reasoning": "",
        "memory": {},
        "replies": []  # ADD THIS if it's missing from your FullAssistantState
    }

    workflow = create_workflow()
    app = workflow.compile()
    result = app.invoke(initial_state)

    # ✅ Assign full result to latest_result
    latest_result = result

    print("✅ Final state in run_workflow():", result)  # Debug
    return result