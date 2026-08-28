import time
import pandas as pd
import numpy as np
import yfinance as Ticker
import duckdb
from datetime import datetime

print("🚀 Iniciando Motor de Aplicación en Tiempo Real (Paper Trading)...")
print("Modo activo: Monitoreando EUR/USD en streaming simulado de 1 hora.\n")

DB_NAME = "eurusd_clean.duckdb"

def obtener_datos_en_vivo():
    """Descarga las últimas velas disponibles del mercado para evaluar el estado actual."""
    df = Ticker.download("EURUSD=X", period="5d", interval="1h", progress=False)
    df.reset_index(inplace=True)
    # Estandarizar nombres de columnas por compatibilidad
    df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
    if 'datetime' not in df.columns and 'date' in df.columns:
        df.rename(columns={'date': 'datetime'}, inplace=True)
    return df

def calcular_indicadores_activos(df):
    """Calcula Z-Score, ATR, RSI y ADX sobre la vela más reciente."""
    periodo_ma = 20
    df['rolling_mean'] = df['close'].rolling(window=periodo_ma).mean()
    df['rolling_std'] = df['close'].rolling(window=periodo_ma).std()
    df['z_score'] = (df['close'] - df['rolling_mean']) / df['rolling_std'].replace(0, np.nan)
    
    # ATR
    high, low, close = df['high'], df['low'], df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = true_range.ewm(alpha=1/14, adjust=False).mean()
    
    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['rsi'] = 100.0 - (100.0 / (1.0 + rs))
    
    # ADX simple
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

# Bucle principal de la aplicación en tiempo real (Paper Trading)
try:
    while True:
        timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp_actual}] 🔄 Consultando estado del mercado EUR/USD...")
        
        df = obtener_datos_en_vivo()
        df = calcular_indicadores_activos(df)
        
        # Tomar la penúltima vela cerrada para evitar ruido de la vela en curso
        ultima_vela = df.iloc[-2]
        
        precio_actual = ultima_vela['close']
        z_val = ultima_vela['z_score']
        rsi_val = ultima_vela['rsi']
        adx_val = ultima_vela['adx']
        
        print(f"   Precio: {precio_actual:.5f} | Z-Score: {z_val:.2f} | RSI: {rsi_val:.2f} | ADX: {adx_val:.2f}")
        
        # Evaluar filtros de alta convicción validados en investigación
        if z_val < -2.2 and adx_val < 25 and rsi_val < 30:
            print("   🚨 ¡SEÑAL DE COMPRA DETECTADA EN VIVO (Paper Trading)! 🚨")
            print(f"   -> Ejecutando orden simulada de compra a {precio_actual:.5f} con salida dinámica.")
            
            # Guardar registro en DuckDB para auditoría
            con = duckdb.connect(DB_NAME)
            con.execute("""
                CREATE TABLE IF NOT EXISTS operaciones_paper (
                    timestamp TIMESTAMP,
                    precio DOUBLE,
                    z_score DOUBLE,
                    rsi DOUBLE,
                    adx DOUBLE,
                    estado VARCHAR
                )
            """)
            con.execute("INSERT INTO operaciones_paper VALUES (?, ?, ?, ?, ?, ?)", 
                        [datetime.now(), precio_actual, z_val, rsi_val, adx_val, 'ABIERTA'])
            con.close()
            print("   💾 Operación registrada en la base de datos de papel.\n")
        else:
            print("   💤 Mercado en rango neutral o sin alta convicción. Esperando siguiente ciclo...\n")
            
        # Esperar 60 segundos antes de la siguiente verificación en vivo
        time.sleep(60)

except KeyboardInterrupt:
    print("\n🛑 Aplicación de Paper Trading detenida por el usuario de forma segura.")