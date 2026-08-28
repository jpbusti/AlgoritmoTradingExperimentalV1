import pandas as pd
import numpy as np
import yfinance as yf
import joblib
import os

print("🔍 [Fase 16] Probando el motor de inferencia en vivo con Machine Learning...")

def evaluar_mercado_en_vivo():
    if not os.path.exists("modelo_xgboost.pkl"):
        print("❌ Error: No se encontró el modelo entrenado. Ejecuta primero la Fase 15.")
        return None

    # Cargar el modelo guardado
    modelo = joblib.load("modelo_xgboost.pkl")

    # Descargar datos recientes del EUR/USD
    df = yf.download("EURUSD=X", period="5d", interval="1h", progress=False)
    if df.empty:
        print("⚠️ No se pudieron descargar datos del mercado.")
        return None

    df.reset_index(inplace=True)
    df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
    if 'datetime' not in df.columns and 'date' in df.columns:
        df.rename(columns={'date': 'datetime'}, inplace=True)

    # Calcular indicadores y características en tiempo real
    periodo_ma = 20
    df['rolling_mean'] = df['close'].rolling(window=periodo_ma).mean()
    df['rolling_std'] = df['close'].rolling(window=periodo_ma).std()
    df['z_score'] = (df['close'] - df['rolling_mean']) / df['rolling_std'].replace(0, np.nan)
    
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['rsi'] = 100.0 - (100.0 / (1.0 + rs))

    df['retorno_1h'] = df['close'].pct_change(1)
    df['retorno_4h'] = df['close'].pct_change(4)
    df['distancia_ma'] = (df['close'] - df['rolling_mean']) / df['rolling_std']

    # Tomar la última vela cerrada
    ultima_vela = df.iloc[-2]
    
    # Extraer las features exactas que espera el modelo
    features = ['z_score', 'rsi', 'retorno_1h', 'retorno_4h', 'distancia_ma']
    X_live = pd.DataFrame([ultima_vela[features]])

    # Predecir la probabilidad de éxito (clase 1)
    probabilidades = modelo.predict_proba(X_live)[0]
    prob_exito = probabilidades[1] # Probabilidad de éxito

    print(f"📊 Análisis de la última vela -> Precio: {ultima_vela['close']:.5f} | Probabilidad de Éxito de la IA: {prob_exito * 100:.2f}%")
    
    return prob_exito

if __name__ == "__main__":
    evaluar_mercado_en_vivo()