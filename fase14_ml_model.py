import duckdb
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

print("🧠 Iniciando Motor de Machine Learning Cuantitativo (XGBoost)...")

# 1. Cargar datos históricos desde DuckDB
con = duckdb.connect("eurusd_clean.duckdb", read_only=True)
df = con.execute("SELECT * FROM matriz_con_targets").df()
con.close()

# 2. Ingeniería de Características (Features) para el modelo
# En lugar de una sola regla rígida, le damos al modelo múltiples dimensiones del mercado
df['retorno_1h'] = df['close'].pct_change(1)
df['retorno_4h'] = df['close'].pct_change(4)
df['distancia_ma'] = (df['close'] - df['close'].rolling(20).mean()) / df['close'].rolling(20).std()

# Limpiar valores nulos resultantes de los cálculos
df.dropna(inplace=True)

# Definir características (X) y la variable objetivo (y: si el target de éxito fue 1 o 0)
features = ['z_score', 'rsi', 'retorno_1h', 'retorno_4h', 'distancia_ma']
X = df[features]
y = df['target_exito']

print(f"📊 Total de registros procesados para entrenamiento: {len(X)}")

# 3. División estricta: Entrenamiento (70%) y Prueba a ciegas / Out-of-Sample (30%)
# El modelo NUNCA verá el 30% de prueba hasta el final para evitar trampas (overfitting)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, shuffle=False)

print(f"⚙️ Entrenando modelo con {len(X_train)} registros históricos...")
modelo = XGBClassifier(
    n_estimators=100, 
    max_depth=4, 
    learning_rate=0.05, 
    random_state=42,
    eval_metric='logloss'
)
modelo.fit(X_train, y_train)

# 4. Evaluación en la zona de prueba a ciegas (Out-of-Sample)
y_pred = modelo.predict(X_test)
y_pred_proba = modelo.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)

print("\n" + "="*50)
print(" 🤖 RESULTADOS DE LA EVALUACIÓN CIEGA (MACHINE LEARNING) ")
print("="*50)
print(f"🎯 Precisión Global (Accuracy): {accuracy * 100:.2f}%")
print("-" * 50)
print("Reporte de Clasificación detallado:")
print(classification_report(y_test, y_pred))
print("="*50)

# 5. Análisis de Importancia de Variables
importancias = pd.Series(modelo.feature_importances_, index=features).sort_values(ascending=False)
print("\n🔍 Qué indicador o variable le importa más al algoritmo:")
print(importancias)