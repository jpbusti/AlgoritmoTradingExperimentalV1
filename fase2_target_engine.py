import duckdb
import pandas as pd
import numpy as np

print("🎯 Iniciando Motor de Etiquetas (Target Engine)...")

# 1. Conectar a la base de datos limpia
con = duckdb.connect("eurusd_clean.duckdb", read_only=False)
df = con.execute("SELECT * FROM matriz_features").df()

# 2. Definir el evento objetivo (Target)
# Horizonte de evaluación: siguientes 5 velas
horizonte = 5
df['future_high'] = df['high'].shift(-horizonte).rolling(horizonte).max()
df['future_low'] = df['low'].shift(-horizonte).rolling(horizonte).min()

# Supongamos una operación de Compra (Long):
# ¿El precio sube al menos 1 ATR (Take Profit) antes de caer 1 ATR (Stop Loss)?
atr_actual = df['atr']
precio_entrada = df['close']

tp_distance = atr_actual * 1.5
sl_distance = atr_actual * 1.0

# Etiqueta binaria: 1 si toca TP antes que SL, 0 en caso contrario
# (Simplificación matemática para medir la ventaja estadística inicial)
df['target_exito'] = np.where(
    (df['future_high'] >= (precio_entrada + tp_distance)) & 
    (df['future_low'] > (precio_entrada - sl_distance)), 1, 0
)

# Limpiar nulos del final de la serie
df = df.dropna().reset_index(drop=True)

# 3. Guardar las etiquetas en la base de datos
con.execute("CREATE OR REPLACE TABLE matriz_con_targets AS SELECT * FROM df")
total_etiquetados = con.execute("SELECT COUNT(*) FROM matriz_con_targets").fetchone()[0]
con.close()

# Estadísticas rápidas del Target
exitos = df['target_exito'].sum()
tasa_exito = (exitos / total_etiquetados) * 100

print(f"\n📊 RESULTADO DEL TARGET ENGINE:")
print(f"Total de muestras etiquetadas: {total_etiquetados}")
print(f"Probabilidad bruta de éxito (TP antes de SL): {tasa_exito:.2f}%")
print("💾 Guardado en 'eurusd_clean.duckdb' bajo la tabla 'matriz_con_targets'.")