from fastapi import FastAPI
app = FastAPI()

@app.get("/ping/{ch}")
def ping(ch: str):
    return {"input": ch, "message": "llamado exitoso"}


#Test
