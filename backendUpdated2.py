from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
import numpy as np
from flask_cors import CORS  # Import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@dataclass
class APIConstants:
    postman_api = ""
    collection_uid = ""
    google_api = ""

practo_specializations = [
    "ophthalmologist",
    "dermatologist",
    "cardiologist",
    "psychiatrist",
    "gastroenterologist",
    "ear-nose-throat-ent-specialist",
    "gynecologist-obstetrician",
    "neurologist",
    "urologist",
    "dentist",
    "prosthodontist",
    "orthodontist",
    "pediatric-dentist",
    "endodontist",
    "implantologist"
]

def format_string(string: str):
    return string.lower().replace(" ", "-")

def find_doctors_google(latitude, longitude, radius=500):
    base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": APIConstants.google_api,
        "location": f"{latitude},{longitude}",
        "radius": radius,
        "keyword": "doctor",
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        results = response.json().get("results", [])
        doctors = []
        for result in results:
            doctor_info = {
                "name": result.get("name"),
                "type": result.get("types", []),
                "address": result.get("vicinity"),
                "locality": result.get("vicinity").split(",")[-2].strip() if result.get("vicinity") and len(result.get("vicinity").split(",")) > 1 else None,
                "city": result.get("vicinity").split(",")[-1].strip() if result.get("vicinity") else None,
                "rating": result.get("rating"),
                "user_ratings_total": result.get("user_ratings_total"),
                "opening_hours": result.get("opening_hours", {}).get("weekday_text", []),
                "lat": result.get("geometry", {}).get("location", {}).get("lat"),
                "lng": result.get("geometry", {}).get("location", {}).get("lng"),
            }
            doctors.append(doctor_info)
        return doctors
    else:
        return {"error": f"Error: {response.status_code}, {response.text}"}

def practo_search(city, speciality):
    doctors = []
    for page in range(1, 4):
        url = f"https://www.practo.com/{city}/{speciality}?page={page}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            doctor_cards = soup.find_all('div', class_='listing-doctor-card')
            if not doctor_cards:
                break
            for card in doctor_cards:
                doctor_name_tag = card.find('h2', {'data-qa-id': 'doctor_name'})
                doctor_name = doctor_name_tag.get_text(strip=True) if doctor_name_tag else 'N/A'

                experience_tag = card.find('div', {'data-qa-id': 'doctor_experience'})
                doctor_experience = experience_tag.get_text(strip=True) if experience_tag else 'N/A'

                locality_tag = card.find('span', {'data-qa-id': 'practice_locality'})
                practice_locality = locality_tag.get_text(strip=True) if locality_tag else 'N/A'

                city_tag = card.find('span', {'data-qa-id': 'practice_city'})
                practice_city = city_tag.get_text(strip=True) if city_tag else 'N/A'

                profile_link_tag = card.find('a', href=True)
                profile_link = f"https://www.practo.com{profile_link_tag['href']}" if profile_link_tag else 'N/A'

                doctor = {
                    'name': doctor_name,
                    'experience': doctor_experience,
                    'locality': format_string(practice_locality[:-1]),
                    'city': format_string(practice_city),
                    'profile': profile_link
                }
                doctors.append(doctor)
        else:
            break
    return doctors

def find_doctors(lat, lng, rad, speciality):
    doctors = find_doctors_google(lat, lng, rad)
    cities = set()
    localities = set()
    for doctor in doctors:
        cities.add(format_string(doctor['city']))
        localities.add(format_string(doctor['locality']))
    final_doctors = []
    for city in cities:
        doctors = practo_search(city, speciality)
        for doctor in doctors:
            if doctor['locality'] in localities:
                final_doctors.append(doctor)
    return final_doctors

@app.route('/find-doctors', methods=['POST'])
def find_doctors_endpoint():
    data = request.json
    lat = data.get('latitude')
    lng = data.get('longitude')
    radius = data.get('radius', 5000)
    speciality = data.get('speciality', "doctor")
    doctors = find_doctors(lat, lng, radius, speciality)
    return jsonify(doctors)

@app.route('/find-doctors-by-symptoms', methods=['POST'])
def find_doctors_by_symptoms():
    data = request.json
    lat = data.get('latitude')
    lng = data.get('longitude')
    radius = data.get('radius', 5000)
    symptoms = data.get('symptoms')

    if not symptoms:
        return jsonify({"error": "Symptoms are required"}), 400

    model = SentenceTransformer("all-MiniLM-L6-v2")
    symptom_embeddings = model.encode([symptoms] * len(practo_specializations), convert_to_numpy=True)
    specialization_embeddings = model.encode(practo_specializations, convert_to_numpy=True)
    max_match_index = np.argmax([np.dot(symptom_embeddings[i], specialization_embeddings[i]) for i in range(len(practo_specializations))])

    speciality = practo_specializations[max_match_index]
    doctors = find_doctors(lat, lng, radius, speciality)
    return jsonify(doctors)

if __name__ == '__main__':
    app.run(debug=True)