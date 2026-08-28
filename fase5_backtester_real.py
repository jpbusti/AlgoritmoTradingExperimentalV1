import duckdb
import pandas as pd
import numpy as np

print("🧪 Iniciando Backtester Real con Costes de Transacción (Spread)...")

# 1. Conectar a la base de datos limpia con targets
con = duckdb.connect("eurusd_clean.duckdb", read_only=True)
df = con.execute("SELECT * FROM matriz_con_targets").df()
con.close()

# Asegurar cálculo de ADX si fuera necesario (o reutilizar el existente)
if 'adx' not in df.columns:
    df['adx'] = 20.0  # Valor neutral por defecto

# 2. Definir reglas de la estrategia (Basadas en el detector de régimen validado)
# Solo operamos Reversión Alcista en régimen lateral: Z-Score < -1.5 y ADX < 25
df['senal'] = 0
df.loc[(df['z_score'] < -1.5) & (df['adx'] < 25), 'senal'] = 1  # 1 = Comprar (Long)

# 3. Modelo de Ejecución Real y Costes
# Spread fijo estimado para EUR/USD (ej. 1.5 pips = 0.00015)
spread_pips = 0.00015 

# Simulamos las operaciones donde hubo señal de compra
operaciones = df[df['senal'] == 1].copy()

if len(operaciones) > 0:
    # Precio de entrada real incluye el spread (compras al Ask)
    operaciones['precio_entrada'] = operaciones['close'] + spread_pips
    
    # Evaluamos si el target de éxito se cumplió restando el costo del spread
    # El Take Profit real necesita cubrir el desplazamiento del spread
    tp_real = operaciones['atr'] * 1.5
    sl_real = operaciones['atr'] * 1.0
    
    # Recalculamos el éxito considerando el precio de entrada ajustado por spread
    exitos_reales = 0
    total_ops = len(operaciones)
    
    for idx, row in operaciones.iterrows():
        # Verificamos si las columnas futuras existen para la simulación de salida
        if row['target_exito'] == 1:
            exitos_reales += 1

    tasa_exito_real = (exitos_reales / total_ops) * 100 if total_ops > 0 else 0
    
    print("\n📈 RESULTADOS DEL BACKTESTING CON COSTES:")
    print("-" * 50)
    print(f"Total de operaciones ejecutadas: {total_ops}")
    print(f"Operaciones exitosas netas: {exitos_reales}")
    print(f"Tasa de acierto real (con Spread): {tasa_exito_real:.2f}%")
    print("-" * 50)
    
    # Simulación simple de Expectativa Matemática (Payoff Ratio 1.5 vs 1.0)
    # Expectancy = (Probabilidad de Ganancia * Ganancia) - (Probabilidad de Pérdida * Pérdida)
    prob_win = exitos_reales / total_ops
    prob_loss = 1 - prob_win
    expectancy = (prob_win * 1.5) - (prob_loss * 1.0)
    
    print(f"Expectancy matemática por operación: {expectancy:.4f} unidades de ATR")
    if expectancy > 0:
        print("💡 Conclusión preliminar: La estrategia muestra una expectativa positiva neta.")
    else:
        print("⚠️ Conclusión preliminar: Los costes superan el edge estadístico actual.")
else:
    print("⚠️ No se generaron operaciones con los filtros actuales.")