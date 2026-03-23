from fastapi import FastAPI

from pool_volume_tool import router as pool_volume_router

app = FastAPI(title="Backend App With Pool Volume Tool")
app.include_router(pool_volume_router)


@app.get("/")
def root() -> dict:
    return {"ok": True, "message": "Pool volume tool mounted."}
