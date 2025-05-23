from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import router, schedule_background_task


# Create the FastAPI app instance
app = FastAPI()

# CORS middleware setup (allowing all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can specify more origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router with the /api prefix
app.include_router(router, prefix="/api")

schedule_background_task(app)  # Schedule the background task for polling Gmail inbox