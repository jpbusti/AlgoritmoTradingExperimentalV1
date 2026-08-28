import time
import pandas as pd
import numpy as np
import yfinance as yf
import duckdb
import MetaTrader5 as mt5
from datetime import datetime

print("🚀 Iniciando Bot Cuantitativo Definitivo (Fase 12 - Producción Paper/Demo)...")
print("Modo activo: Monitoreando EUR/USD, calculando filtros y enlazado con MetaTrader 5.\n")

DB_NAME = "eurusd_clean.duckdb"
SIMBOLO = "EURUSD"

# 1. Inicializar Base de Datos Local (DuckDB)
con = duckdb.connect(DB_NAME)
con.execute("""
    CREATE TABLE IF NOT EXISTS operaciones_produccion (
        id BIGINT,
        timestamp VARCHAR,
        precio_entrada DOUBLE,
        atr_entrada DOUBLE,
        ticket_mt5 BIGINT,
        estado VARCHAR
    )
""")
con.close()

# 2. Inicializar MetaTrader 5
if not mt5.initialize():
    print(f"❌ Error crítico: No se pudo conectar a MetaTrader 5. Código: {mt5.last_error()}")
    quit()
else:
    print("✅ Conexión con MetaTrader 5 establecida correctamente para producción.")

def obtener_datos_en_vivo():
    """Descarga los últimos datos de la vela de 1 hora de EUR/USD."""
    try:
        df = yf.download("EURUSD=X", period="5d", interval="1h", progress=False)
        if df.empty:
            return None
        df.reset_index(inplace=True)
        df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
        if 'datetime' not in df.columns and 'date' in df.columns:
            df.rename(columns={'date': 'datetime'}, inplace=True)
        return df
    except Exception as e:
        print(f"⚠️ Advertencia al descargar datos de mercado: {e}")
        return None

def calcular_indicadores(df):
    """Calcula la matriz completa de indicadores técnicos en tiempo real."""
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

def ejecutar_orden_mt5(precio_actual, atr_actual):
    """Envía la orden real de compra a MT5 con gestión de riesgo integrada."""
    punto = mt5.symbol_info(SIMBOLO).point
    # Definimos SL y TP seguros basados en la volatilidad (ATR)
    sl = precio_actual - (1.5 * atr_actual)
    tp = precio_actual + (2.0 * atr_actual)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SIMBOLO,
        "volume": 0.1,
        "type": mt5.ORDER_TYPE_BUY,
        "price": precio_actual,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 999999,
        "comment": "Bot Cuantitativo Prod",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    resultado = mt5.order_send(request)
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Falló orden en MT5. Código error: {resultado.retcode}")
        return None
    else:
        print(f"✅ ¡Orden ejecutada en Bróker! Ticket: {resultado.order}")
        return resultado.order

# Bucle principal de ejecución autónoma
try:
    while True:
        timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp_actual}] 🔄 Consultando mercado en tiempo real...")
        
        df = obtener_datos_en_vivo()
        if df is not None and len(df) > 25:
            df = calcular_indicadores(df)
            ultima_vela = df.iloc[-2]
            
            precio_actual = ultima_vela['close']
            z_val = ultima_vela['z_score']
            rsi_val = ultima_vela['rsi']
            adx_val = ultima_vela['adx']
            atr_val = ultima_vela['atr']
            
            print(f"   Precio: {precio_actual:.5f} | Z-Score: {z_val:.2f} | RSI: {rsi_val:.2f} | ADX: {adx_val:.2f}")
            
            # Filtros estrictos de alta convicción (El francotirador)
            if z_val < -2.2 and adx_val < 25 and rsi_val < 30:
                print("   🚨 ¡SEÑAL DE ALTA CONVICCIÓN DETECTADA! Enviando orden a MetaTrader 5...")
                
                # Ejecutar en el bróker real (cuenta demo)
                ticket = ejecutar_orden_mt5(precio_actual, atr_val)
                
                if ticket:
                    # Registrar en DuckDB para auditoría y visualización
                    con = duckdb.connect(DB_NAME)
                    nuevo_id = int(time.time())
                    con.execute("INSERT INTO operaciones_produccion VALUES (?, ?, ?, ?, ?, ?)", 
                                [nuevo_id, timestamp_actual, precio_actual, atr_val, ticket, 'ABIERTA_MT5'])
                    con.close()
                    print(f"   -> Operación guardada exitosamente en la base de datos local.\n")
            else:
                print("   💤 Mercado en rango neutral o sin alta convicción. Esperando siguiente ciclo...\n")
        else:
            print("   ⚠️ No se pudieron obtener suficientes datos en este ciclo. Reintentando...")
            
        time.sleep(60)

except KeyboardInterrupt:
    print("\n🛑 Apagando el bot de producción de forma segura...")
    mt5.shutdown()
    print("🔌 Conexión con MT5 cerrada. ¡Hasta pronto!")