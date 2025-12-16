import json
import os
import time
from typing import Any, Dict, Optional

import joblib
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Inferencia ENR API")

MODEL_PRE_PATH = os.getenv("MODEL_PRE_PATH", "enr_preprocess_ohe.joblib")
MODEL_BST_PATH = os.getenv("MODEL_BST_PATH", "enr_xgb_cuda_booster.json")
META_PATH      = os.getenv("META_PATH",      "enr_model_meta.json")

pre = None
bst = None
baseline_nacional: float = 0.0436

REQUIRED_FEATURES = [
    "estado_ocurrencia",
    "tamano_localidad_ocurrencia",
    "edad_madre_rango",
    "edad_madre_no_especificada",
    "escolaridad_madre",
    "condicion_actividad_madre",
    "estado_civil_madre_modelo",
    "edad_padre_rango",
    "edad_padre_no_especificada",
    "escolaridad_padre",
    "condicion_actividad_padre",
    "hijos_vivo_bucket",
]

class PredictRequest(BaseModel):
    features: Dict[str, Any] = Field(...)

class PredictResponse(BaseModel):
    prob_parto_no_institucional: float
    riesgo_relativo_vs_nacional: Optional[float]
    latency_ms: float

@app.on_event("startup")
def load_artifacts():
    global pre, bst, baseline_nacional
    # Carga una sola vez
    pre = joblib.load(MODEL_PRE_PATH)

    bst = xgb.Booster()
    bst.load_model(MODEL_BST_PATH)

    try:
        with open(META_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        baseline_nacional = float(meta.get("baseline_nacional", baseline_nacional))
    except Exception:
        pass

@app.get("/health")
def health():
    return {"ok": pre is not None and bst is not None, "baseline_nacional": baseline_nacional}

@app.get("/ping/{ch}")
def ping(ch: str):
    return {"input": ch, "message": "llamado exitoso"}

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if pre is None or bst is None:
        raise HTTPException(status_code=503, detail="Modelo no cargado aún")

    feats = req.features
    missing = [k for k in REQUIRED_FEATURES if k not in feats]
    if missing:
        raise HTTPException(status_code=400, detail={"missing": missing})

    t0 = time.time()
    X = pd.DataFrame([feats])
    Xv = pre.transform(X)
    dX = xgb.DMatrix(Xv)
    p = float(bst.predict(dX)[0])

    rr = (p / baseline_nacional) if baseline_nacional > 0 else None
    latency_ms = (time.time() - t0) * 1000.0

    return PredictResponse(
        prob_parto_no_institucional=p,
        riesgo_relativo_vs_nacional=rr,
        latency_ms=latency_ms,
    )
