import yfinance as Ticker
import pandas as pd

print("📥 Descargando datos limpios de EUR/USD desde Yahoo Finance...")

# Descargar datos históricos de EUR/USD (ej. últimos 2 años a temporalidad de 1 hora o diaria para empezar limpio)
df = Ticker.download("EURUSD=X", period="2y", interval="1h")

# Limpiar formato de columnas
df.reset_index(inplace=True)
df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]

print(f"✅ ¡Datos descargados con éxito! Total de filas: {len(df)}")
print(df.head())

# Guardar en un CSV limpio y ordenado
df.to_csv("eurusd_limpio.csv", index=False)
print("💾 Archivo guardado como 'eurusd_limpio.csv'")