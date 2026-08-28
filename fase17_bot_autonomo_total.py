import time
import os
import duckdb
import joblib
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from datetime import datetime

print("🚀 [Fase 17 - Producción Definitiva] Iniciando Bot Autónomo con Datos de MT5 en Tiempo Real")

DB_NAME = "eurusd_clean.duckdb"
SIMBOLO = "EURUSD"
UMBRAL_PROBABILIDAD = 0.75# Umbral de confianza configurado para pruebas (ej. 50% o 0.75)

# 1. Setup Base de Datos de Auditoría (DuckDB)
con = duckdb.connect(DB_NAME)
con.execute("""
    CREATE TABLE IF NOT EXISTS operaciones_ml_produccion (
        id BIGINT, timestamp VARCHAR, precio_entrada DOUBLE, 
        probabilidad_ia DOUBLE, ticket_mt5 BIGINT, estado VARCHAR
    )
""")
con.close()

# 2. Setup Conexión con MetaTrader 5
if not mt5.initialize():
    print(f"❌ Error crítico conectando con MT5: {mt5.last_error()}")
    quit()

print("✅ Conexión con MetaTrader 5 establecida para piloto automático.")

if not os.path.exists("modelo_xgboost.pkl"):
    print("❌ Archivo 'modelo_xgboost.pkl' no encontrado. Deteniendo sistema.")
    mt5.shutdown()
    quit()

modelo = joblib.load("modelo_xgboost.pkl")

# Función de cálculo de ATR dinámico
def calcular_atr_actual(df):
    high, low, close = df['high'], df['low'], df['close']
    true_range = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    return true_range.ewm(alpha=1/14, adjust=False).mean().iloc[-2]

# Función blindada de ejecución en dos pasos (Orden limpia + Asignación posterior de Stops)
def ejecutar_orden_mt5(precio_actual, atr_actual):
    simbolo_info = mt5.symbol_info(SIMBOLO)
    if simbolo_info is None:
        print(f"❌ Símbolo {SIMBOLO} no encontrado en MT5.")
        return None

    tick_actual = mt5.symbol_info_tick(SIMBOLO)
    precio_ask = tick_actual.ask if tick_actual else precio_actual

    # Paso 1: Enviar orden de compra limpia para evitar el error 10016 del bróker
    request_orden = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SIMBOLO,
        "volume": 0.1,
        "type": mt5.ORDER_TYPE_BUY,
        "price": precio_ask,
        "deviation": 20,
        "magic": 999999,
        "comment": "Bot IA XGBoost Live",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    resultado = mt5.order_send(request_orden)
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Falló la orden en MT5. Código error: {resultado.retcode}")
        return None
    
    ticket_orden = resultado.order
    print(f"✅ ¡Orden ejecutada con éxito! Ticket: {ticket_orden}")

    # Paso 2: Calcular niveles de protección (SL y TP) usando el ATR dinámico
    punto = simbolo_info.point
    stops_level = max(simbolo_info.trade_stops_level * punto, atr_actual * 1.5)
    
    sl = round(resultado.price - stops_level, simbolo_info.digits)
    tp = round(resultado.price + (2.0 * atr_actual), simbolo_info.digits)

    # Paso 3: Asignar SL y TP a la posición abierta
    request_modificacion = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": SIMBOLO,
        "position": ticket_orden,
        "sl": sl,
        "tp": tp,
    }

    res_mod = mt5.order_send(request_modificacion)
    if res_mod.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"🛡️ Protección aplicada con éxito -> Stop Loss: {sl} | Take Profit: {tp}")
    else:
        print(f"⚠️ La orden abrió, pero falló la asignación de stops. Código error: {res_mod.retcode}")

    return ticket_orden

# 3. Bucle Principal Algorítmico en Tiempo Real (Poll Rate: 60s)
try:
    while True:
        timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Extracción de datos en tiempo real directo desde MetaTrader 5 (Evita bloqueos de Yahoo)
        rates = mt5.copy_rates_from_pos(SIMBOLO, mt5.TIMEFRAME_H1, 0, 150)
        
        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            df['datetime'] = pd.to_datetime(df['time'], unit='s')
            df.drop(['time', 'spread', 'real_volume'], axis=1, errors='ignore', inplace=True)
            df.columns = [col.lower() for col in df.columns]

            # Ingeniería de Características Vectorizada
            dt_actual = pd.to_datetime(df['datetime'].iloc[-1])
            df['rolling_mean'] = df['close'].rolling(20).mean()
            df['rolling_std'] = df['close'].rolling(20).std()
            df['z_score'] = (df['close'] - df['rolling_mean']) / df['rolling_std'].replace(0, np.nan)
            
            delta = df['close'].diff()
            rs = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean() / (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().replace(0, np.nan)
            df['rsi'] = 100.0 - (100.0 / (1.0 + rs))

            df['retorno_1h'] = df['close'].pct_change(1)
            df['retorno_4h'] = df['close'].pct_change(4)
            df['distancia_ma'] = (df['close'] - df['rolling_mean']) / df['rolling_std']
            df['tendencia_macro'] = np.where(df['close'] > df['close'].ewm(span=200, adjust=False).mean(), 1, 0)
            
            atr_val = calcular_atr_actual(df)
            df['atr_norm'] = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift(1)).abs(), (df['low'] - df['close'].shift(1)).abs()], axis=1).max(axis=1) / df['close']

            # Tomar la última vela activa
            ultima_vela = df.iloc[-1]
            
            # Vector de inferencia con las 9 características exactas
            X_live = pd.DataFrame([{
                'z_score': ultima_vela['z_score'], 'rsi': ultima_vela['rsi'],
                'retorno_1h': ultima_vela['retorno_1h'], 'retorno_4h': ultima_vela['retorno_4h'],
                'distancia_ma': ultima_vela['distancia_ma'], 'hora': dt_actual.hour,
                'dia_semana': dt_actual.dayofweek, 'atr_norm': ultima_vela['atr_norm'],
                'tendencia_macro': ultima_vela['tendencia_macro']
            }])
            
            # Inferencia de Probabilidad con el modelo XGBoost
            prob_exito = modelo.predict_proba(X_live)[0][1]
            print(f"[{timestamp_actual}] 🤖 Precio en vivo: {ultima_vela['close']:.5f} | Confianza de la IA: {prob_exito * 100:.2f}%")

            # Ejecución basada en el umbral configurado
            if prob_exito >= UMBRAL_PROBABILIDAD:
                print("   🚨 ¡ALTA CONVICCIÓN DETECTADA! Disparando orden a MetaTrader 5...")
                ticket = ejecutar_orden_mt5(ultima_vela['close'], atr_val)
                if ticket:
                    duckdb.connect(DB_NAME).execute(
                        "INSERT INTO operaciones_ml_produccion VALUES (?, ?, ?, ?, ?, ?)", 
                        [int(time.time()), timestamp_actual, ultima_vela['close'], float(prob_exito), ticket, 'ABIERTA_IA']
                    ).close()
            else:
                print("   💤 Confianza por debajo del umbral. El bot se mantiene en modo defensivo...\n")
        else:
            print("⚠️ No se pudieron obtener datos desde MetaTrader 5. Reintentando...")
        
        time.sleep(35)  # Poll Rate de 35 segundos para evitar bloqueos y respetar límites de MT5

except KeyboardInterrupt:
    mt5.shutdown()
    print("\n🔴 Apagando el bot autónomo de forma segura...")
    print("🔌 Conexión con MT5 cerrada. ¡Sistema detenido!")