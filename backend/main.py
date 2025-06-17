from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1 import auth as auth_router
from backend.api.v1 import passes as passes_router
from backend.api.v1 import schools as schools_router
from backend.api.v1 import dashboards as dashboards_router

app = FastAPI(
    title="SchoolSecure Hall Pass API",
    description="API for managing school hall passes.",
    version="0.0.1",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to the frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(passes_router.router, prefix="/api/v1")
app.include_router(schools_router.router, prefix="/api/v1")
app.include_router(dashboards_router.router, prefix="/api/v1")

@app.get("/", tags=["Health Check"])
def read_root():
    """
    Root endpoint for health check.
    """
    return {"status": "ok", "message": "Welcome to the SchoolSecure API"} 