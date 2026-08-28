import duckdb
import pandas as pd
import numpy as np

print("📊 Iniciando Motor de Métricas Cuantitativas Avanzadas...")

# 1. Cargar datos históricos
con = duckdb.connect("eurusd_clean.duckdb", read_only=True)
df = con.execute("SELECT * FROM matriz_con_targets").df()
con.close()

# Asegurar que el indicador ADX esté calculado (para evitar errores si no se guardó antes)
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

# 2. Filtrar las señales que dispararía el bot (El Francotirador)
df['senal'] = 0
df.loc[(df['z_score'] < -2.2) & (df['adx'] < 25) & (df['rsi'] < 30), 'senal'] = 1
trades = df[df['senal'] == 1].copy()

print(f"🎯 Total de operaciones simuladas encontradas en el historial: {len(trades)}")

# 3. Simular la evolución de la cuenta
# Asumimos las reglas del bot en producción: Riesgo/Recompensa aprox de 1 : 1.33
# Simularemos que arriesgas $30 por operación (1% de tu cuenta demo de $3,000)
# Si ganas sumas +$40. Si pierdes restas -$30.

capital_inicial = 3000.0
capital_actual = capital_inicial
curva_capital = [capital_inicial]

ganancias_brutas = 0.0
perdidas_brutas = 0.0
wins = 0
losses = 0

for idx, row in trades.iterrows():
    if row['target_exito'] == 1:
        capital_actual += 40.0
        ganancias_brutas += 40.0
        wins += 1
    else:
        capital_actual -= 30.0
        perdidas_brutas += 30.0
        losses += 1
        
    curva_capital.append(capital_actual)

# 4. Cálculo de las métricas maestras
if len(trades) > 0:
    win_rate = (wins / len(trades)) * 100
    # Evitar división por cero
    profit_factor = ganancias_brutas / perdidas_brutas if perdidas_brutas > 0 else float('inf')
    
    # Calcular Max Drawdown (Matemática pura: la mayor caída porcentual desde un pico histórico)
    picos = np.maximum.accumulate(curva_capital)
    drawdowns = (curva_capital - picos) / picos * 100
    max_drawdown = drawdowns.min()

    # 5. Imprimir el Reporte Final
    print("\n" + "="*55)
    print(" 📈 REPORTE DE RENDIMIENTO (SISTEMA DE ALTA CONVICCIÓN) ")
    print("="*55)
    print(f"💰 Capital Inicial:      ${capital_inicial:,.2f}")
    print(f"🏦 Capital Final:        ${capital_actual:,.2f}")
    print(f"📊 Retorno Total:        {((capital_actual - capital_inicial) / capital_inicial) * 100:.2f}%")
    print("-" * 55)
    print(f"✅ Operaciones Ganadas:  {wins}")
    print(f"❌ Operaciones Perdidas: {losses}")
    print(f"🎯 Win Rate (Acierto):   {win_rate:.1f}%")
    print(f"⚖️ Profit Factor:        {profit_factor:.2f}")
    print(f"📉 Max Drawdown:         {max_drawdown:.2f}%")
    print("="*55)
    
    print("\n💡 INTERPRETACIÓN DEL INGENIERO:")
    if profit_factor > 1.0:
        print("-> Sistema RENTABLE. Generas más dólares de los que pierdes.")
    else:
        print("-> Sistema NO RENTABLE. Se necesita optimizar los filtros o el SL/TP.")
    
    if max_drawdown < -20.0:
        print("-> CUIDADO: El Drawdown es alto (riesgo de caídas fuertes). Considera reducir el tamaño del lote en MT5.")
    else:
        print("-> Excelente control de riesgo. Las caídas son manejables.")
else:
    print("No se encontraron operaciones con los filtros actuales.")