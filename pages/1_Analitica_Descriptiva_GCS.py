import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from utils.gcs_loader import list_gcs_blobs, load_gcs_blob

st.title("Analítica Descriptiva desde GCS (Altair)")

# --------------------------------------------
# Parámetros de conexión
# --------------------------------------------
bucket = st.text_input("Bucket de GCS:", "bucket_131025")
prefix = st.text_input("Prefijo:", "tlc_yellow_trips_2022/")

# --------------------------------------------
# Listar blobs en el bucket
# --------------------------------------------
blobs = list_gcs_blobs(bucket, prefix)

if not blobs:
    st.error("No se encontraron archivos .csv en ese prefijo.")
    st.stop()

# Estado persistente del índice
if "blob_index" not in st.session_state:
    st.session_state.blob_index = 0

# Botón para avanzar
if st.button("Procesar siguiente archivo"):
    if st.session_state.blob_index + 1 < len(blobs):
        st.session_state.blob_index += 1
    else:
        st.warning("No hay más archivos disponibles.")

actual_blob = blobs[st.session_state.blob_index]
st.success(f"Analizando: **{actual_blob}**")

# --------------------------------------------
# Cargar datos
# --------------------------------------------
df = load_gcs_blob(bucket, actual_blob)

st.subheader("Vista previa")
st.dataframe(df.head())

# --------------------------------------------
# Limpieza mínima
# --------------------------------------------
if "pickup_datetime" in df.columns:
    df["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"], errors="coerce")

if "trip_distance" in df.columns:
    df["trip_distance"] = pd.to_numeric(df["trip_distance"], errors="coerce")

# --------------------------------------------
# Histograma Altair
# --------------------------------------------
st.subheader("Distribución de distancias (p99)")

if "trip_distance" in df.columns:
    p99 = df["trip_distance"].quantile(0.99)
    df_plot = df[df["trip_distance"] <= p99]

    chart = (
        alt.Chart(df_plot)
        .mark_bar()
        .encode(
            alt.X("trip_distance:Q", bin=True, title="Distancia (millas)"),
            alt.Y("count()", title="Frecuencia"),
        )
        .properties(height=350)
    )

    st.altair_chart(chart, use_container_width=True)
else:
    st.info("El archivo no contiene trip_distance")

# --------------------------------------------
# Conteo por hora
# --------------------------------------------
if "pickup_datetime" in df.columns:
    st.subheader("Viajes por hora del día")
    
    df["hour"] = df["pickup_datetime"].dt.hour

    chart_hours = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("hour:O", title="Hora del día (0–23)"),
            y=alt.Y("count()", title="Número de viajes"),
        )
        .properties(height=350)
    )

    st.altair_chart(chart_hours, use_container_width=True)

# --------------------------------------------
# Matriz de correlación
# --------------------------------------------
st.subheader("Matriz de correlación numérica")

df_num = df.select_dtypes(include=["float64", "int64"])

if df_num.shape[1] > 1:
    corr = df_num.corr().reset_index().melt("index")
    corr.columns = ["var1", "var2", "value"]

    heatmap = (
        alt.Chart(corr)
        .mark_rect()
        .encode(
            x=alt.X("var1:N", title="Variable 1"),
            y=alt.Y("var2:N", title="Variable 2"),
            color=alt.Color("value:Q", scale=alt.Scale(scheme="redblue")),
            tooltip=["var1", "var2", alt.Tooltip("value:Q", format=".2f")],
        )
        .properties(height=450)
    )

    st.altair_chart(heatmap, use_container_width=True)
else:
    st.info("El archivo no contiene suficientes variables numéricas.")
