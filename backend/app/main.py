from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import auth, courses, assignments, teams, submissions, feedback

settings = get_settings()

app = FastAPI(
    title="CourseWork Evaluation Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api/auth",        tags=["Auth"])
app.include_router(courses.router,     prefix="/api/courses",     tags=["Courses"])
app.include_router(assignments.router, prefix="/api/assignments",  tags=["Assignments"])
app.include_router(teams.router,       prefix="/api/teams",        tags=["Teams"])
app.include_router(submissions.router, prefix="/api/submissions",  tags=["Submissions"])
app.include_router(feedback.router,    prefix="/api/feedback",     tags=["Feedback"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
