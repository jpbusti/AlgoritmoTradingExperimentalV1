import time
import pandas as pd
import numpy as np
import yfinance as Ticker
import duckdb
from datetime import datetime

print("🚀 Iniciando Aplicación de Paper Trading con Gestión Dinámica...")
print("Modo activo: Monitoreando EUR/USD y gestionando posiciones abiertas.\n")

DB_NAME = "eurusd_clean.duckdb"

def obtener_datos_en_vivo():
    df = Ticker.download("EURUSD=X", period="5d", interval="1h", progress=False)
    df.reset_index(inplace=True)
    df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
    if 'datetime' not in df.columns and 'date' in df.columns:
        df.rename(columns={'date': 'datetime'}, inplace=True)
    return df

def calcular_indicadores_activos(df):
    periodo_ma = 20
    df['rolling_mean'] = df['close'].rolling(window=periodo_ma).mean()
    df['rolling_std'] = df['close'].rolling(window=periodo_ma).std()
    df['z_score'] = (df['close'] - df['rolling_mean']) / df['rolling_std'].replace(0, np.nan)
    
    high, low, close = df['high'], df['low'], df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = true_range.ewm(alpha=1/14, adjust=False).mean()
    
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['rsi'] = 100.0 - (100.0 / (1.0 + rs))
    
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
    
    return df

# Inicializar tabla de operaciones dinámicas si no existe
con = duckdb.connect(DB_NAME)
con.execute("""
    CREATE TABLE IF NOT EXISTS operaciones_dinamicas (
        id INTEGER,
        timestamp TIMESTAMP,
        precio_entrada DOUBLE,
        atr_entrada DOUBLE,
        estado VARCHAR
    )
""")
con.close()

try:
    while True:
        timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp_actual}] 🔄 Evaluando mercado EUR/USD y gestión de posiciones...")
        
        df = obtener_datos_en_vivo()
        df = calcular_indicadores_activos(df)
        
        ultima_vela = df.iloc[-2]
        precio_actual = ultima_vela['close']
        z_val = ultima_vela['z_score']
        rsi_val = ultima_vela['rsi']
        adx_val = ultima_vela['adx']
        atr_val = ultima_vela['atr']
        
        print(f"   Precio: {precio_actual:.5f} | Z-Score: {z_val:.2f} | RSI: {rsi_val:.2f} | ADX: {adx_val:.2f}")
        
        con = duckdb.connect(DB_NAME)
        
        # 1. GESTIÓN DE POSICIONES ABIERTAS (Revisar si deben cerrarse por tiempo o trailing)
        abiertas = con.execute("SELECT * FROM operaciones_dinamicas WHERE estado = 'ABIERTA'").fetchall()
        
        if len(abiertas) > 0:
            print(f"   🛡️ Gestionando {len(abiertas)} posición(es) abierta(s)...")
            for op in abiertas:
                op_id, op_time, precio_entrada, atr_entrada, estado = op
                # Regla dinámica: Cierre por tiempo de mercado (ej. si el precio actual superó 1.0 ATR de beneficio o cayó 0.8 ATR)
                delta_precio = precio_actual - precio_entrada
                
                if delta_precio >= (atr_entrada * 1.2):
                    print(f"   ✅ ¡Take Profit Dinámico alcanzado! Cerrando posición en ganancia a {precio_actual:.5f}")
                    con.execute("UPDATE operaciones_dinamicas SET estado = 'CERRADA_GANANCIA' WHERE id = ?", [op_id])
                elif delta_precio <= -(atr_entrada * 0.8):
                    print(f"   ❌ ¡Stop Loss dinámico alcanzado! Cortando pérdida en {precio_actual:.5f}")
                    con.execute("UPDATE operaciones_dinamicas SET estado = 'CERRADA_PERDIDA' WHERE id = ?", [op_id])
                else:
                    print(f"   ⏳ Posición #{op_id} en curso. Variación actual: {delta_precio:.5f}")
        
        # 2. BUSCAR NUEVAS ENTRADAS SI EL MERCADO DA LA SEÑAL
        if z_val < -2.2 and adx_val < 25 and rsi_val < 30:
            print("   🚨 ¡SEÑAL DE ALTA CONVICCIÓN DETECTADA!")
            nuevo_id = int(time.time())
            con.execute("INSERT INTO operaciones_dinamicas VALUES (?, ?, ?, ?, ?)", 
                        [nuevo_id, datetime.now(), precio_actual, atr_val, 'ABIERTA'])
            print(f"   -> Orden simulada abierta con ID {nuevo_id} a precio {precio_actual:.5f}\n")
        else:
            print("   💤 Sin señales de entrada nuevas. Esperando ciclo...\n")
            
        con.close()
        time.sleep(60)

except KeyboardInterrupt:
    print("\n🛑 Aplicación dinámica detenida de forma segura.")