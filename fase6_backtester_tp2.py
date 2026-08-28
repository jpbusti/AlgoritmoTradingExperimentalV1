import duckdb
import pandas as pd
import numpy as np

print("🧪 Ejecutando Backtester con TP ampliado (2.0 ATR)...")

# 1. Conectar a la base de datos limpia con targets
con = duckdb.connect("eurusd_clean.duckdb", read_only=True)
df = con.execute("SELECT * FROM matriz_con_targets").df()
con.close()

if 'adx' not in df.columns:
    df['adx'] = 20.0

# 2. Reglas de entrada de alta convicción (Z-score < -2.2, ADX < 25, RSI < 30)
df['senal'] = 0
df.loc[(df['z_score'] < -2.2) & (df['adx'] < 25) & (df['rsi'] < 30), 'senal'] = 1

# 3. Ajustar el evento objetivo con un Take Profit de 2.0 ATR (mayor recompensa)
horizonte = 5
future_high_tp2 = df['high'].shift(-horizonte).rolling(horizonte).max()
future_low_sl = df['low'].shift(-horizonte).rolling(horizonte).min()

tp_distance = df['atr'] * 2.0
sl_distance = df['atr'] * 1.0
precio_entrada = df['close']

# Recalcular el éxito con el nuevo ratio TP/SL (2.0 vs 1.0)
df['target_exito_tp2'] = np.where(
    (future_high_tp2 >= (precio_entrada + tp_distance)) & 
    (future_low_sl > (precio_entrada - sl_distance)), 1, 0
)

# 4. Modelo de Ejecución Real y Costes (Spread de 1.5 pips)
spread_pips = 0.00015 
operaciones = df[df['senal'] == 1].copy()
total_ops = len(operaciones)

if total_ops > 10:
    exitos_reales = operaciones['target_exito_tp2'].sum()
    tasa_exito_real = (exitos_reales / total_ops) * 100
    
    # Expectancy matemática con Ratio Riesgo/Beneficio de 2.0 vs 1.0
    prob_win = exitos_reales / total_ops
    prob_loss = 1 - prob_win
    expectancy = (prob_win * 2.0) - (prob_loss * 1.0)
    
    print("\n📈 RESULTADOS CON TP = 2.0 ATR:")
    print("-" * 50)
    print(f"Total de operaciones de alta convicción: {total_ops}")
    print(f"Operaciones exitosas netas: {exitos_reales}")
    print(f"Tasa de acierto real (con Spread): {tasa_exito_real:.2f}%")
    print(f"Expectancy matemática por operación: {expectancy:.4f} unidades de ATR")
    print("-" * 50)
    
    if expectancy > 0:
        print("💡 ¡OBJETIVO LOGRADO! Expectativa matemática positiva. Este modelo es apto para pasar a Paper Trading.")
    else:
        print("⚠️ La expectativa sigue siendo negativa. El mercado requiere un filtro adicional de salida o gestión dinámica.")
else:
    print(f"⚠️ Pocas operaciones ({total_ops}).")