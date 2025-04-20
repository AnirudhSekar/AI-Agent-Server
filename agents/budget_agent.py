# agents/budget_agent.py
from typing import Dict
from backend.tools.calendar_tools import write_invoice

def budget_tracker_agent(state: Dict) -> Dict:
    """
    Processes invoice details from the summary and writes them to a CSV file.
    """
    summary = state.get("summary", "").lower()
    if "invoice" in summary or "500" in summary:
        # Create an invoice record.
        invoice = {
            "InvoiceID": "123",
            "Amount": "500",
            "DueDate": "2025-05-01"
        }
        csv_file = "invoices.csv"
        write_invoice(invoice, csv_file)
        state["budget_status"] = "Invoice of $500 processed and recorded."
        state["action"] = "budget_updated"
    else:
        state["budget_status"] = "No invoice processed."
    
    print("State after Budget Processing:", state)
    return state
