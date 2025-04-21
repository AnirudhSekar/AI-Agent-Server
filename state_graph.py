# state_graph.py
from typing import Dict, TypedDict
from agents.email_agent import email_summarization_agent, email_reply_agent
from agents.calendar_agent import calendar_scheduler_agent
from agents.reasoning_agent import reasoning_agent
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
    replies: list  # make sure this exists

def create_workflow() -> StateGraph:
    workflow = StateGraph(state_schema=FullAssistantState)

    # Add agent nodes
    workflow.add_node("EmailSummarization", email_summarization_agent)
    workflow.add_node("ReasoningAgent", reasoning_agent)
    workflow.add_node("EmailReply", email_reply_agent)
    workflow.add_node("CalendarScheduler", calendar_scheduler_agent)

    # Entry and exit
    workflow.set_entry_point("EmailSummarization")
    workflow.set_finish_point("CalendarScheduler")

    # Flow: EmailSummarization -> Reasoning
    workflow.add_edge("EmailSummarization", "ReasoningAgent")

    # Conditional branching after Reasoning
    workflow.add_conditional_edges(
        "ReasoningAgent",
        lambda state: state["action"],
        {
            "reply": "CalendarScheduler",   # still go to calendar first
            "schedule": "CalendarScheduler",
            "both": "CalendarScheduler",
        }
    )

    # Always Calendar → Reply
    workflow.add_edge("CalendarScheduler", "EmailReply")
    return workflow


def run_workflow(inbox_data: list) -> Dict:
    global latest_result  # global var to expose result if needed elsewhere

    initial_state: FullAssistantState = {
        "inbox": inbox_data,
        "summary": "",
        "action": "",
        "reply": "",
        "calendar_event": "",
        "budget_status": "",
        "reasoning": "",
        "memory": {},
        "replies": [],
    }

    workflow = create_workflow()
    app = workflow.compile()
    result = app.invoke(initial_state)

    latest_result = result
    print("✅ Final state in run_workflow():", result)
    return result
