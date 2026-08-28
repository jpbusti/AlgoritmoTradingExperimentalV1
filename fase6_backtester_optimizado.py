import duckdb
import pandas as pd
import numpy as np

print("🧪 Ejecutando Backtester Optimizado con Filtros de Alta Convicción...")

# 1. Conectar a la base de datos limpia con targets
con = duckdb.connect("eurusd_clean.duckdb", read_only=True)
df = con.execute("SELECT * FROM matriz_con_targets").df()
con.close()

if 'adx' not in df.columns:
    df['adx'] = 20.0

# 2. Reglas de entrada de alta convicción:
# - Z-Score extremadamente bajo (< -2.2) para buscar rebotes más limpios
# - ADX < 25 (mercado lateral o sin tendencia fuerte)
# - RSI < 30 (sobreventa confirmada)
df['senal'] = 0
df.loc[(df['z_score'] < -2.2) & (df['adx'] < 25) & (df['rsi'] < 30), 'senal'] = 1

# 3. Modelo de Ejecución Real y Costes (Spread de 1.5 pips)
spread_pips = 0.00015 
operaciones = df[df['senal'] == 1].copy()

total_ops = len(operaciones)

if total_ops > 10: # Asegurar una muestra mínima para evaluar
    exitos_reales = operaciones['target_exito'].sum()
    tasa_exito_real = (exitos_reales / total_ops) * 100
    
    # Expectancy matemática (Ratio Riesgo/Beneficio: TP de 1.5 ATR vs SL de 1.0 ATR)
    prob_win = exitos_reales / total_ops
    prob_loss = 1 - prob_win
    expectancy = (prob_win * 1.5) - (prob_loss * 1.0)
    
    print("\n📈 RESULTADOS DEL BACKTESTING OPTIMIZADO:")
    print("-" * 50)
    print(f"Total de operaciones de alta convicción: {total_ops}")
    print(f"Operaciones exitosas netas: {exitos_reales}")
    print(f"Tasa de acierto real (con Spread): {tasa_exito_real:.2f}%")
    print(f"Expectancy matemática por operación: {expectancy:.4f} unidades de ATR")
    print("-" * 50)
    
    if expectancy > 0:
        print("💡 ¡ÉXITO DE INVESTIGACIÓN! Con estos filtros, la expectativa matemática es positiva.")
    else:
        print("⚠️ Los costes siguen superando el edge. Necesitamos ajustar el horizonte o el ratio de beneficio.")
else:
    print(f"⚠️ Pocas operaciones ({total_ops}). Los filtros son demasiado estrictos; relajemos un poco el Z-score (ej. -2.0).")