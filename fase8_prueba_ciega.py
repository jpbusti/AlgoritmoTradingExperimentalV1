import duckdb
import pandas as pd
import numpy as np

print("🕵️‍♂️ Iniciando Prueba Ciega (Walk-Forward / Simulación en el Pasado)...")

# 1. Conectar a la base de datos limpia con targets
con = duckdb.connect("eurusd_clean.duckdb", read_only=True)
df = con.execute("SELECT * FROM matriz_con_targets").df()
con.close()

# 2. Asegurar que el indicador ADX esté calculado en el DataFrame
if 'adx' not in df.columns:
    high, low, close = df['high'], df['low'], df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    period = 14
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    atr_w = true_range.ewm(alpha=1.0/period, adjust=False).mean()
    p_di = 100.0 * pd.Series(plus_dm).ewm(alpha=1.0/period, adjust=False).mean() / atr_w
    m_di = 100.0 * pd.Series(minus_dm).ewm(alpha=1.0/period, adjust=False).mean() / atr_w
    dx = 100.0 * (p_di - m_di).abs() / (p_di + m_di).replace(0.0, np.nan)
    df['adx'] = dx.ewm(alpha=1.0/period, adjust=False).mean().fillna(20.0)

# 3. Elegir un punto de corte en el pasado
punto_corte = int(len(df) * 0.7)
df_pasado = df.iloc[:punto_corte].copy()

print(f"📅 Total de registros históricos analizados: {len(df)}")
print(f"✂️ Cortando datos en el registro #{punto_corte} para simular el 'presente' del pasado.")

# 4. Aplicar filtros de alta convicción
df_pasado['senal'] = 0
df_pasado.loc[(df_pasado['z_score'] < -2.2) & (df_pasado['adx'] < 25) & (df_pasado['rsi'] < 30), 'senal'] = 1

alertas_pasadas = df_pasado[df_pasado['senal'] == 1]

print(f"\n🚨 Alertas de alta convicción generadas en la simulación pasada: {len(alertas_pasadas)}")

if len(alertas_pasadas) > 0:
    print("\n🔍 AUDITORÍA DE LAS ÚLTIMAS SEÑALES EN EL PASADO:")
    print("-" * 65)
    
    exitos_ciegos = 0
    for idx, row in alertas_pasadas.tail(5).iterrows():
        fecha = row['datetime'] if 'datetime' in row else f"Índice {idx}"
        precio = row['close']
        z = row['z_score']
        exito = row['target_exito']
        
        if exito == 1:
            resultado_txt = "✅ ACIERTO (El precio rebotó como se esperaba)"
            exitos_ciegos += 1
        else:
            resultado_txt = "❌ FALLO (El mercado rompió en contra)"
            
        print(f"Fecha/ID: {fecha} | Precio: {precio:.5f} | Z: {z:.2f} -> {resultado_txt}")
        
    print("-" * 65)
    print(f"💡 Prueba completada con éxito.")
else:
    print("💤 No se encontraron alertas con estos filtros estrictos. Relaja el Z-score a -2.0 si lo deseas.")