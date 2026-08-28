import MetaTrader5 as mt5
import pandas as pd
import duckdb
from datetime import datetime

print("🔌 Conectando con MetaTrader 5 para ejecución en Cuenta Demo...")

# 1. Inicializar la conexión con MetaTrader 5
if not mt5.initialize():
    print(f"❌ Falló la inicialización de MT5, código de error = {mt5.last_error()}")
    quit()
else:
    print("✅ ¡Conexión exitosa con la terminal de MetaTrader 5!")

# Mostrar información de la cuenta conectada para verificar
cuenta_info = mt5.account_info()
if cuenta_info is not None:
    print(f"👤 Cuenta: {cuenta_info.login} | Servidor: {cuenta_info.server} | Balance Demo: ${cuenta_info.balance:.2f} {cuenta_info.currency}")
else:
    print("⚠️ No se pudo obtener la información de la cuenta. Asegúrate de haber iniciado sesión en MT5.")

# 2. Configurar el símbolo con el que operaremos
simbolo = "EURUSD"

# Verificar si el símbolo está disponible en el Market Watch
info_simbolo = mt5.symbol_info(simbolo)
if info_simbolo is None:
    print(f"❌ El símbolo {simbolo} no está disponible en este bróker.")
    mt5.shutdown()
    quit()

if not info_simbolo.visible:
    print(f"🔍 El símbolo {simbolo} no está visible. Intentando habilitarlo...")
    if not mt5.symbol_select(simbolo, True):
        print(f"❌ Falló al habilitar {simbolo}")
        mt5.shutdown()
        quit()

print(f"🎯 Símbolo {simbolo} listo. Precio de compra actual (Ask): {info_simbolo.ask}")

# 3. Función de Prueba para Enviar una Orden de Compra a la Cuenta Demo
def enviar_orden_prueba_demo(lotes=0.1):
    print("\n🚀 Enviando orden de prueba (Buy Market) a la cuenta demo de MT5...")
    
    punto = mt5.symbol_info(simbolo).point
    precio_actual = mt5.symbol_info_tick(simbolo).ask
    sl = precio_actual - (300 * punto)  # Stop Loss de prueba
    tp = precio_actual + (600 * punto)  # Take Profit de prueba

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": simbolo,
        "volume": lotes,
        "type": mt5.ORDER_TYPE_BUY,
        "price": precio_actual,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 234000,
        "comment": "Bot Cuantitativo Python Demo",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    # Enviar la orden al servidor del bróker
    resultado = mt5.order_send(request)
    
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Falló el envío de la orden, retcode={resultado.retcode}")
        print(f"Detalle del error: {resultado.comment}")
    else:
        print(f"✅ ¡Orden ejecutada con éxito en la Cuenta Demo!")
        print( ticket := f"   Ticket de operación: {resultado.order} | Precio de ejecución: {resultado.price}" )

    return resultado

# Ejecutar la prueba del puente
resultado_prueba = enviar_orden_prueba_demo(lotes=0.1)

# Cerrar la conexión limpiamente al terminar la prueba
mt5.shutdown()
print("\n🔌 Conexión con MT5 cerrada de forma segura.")