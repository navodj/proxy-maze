from fastapi import FastAPI

app = FastAPI(title="Proxy Maze 26")

@app.get("/health")
async def health_check():
    return {"status": "ok"}