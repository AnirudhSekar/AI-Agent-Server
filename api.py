# backend/api.py
import logging
import asyncio
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict
from backend.state_graph import run_workflow
from backend.agents.email_agent import email_summarization_agent
from backend.tools.gmail_tools import get_gmail_inbox, authenticate_gmail

router = APIRouter()
latest_result: Dict = {}

class WorkflowRequest(BaseModel):
    inbox: List[Dict]  # Inbox from external request (manual sync)

@router.on_event("startup")
async def schedule_background_task():
    async def poll_loop():
        while True:
            try:
                logging.info("⏳ Fetching Gmail inbox & running workflow…")
                # Get Gmail inbox with auto authentication handling
                inbox = get_gmail_inbox(max_results=10)  # You can customize the max_results
                latest_result.clear()
                latest = run_workflow(inbox)
                latest_result.update(latest)
                logging.info("✅ Workflow result: %s", latest)
            except Exception as e:
                logging.error("❌ Scheduled run failed: %s", e)
            await asyncio.sleep(300)  # Wait 5 minutes before running again

    # Start background task for polling
    asyncio.create_task(poll_loop())

@router.get("/last-result")
async def get_last_result():
    """
    Get the most recent workflow result from the 5-minute polling.
    """
    if not latest_result:
        return {"message": "No data yet – please wait for the first run."}
    return latest_result

@router.post("/run-workflow")
async def run_full_workflow(req: WorkflowRequest):
    """
    Manually trigger the workflow with a custom inbox payload.
    """
    try:
        inbox = req.inbox
        result = run_workflow(inbox)
        return result
    except Exception as e:
        logging.error("❌ Manual run failed: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "details": str(e)},
        )

@router.get("/sync-gmail")
async def sync_gmail_inbox():
    """
    Sync Gmail inbox, run workflow, and return the result.
    This route allows manual sync and runs the workflow based on Gmail inbox.
    """
    try:
        # Ensure Gmail authentication
        inbox = get_gmail_inbox()  # Fetch inbox after authenticating
        result = run_workflow(inbox)
        global latest_result
        latest_result = result
        logging.info("✅ Gmail sync completed successfully")
        return result
    except Exception as e:
        logging.error("❌ Gmail sync failed: %s", str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})

# New helper endpoint to handle authentication
@router.get("/authenticate-gmail")
async def authenticate_gmail_account():
    """
    Handle OAuth authentication for Gmail (step 1)
    This route will trigger the OAuth flow if no token is present or if authentication is required.
    """
    try:
        authenticate_gmail()  # Initiates OAuth process
        return {"message": "Please visit the authentication URL to grant access to your Gmail account."}
    except Exception as e:
        logging.error("❌ Gmail authentication failed: %s", str(e))
        return JSONResponse(status_code=500, content={"error": "Authentication failed", "details": str(e)})
@router.get("/fetch-and-run")
async def fetch_and_run():
    try:
        inbox = get_gmail_inbox()
        result = run_workflow(inbox)
        global latest_result
        latest_result = result
        return result
    except Exception as e:
        logging.error("❌ fetch-and-run failed: %s", str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})
