from flask import Flask, request, jsonify, render_template
from sentence_transformers import SentenceTransformer
import numpy as np
from flask_cors import CORS

from constants import practo_specializations, APIConstants
from db import RecDB

db = RecDB()
model = SentenceTransformer("all-MiniLM-L6-v2")
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)


@app.route('/find-doctors-by-symptoms', methods=['POST'])
async def find_doctors_by_symptoms():
    data = request.json
    lat = data.get('latitude')
    lng = data.get('longitude')
    radius = data.get('radius', 5000)
    symptoms = data.get('symptoms')

    if not symptoms:
        return jsonify({"error": "Symptoms are required"}), 400

    symptom_embeddings = model.encode([symptoms] * len(practo_specializations), convert_to_numpy=True)
    specialization_embeddings = model.encode(practo_specializations, convert_to_numpy=True)
    max_match_index = np.argmax([np.dot(symptom_embeddings[i], specialization_embeddings[i]) for i in range(len(practo_specializations))])

    speciality = practo_specializations[max_match_index]
    doctors = await db.get_doctors(lat, lng, radius, speciality)
    return jsonify(doctors)

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/get-api-key')
def get_api_key():
    return jsonify({"api_key": APIConstants.google_api})


if __name__ == '__main__':
    app.run(debug=True)