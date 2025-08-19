from flask import Flask, request, jsonify
import numpy as np
import joblib

app = Flask(__name__)

# Load the trained Isolation Forest model
model = joblib.load("iso_forest_model.pkl")
print("✅ Model loaded successfully!")

@app.route("/analyze", methods=["POST"])
def analyze_heart_rate():
    data = request.get_json()

    # Check if heart_rate key exists
    if "heart_rate" not in data:
        return jsonify({"error": "Missing 'heart_rate' in request"}), 400

    hr_value = data["heart_rate"]

    try:
        hr_value = float(hr_value)
    except ValueError:
        return jsonify({"error": "Invalid heart_rate value, must be numeric"}), 400

    # Reshape to fit model input
    hr_array = np.array([[hr_value]])

    prediction = model.predict(hr_array)

    if prediction[0] == 1:
        result = "Normal"
    else:
        result = "Anomaly detected"

    return jsonify({
        "heart_rate": hr_value,
        "status": result
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
