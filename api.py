# backend/api.py

import logging
import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict
from state_graph import run_workflow
from agents.email_agent import email_summarization_agent
from tools.gmail_tools import get_gmail_inbox, authenticate_gmail

router = APIRouter()
latest_result: Dict = {}

# Configure logging to see the process clearly in development
logging.basicConfig(
    level=logging.INFO,  # Adjust logging level as needed
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class WorkflowRequest(BaseModel):
    inbox: List[Dict]  # Inbox data provided in the request

def schedule_background_task(app):
    """
    Schedules a background task that polls Gmail inbox and triggers the workflow.
    Runs every 10 minutes to ensure the latest data is available.
    """
    @app.on_event("startup")
    async def poll_loop():
        while True:
            try:
                logging.info("⏳ Fetching Gmail inbox & running workflow…")
                inbox = get_gmail_inbox(max_results=1)  # Fetch one email for testing
                if inbox:
                    logging.info(f"Fetched inbox: {inbox}")
                    latest_result.clear()
                    result = run_workflow(inbox)
                    latest_result.update(result)
                    logging.info(f"✅ Workflow result: {latest_result}")
                    break
                else:
                    logging.warning("⚠️ No emails fetched, skipping workflow run.")
            except Exception as e:
                logging.error(f"❌ Error while fetching inbox or running workflow: {str(e)}")
@router.get("/last-result")
def get_last_result():
    """
    Returns the most recent workflow result from the background polling.
    If no result is available, informs the user to wait.
    """
    global latest_result
    
    if not latest_result:
        logging.warning("No result available yet.")
        return {"message": "No data yet – please wait for the first run."}
    
    logging.info(f"Returning latest result: {latest_result}")
    return latest_result

@router.post("/run-workflow")
async def run_full_workflow(req: WorkflowRequest):
    """
    Manually trigger the workflow with a custom inbox payload.
    Useful for testing or triggering the workflow on demand.
    """
    try:
        inbox = req.inbox
        logging.info(f"Manually triggering workflow with inbox: {inbox}")
        result = run_workflow(inbox)
        logging.info(f"✅ Workflow result: {result}")
        return result
    except Exception as e:
        logging.error(f"❌ Manual run failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/sync-gmail")
async def sync_gmail_inbox():
    """
    Manually sync Gmail inbox and run the workflow based on the fetched emails.
    This endpoint is used to trigger a sync without waiting for the background task.
    """
    try:
        logging.info("⏳ Manually syncing Gmail inbox…")
        inbox = get_gmail_inbox()  # Sync inbox directly (make sure this is authenticated)
        
        if not inbox:
            logging.warning("⚠️ No emails fetched during Gmail sync.")
            return JSONResponse(status_code=404, content={"error": "No emails found in inbox"})
        
        logging.info(f"Fetched inbox: {inbox}")
        result = run_workflow(inbox)
        global latest_result
        latest_result = result
        logging.info("✅ Gmail sync completed and workflow result obtained.")
        return result
    except Exception as e:
        logging.error(f"❌ Gmail sync failed: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/authenticate-gmail")
async def authenticate_gmail_account():
    """
    Starts the Gmail OAuth authentication process if needed.
    This is the first step to ensure the app can access Gmail inbox.
    """
    try:
        logging.info("🔑 Starting Gmail authentication process...")
        authenticate_gmail()  # Ensure that the Gmail API OAuth process is triggered
        return {"message": "Please visit the authentication URL to grant access to your Gmail account."}
    except Exception as e:
        logging.error(f"❌ Gmail authentication failed: {str(e)}")
        return JSONResponse(status_code=500, content={"error": "Authentication failed", "details": str(e)})



