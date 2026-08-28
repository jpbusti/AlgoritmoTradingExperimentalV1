import pandas as pd
import duckdb
import numpy as np

# 1. Cargar el archivo limpio generado por yfinance
print("📥 Cargando eurusd_limpio.csv...")
df = pd.read_csv("eurusd_limpio.csv")

# Verificar las columnas descargadas
print("Columnas detectadas:", df.columns.tolist())

# Asegurar formato de fecha
df['datetime'] = pd.to_datetime(df['datetime'] if 'datetime' in df.columns else df['date'])
df.sort_values('datetime', inplace=True)

# 2. Calcular Indicadores Clave (Feature Engine)
print("🧮 Calculando Z-Score, ATR, RSI y ADX...")

# Media móvil y desviación estándar para Reversión a la Media (Z-Score)
periodo_ma = 20
df['rolling_mean'] = df['close'].rolling(window=periodo_ma).mean()
df['rolling_std'] = df['close'].rolling(window=periodo_ma).std()
df['z_score'] = (df['close'] - df['rolling_mean']) / df['rolling_std'].replace(0, np.nan)

# ATR (Average True Range) de 14 periodos
high, low, close = df['high'], df['low'], df['close']
tr1 = high - low
tr2 = (high - close.shift(1)).abs()
tr3 = (low - close.shift(1)).abs()
true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
df['atr'] = true_range.ewm(alpha=1/14, adjust=False).mean()

# RSI de 14 periodos
delta = close.diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
rs = avg_gain / avg_loss.replace(0, np.nan)
df['rsi'] = 100.0 - (100.0 / (1.0 + rs))

# Limpiar valores nulos generados por las ventanas de los indicadores
df = df.dropna().reset_index(drop=True)

# 3. Persistencia en DuckDB optimizada
print("💾 Guardando la matriz limpia en DuckDB...")
db_name = "eurusd_clean.duckdb"
con = duckdb.connect(db_name)

con.execute("CREATE OR REPLACE TABLE matriz_features AS SELECT * FROM df")
con.execute("CREATE INDEX IF NOT EXISTS idx_zscore ON matriz_features(z_score)")
con.execute("CREATE INDEX IF NOT EXISTS idx_atr ON matriz_features(atr)")

total_filas = con.execute("SELECT COUNT(*) FROM matriz_features").fetchone()[0]
con.close()

print(f"\n🎉 ¡PROCESO EXITOSO! Se estructuraron y guardaron {total_filas} registros en '{db_name}'.")