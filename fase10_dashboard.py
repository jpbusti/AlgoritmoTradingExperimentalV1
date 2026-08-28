import streamlit as st
import duckdb
import pandas as pd
import datetime

# Configuración de la página del Dashboard
st.set_page_config(
    page_title="Dashboard Cuantitativo - EUR/USD",
    page_icon="📊",
    layout="wide"
)

DB_NAME = "eurusd_clean.duckdb"

st.title("📊 Panel de Control en Tiempo Real (Paper Trading)")
st.markdown("Monitoreo de rendimiento, operaciones activas y gestión dinámica del bot cuantitativo para EUR/USD.")

# Botón para refrescar datos manualmente
if st.button("🔄 Actualizar Datos"):
    st.rerun()

# Conectar a la base de datos y extraer las operaciones dinámicas
try:
    con = duckdb.connect(DB_NAME, read_only=True)
    # Verificamos si la tabla existe
    tablas = con.execute("SHOW TABLES").fetchall()
    tablas_nombres = [t[0] for t in tablas]
    
    if "operaciones_dinamicas" in tablas_nombres:
        df_ops = con.execute("SELECT * FROM operaciones_dinamicas").df()
    else:
        df_ops = pd.DataFrame(columns=['id', 'timestamp', 'precio_entrada', 'atr_entrada', 'estado'])
    con.close()
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    df_ops = pd.DataFrame()

# Métricas principales (KPIs)
st.subheader("📈 Resumen de Rendimiento")
col1, col2, col3, col4 = st.columns(4)

total_ops = len(df_ops)
abiertas = len(df_ops[df_ops['estado'] == 'ABIERTA']) if not df_ops.empty else 0
ganadas = len(df_ops[df_ops['estado'] == 'CERRADA_GANANCIA']) if not df_ops.empty else 0
perdidas = len(df_ops[df_ops['estado'] == 'CERRADA_PERDIDA']) if not df_ops.empty else 0

col1.metric("Total Operaciones", total_ops)
col2.metric("Operaciones Abiertas", abiertas)
col3.metric("Ganadas 🟢", ganadas)
col4.metric("Perdidas 🔴", perdidas)

st.markdown("---")

# Tabla detallada de operaciones
st.subheader("📋 Registro Histórico de Operaciones Dinámicas")
if not df_ops.empty:
    st.dataframe(df_ops.sort_values(by="timestamp", ascending=False), use_container_width=True)
else:
    st.info("ℹ️ Aún no hay operaciones registradas en la base de datos. Ejecuta el script de la Fase 9 para empezar a generar señales en vivo.")

# Pie de página informativo
st.markdown("---")
st.markdown("💡 *Nota: Mantén ejecutando tu script de la Fase 9 (`fase9_app_dinamica.py`) en segundo plano para que el bot continúe evaluando el mercado y actualizando este panel.*")