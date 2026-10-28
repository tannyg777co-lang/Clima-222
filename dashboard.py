import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
import streamlit as st


st.set_page_config(page_title="Clima | Dashboard", page_icon="🌦️", layout="wide")

GRIS = "#B9C3D1"
AZUL = "#1C4C9A"
ROJO = "#B2182B"
NARANJA = "#E69F00"
CIUDADES = {
    "Morelia": (19.7008, -101.1844),
    "Querétaro": (20.5888, -100.3899),
}
VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_max",
    "precipitation_sum",
    "precipitation_hours",
    "windspeed_10m_max",
    "shortwave_radiation_sum",
]

sns.set_theme(style="whitegrid")


@st.cache_data(ttl=3600, show_spinner=False)
def cargar_datos(ciudad):
    latitud, longitud = CIUDADES[ciudad]
    respuesta = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": latitud,
            "longitude": longitud,
            "start_date": "2021-01-01",
            "end_date": "2025-12-31",
            "daily": ",".join(VARIABLES),
            "timezone": "America/Mexico_City",
        },
        timeout=60,
    )
    respuesta.raise_for_status()
    datos = respuesta.json()
    df = pd.DataFrame(datos["daily"])
    df["time"] = pd.to_datetime(df["time"])
    df = df.rename(columns={
        "time": "Fecha",
        "temperature_2m_max": "TempMax",
        "temperature_2m_min": "TempMin",
        "temperature_2m_mean": "TempMedia",
        "apparent_temperature_max": "Sensacion",
        "precipitation_sum": "Lluvia",
        "precipitation_hours": "HorasLluvia",
        "windspeed_10m_max": "Viento",
        "shortwave_radiation_sum": "Radiacion",
    })
    df["Anio"] = df["Fecha"].dt.year
    df["Mes"] = df["Fecha"].dt.month
    df["Amplitud"] = df["TempMax"] - df["TempMin"]
    df["Temporada"] = df["Mes"].apply(
        lambda mes: "Lluvias" if 6 <= mes <= 10 else "Secas"
    )
    return df, datos["daily_units"]


st.title("Clima diario")
st.caption("Temperatura, lluvia y radiación solar · Datos históricos de Open-Meteo")

with st.sidebar:
    st.header("Filtros")
    ciudad = st.selectbox("Ciudad", list(CIUDADES))

try:
    with st.spinner(f"Cargando datos de {ciudad}…"):
        df, unidades = cargar_datos(ciudad)
except (requests.RequestException, KeyError, ValueError) as error:
    st.error(f"No se pudieron cargar los datos meteorológicos: {error}")
    st.stop()

with st.sidebar:
    anios_disponibles = sorted(df["Anio"].unique().tolist())
    anios = st.multiselect("Años", anios_disponibles, default=anios_disponibles)

if not anios:
    st.info("Selecciona al menos un año para mostrar las gráficas.")
    st.stop()

datos = df[df["Anio"].isin(anios)].copy()
ultimo_anio = max(anios)

metrica1, metrica2, metrica3, metrica4 = st.columns(4)
metrica1.metric("Días analizados", f"{len(datos):,}")
metrica2.metric("Temperatura media", f"{datos['TempMedia'].mean():.1f} {unidades['temperature_2m_mean']}")
metrica3.metric("Lluvia acumulada", f"{datos['Lluvia'].sum():,.0f} {unidades['precipitation_sum']}")
metrica4.metric("Radiación diaria media", f"{datos['Radiacion'].mean():.1f} {unidades['shortwave_radiation_sum']}")

st.divider()

columna1, columna2 = st.columns(2)

with columna1:
    st.subheader("1 · Banda de temperatura")
    st.caption(f"Temperaturas diarias de {ultimo_anio}")
    ultimo = datos[datos["Anio"] == ultimo_anio]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.fill_between(ultimo["Fecha"], ultimo["TempMin"], ultimo["TempMax"],
                    color=GRIS, label="Mínima a máxima")
    ax.plot(ultimo["Fecha"], ultimo["TempMedia"], color=AZUL,
            linewidth=1.5, label="Media")
    ax.set_xlabel("Fecha")
    ax.set_ylabel(f"Temperatura ({unidades['temperature_2m_mean']})")
    ax.legend(frameon=False)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

with columna2:
    st.subheader("2 · Lluvia y horas de lluvia")
    mensual_anio = datos.groupby(["Anio", "Mes"]).agg(
        Lluvia=("Lluvia", "sum"), Horas=("HorasLluvia", "sum")
    )
    mensual = mensual_anio.groupby("Mes").mean().reindex(range(1, 13))
    fig, ax = plt.subplots(figsize=(9, 4.2))
    colores = [AZUL if valor == mensual["Lluvia"].max() else GRIS
               for valor in mensual["Lluvia"]]
    ax.bar(mensual.index, mensual["Lluvia"], color=colores)
    ax.set_xlabel("Mes")
    ax.set_ylabel(f"Lluvia ({unidades['precipitation_sum']})")
    ax.set_xticks(range(1, 13))
    eje2 = ax.twinx()
    eje2.plot(mensual.index, mensual["Horas"], color=ROJO, marker="o",
              linewidth=2, markersize=4)
    eje2.set_ylabel("Horas con lluvia", color=ROJO)
    eje2.grid(False)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

columna3, columna4 = st.columns(2)

with columna3:
    st.subheader("3 · Amplitud térmica por mes")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    sns.boxplot(data=datos, x="Mes", y="Amplitud", color=GRIS, ax=ax)
    ax.set_xlabel("Mes")
    ax.set_ylabel(f"Máxima menos mínima ({unidades['temperature_2m_mean']})")
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

with columna4:
    st.subheader("4 · Radiación contra temperatura")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    sns.scatterplot(data=datos, x="Radiacion", y="TempMedia", s=18,
                    alpha=0.45, color=NARANJA, edgecolor=None, ax=ax)
    ax.set_xlabel(f"Radiación diaria ({unidades['shortwave_radiation_sum']})")
    ax.set_ylabel(f"Temperatura media ({unidades['temperature_2m_mean']})")
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

st.subheader("5 · Mapa de calor: mes por año")
calor = datos.pivot_table(index="Anio", columns="Mes", values="TempMedia",
                          aggfunc="mean").reindex(columns=range(1, 13))
meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
fig, ax = plt.subplots(figsize=(12, max(3.2, len(calor) * 0.65)))
sns.heatmap(
    calor, annot=True, fmt=".1f", cmap="YlOrRd", linewidths=0.5,
    linecolor="white", ax=ax,
    cbar_kws={"label": f"Temperatura media ({unidades['temperature_2m_mean']})"},
)
ax.set_xlabel("Mes")
ax.set_ylabel("Año")
ax.set_xticklabels(meses, rotation=0)
fig.tight_layout()
st.pyplot(fig, use_container_width=True)
plt.close(fig)

with st.expander("Consultar datos diarios"):
    st.dataframe(datos, use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar datos filtrados (CSV)",
        data=datos.to_csv(index=False).encode("utf-8"),
        file_name=f"clima_{ciudad.lower().replace('é', 'e')}.csv",
        mime="text/csv",
    )
