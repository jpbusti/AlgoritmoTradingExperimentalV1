import duckdb
import pandas as pd
import numpy as np

print("🔍 Calculando ADX al vuelo y aplicando Filtro de Regimen...")

# 1. Conectar a la base de datos limpia con targets
con = duckdb.connect("eurusd_clean.duckdb", read_only=False)
df = con.execute("SELECT * FROM matriz_con_targets").df()

# 2. Calcular ADX si no está presente en las columnas
if 'adx' not in df.columns:
    high, low, close = df['high'], df['low'], df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Wilder smoothing para ADX de 14 periodos
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

# 3. Segmentación avanzada: Z-Score + ADX
df['filtro_mercado'] = 'OTRO'
df.loc[(df['z_score'] < -1.5) & (df['adx'] < 25), 'filtro_mercado'] = 'OVERSOLD + Lateral (ADX<25)'
df.loc[(df['z_score'] > 1.5) & (df['adx'] < 25), 'filtro_mercado'] = 'OVERBOUGHT + Lateral (ADX<25)'
df.loc[(df['adx'] >= 25), 'filtro_mercado'] = 'Tendencia Fuerte (ADX>=25 - No operar Reversión)'

print("\n📊 PROBABILIDAD FILTRADA POR ADX Y Z-SCORE:")
print("-" * 75)

resumen = df.groupby('filtro_mercado').agg(
    total_casos=('target_exito', 'count'),
    exitos=('target_exito', 'sum')
).reset_index()

resumen['probabilidad_%'] = (resumen['exitos'] / resumen['total_casos']) * 100
print(resumen.to_string(index=False))
print("-" * 75)
con.close()