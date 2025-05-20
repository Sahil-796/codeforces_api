from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from collections import defaultdict
from datetime import datetime
import os

app = FastAPI(title="Codeforces API", description="API for fetching Codeforces user data")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

CODEFORCES_API = "https://codeforces.com/api"

async def fetch_codeforces(endpoint: str, params: dict = None):
    url = f"{CODEFORCES_API}/{endpoint}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        if data.get("status") != "OK":
            raise HTTPException(status_code=404, detail=data.get("comment", "Not found"))
        return data["result"]

@app.get("/", response_class=JSONResponse)
@app.head("/")
async def root():
    return {
        "status": "active",
        "message": "Welcome to Codeforces API",
        "endpoints": {
            "user_info": "/user/{handle}",
            "solved_problems": "/user/{handle}/solved",
            "rating_history": "/user/{handle}/rating"
        }
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.get("/user/{handle}")
async def get_user_info(handle: str):
    user_info = await fetch_codeforces("user.info", {"handles": handle})
    rating_info = user_info[0]
    # Get rating and rank
    rating = rating_info.get("rating")
    rank = rating_info.get("rank")
    max_rating = rating_info.get("maxRating")
    max_rank = rating_info.get("maxRank")
    # Get total solved
    submissions = await fetch_codeforces("user.status", {"handle": handle})
    solved = set()
    for sub in submissions:
        if sub.get("verdict") == "OK":
            pid = (sub["problem"].get("contestId"), sub["problem"].get("index"))
            solved.add(pid)
    total_solved = len(solved)
    return {
        "handle": handle,
        "rating": rating,
        "rank": rank,
        "max_rating": max_rating,
        "max_rank": max_rank,
        "total_solved": total_solved
    }

@app.get("/user/{handle}/solved")
async def get_user_solved(handle: str):
    submissions = await fetch_codeforces("user.status", {"handle": handle})
    solved = {}
    solved_dates = defaultdict(int)
    for sub in submissions:
        if sub.get("verdict") == "OK":
            pid = (sub["problem"].get("contestId"), sub["problem"].get("index"))
            if pid not in solved:
                solved[pid] = sub
                # For consistency graph: count by day
                ts = sub["creationTimeSeconds"]
                day = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
                solved_dates[day] += 1
    return {
        "total_solved": len(solved),
        "solved_problems": list(solved.keys()),
        "solved_per_day": solved_dates
    }

@app.get("/user/{handle}/rating")
async def get_user_rating(handle: str):
    rating_changes = await fetch_codeforces("user.rating", {"handle": handle})
    return rating_changes 