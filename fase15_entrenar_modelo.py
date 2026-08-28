import duckdb
import pandas as pd
import numpy as np
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

print("🧠 [Fase 15 - Versión Macro-Tendencial] Entrenando XGBoost con filtro de tendencia macro...")

# 1. Cargar datos históricos limpios desde DuckDB
con = duckdb.connect("eurusd_clean.duckdb", read_only=True)
df = con.execute("SELECT * FROM matriz_con_targets").df()
con.close()

# Asegurar formato de fecha si existe la columna de tiempo
if 'datetime' in df.columns:
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['hora'] = df['datetime'].dt.hour
    df['dia_semana'] = df['datetime'].dt.dayofweek
else:
    df['hora'] = 12
    df['dia_semana'] = 2

# 2. Ingeniería de Características (Features) con Tendencia Macro
df['retorno_1h'] = df['close'].pct_change(1)
df['retorno_4h'] = df['close'].pct_change(4)
df['distancia_ma'] = (df['close'] - df['close'].rolling(20).mean()) / df['close'].rolling(20).std()

# NUEVO: Tendencia Macro (EMA de 200 periodos para evaluar la marea principal)
ema_200 = df['close'].ewm(span=200, adjust=False).mean()
df['tendencia_macro'] = np.where(df['close'] > ema_200, 1, 0) # 1 si está alcista macro, 0 si es bajista

# Volatilidad ampliada (Rango verdadero normalizado)
high, low, close = df['high'], df['low'], df['close']
tr1 = high - low
tr2 = (high - close.shift(1)).abs()
tr3 = (low - close.shift(1)).abs()
true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
df['atr_norm'] = true_range / close

df.dropna(inplace=True)

# Añadimos la tendencia macro al set de características
features = ['z_score', 'rsi', 'retorno_1h', 'retorno_4h', 'distancia_ma', 'hora', 'dia_semana', 'atr_norm', 'tendencia_macro']
X = df[features]
y = df['target_exito']

print(f"📊 Total de registros procesados con filtro macro: {len(X)}")
conteo_clases = y.value_counts()
clase_0 = conteo_clases.get(0, 1)
clase_1 = conteo_clases.get(1, 1)
peso_balanceo = clase_0 / clase_1

# 3. División estricta (70% entrenamiento, 30% prueba a ciegas sin barajar)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, shuffle=False)

# 4. Entrenar el modelo XGBoost optimizado
modelo = XGBClassifier(
    n_estimators=200, 
    max_depth=5, 
    learning_rate=0.02, 
    scale_pos_weight=peso_balanceo,
    random_state=42,
    eval_metric='logloss'
)
modelo.fit(X_train, y_train)

# 5. Evaluar en la zona de prueba a ciegas
y_pred = modelo.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print("\n" + "="*50)
print(" 🤖 RESULTADOS CON TENDENCIA MACRO (EMA 200) ")
print("="*50)
print(f"🎯 Precisión Global (Accuracy): {accuracy * 100:.2f}%")
print("-" * 50)
print(classification_report(y_test, y_pred))
print("="*50)

# 6. Analizar la nueva importancia de variables
importancias = pd.Series(modelo.feature_importances_, index=features).sort_values(ascending=False)
print("\n🔍 Importancia de las variables para la IA:")
print(importancias)

# 7. Guardar el modelo definitivo
joblib.dump(modelo, "modelo_xgboost.pkl")
print("\n💾 ¡Modelo macro-tendencial guardado exitosamente como 'modelo_xgboost.pkl'!")