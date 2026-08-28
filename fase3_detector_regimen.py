import duckdb
import pandas as pd

print("🔍 Ejecutando Detector de Régimen y Segmentación...")

# 1. Conectar a la base de datos
con = duckdb.connect("eurusd_clean.duckdb", read_only=True)
df = con.execute("SELECT * FROM matriz_con_targets").df()
con.close()

# 2. Clasificar el mercado según la volatilidad y el Z-Score (Reversión vs Tendencia)
# Definimos regímenes simples basados en Z-Score y la desviación
df['regimen'] = 'NEUTRAL'

# Si el precio está muy desviado de su media, es candidato a Reversión a la Media
df.loc[df['z_score'] > 1.5, 'regimen'] = 'OVERBOUGHT (Reversión Bajista)'
df.loc[df['z_score'] < -1.5, 'regimen'] = 'OVERSOLD (Reversión Alcista)'

print("\n📊 PROBABILIDAD DE ÉXITO SEGÚN EL RÉGIMEN DE MERCADO:")
print("-" * 60)

# 3. Evaluar la probabilidad de éxito (TP antes de SL) en cada régimen
resumen = df.groupby('regimen').agg(
    total_casos=('target_exito', 'count'),
    exitos=('target_exito', 'sum')
).reset_index()

resumen['probabilidad_%'] = (resumen['exitos'] / resumen['total_casos']) * 100
print(resumen.to_string(index=False))
print("-" * 60)