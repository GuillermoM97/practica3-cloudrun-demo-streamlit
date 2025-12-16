from fastapi import FastAPI

app = FastAPI(title="Dummy API")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/ping/{ch}")
def ping(ch: str):
    # ch puede ser cualquier caracter o string
    return {"input": ch, "message": "llamado exitoso"}

#Test
