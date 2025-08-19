import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import matplotlib.pyplot as plt
csv_file_path = "iwatch_data_1.csv"  


df = pd.read_csv(csv_file_path)


df['heart_rate'] = pd.to_numeric(df['heart_rate'], errors='coerce')
df = df.dropna(subset=['heart_rate'])
print(df)
heart_rates = df[['heart_rate']].values
iso_forest = IsolationForest(contamination=0.1, random_state=42)
iso_forest.fit(heart_rates)
joblib.dump(iso_forest, 'iso_forest_model.pkl')
print("✅ Model trained and saved as iso_forest_model.pkl")
loaded_model = joblib.load('iso_forest_model.pkl')
print("✅ Model loaded successfully")

heart= df['heart_rate'].tolist()
new_heart_rates_array = np.array(heart).reshape(-1, 1)
predictions = loaded_model.predict(new_heart_rates_array)

for hr, pred in zip(new_heart_rates_array, predictions):
    if pred == 1:
        print(f"Heart rate {hr}: ✅ Normal")
    else:
        print(f"Heart rate {hr}: ⚠️ Anomaly detected!")
mask_normal = predictions == 1
mask_anomaly = predictions == -1

# Plot
plt.figure(figsize=(10, 6))
plt.scatter(df.index[mask_normal], heart_rates[mask_normal], c='green', label='Normal')
plt.scatter(df.index[mask_anomaly], heart_rates[mask_anomaly], c='red', label='Anomaly')

plt.title('Heart Rate Anomaly Detection')
plt.xlabel('Index')
plt.ylabel('Heart Rate')
plt.legend()
plt.grid(True)
plt.show()
