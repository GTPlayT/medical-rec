from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup
import re
import json
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
import numpy as np
from flask_cors import CORS
import concurrent
from concurrent.futures import ThreadPoolExecutor

@dataclass
class APIConstants:
    google_api = ""
    gemini_api = ""

model = SentenceTransformer("all-MiniLM-L6-v2")
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)



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


def fetch_doctor_profile(profile_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    
    response = requests.get(profile_url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        name_tag = soup.find('h1', {'data-qa-id': 'doctor-name'})
        doctor_name = name_tag.get_text(strip=True) if name_tag else 'N/A'

        specializations_tag = soup.find('div', {'data-qa-id': 'doctor-specializations'})
        if specializations_tag:
            specialization_text = specializations_tag.get_text(strip=True)
            experience_match = re.search(r'(\d+)\s*Years', specialization_text)
            experience = experience_match.group(1) + ' Years' if experience_match else 'N/A'
            specializations = re.sub(r'\d+\s*Years.*', '', specialization_text).strip()
        else:
            specializations = 'N/A'
            experience = 'N/A'

        image_tag = soup.find('img', {'data-qa-id': 'doctor-profile-image'})
        if image_tag:
            full_image_url = image_tag['src']
            profile_image_url = full_image_url.split('?')[0]
        else:
            profile_image_url = 'N/A'

        fee_tag = soup.find('div', class_='u-f-right u-large-font u-bold u-valign--middle u-lheight-normal')
        if fee_tag:
            fee_text = fee_tag.get_text(strip=True)
            consultation_fee = re.sub(r'[^\d]', '', fee_text)
        else:
            consultation_fee = 'N/A'

        summary_tag = soup.find('div', {'data-qa-id': 'doctor-summary'})
        if summary_tag:
            more_button = summary_tag.find('span', {'data-qa-id': 'summary-more'})
            if more_button:
                more_button.extract()
            doctor_summary = summary_tag.get_text(strip=True)
        else:
            doctor_summary = 'N/A'

        directions_tag = soup.find('a', {'data-qa-id': 'get-directions'})
        if directions_tag and 'href' in directions_tag.attrs:
            directions_url = directions_tag['href']
            lat_lng_match = re.search(r'place/([-.\d]+),([-.\d]+)', directions_url)
            if lat_lng_match:
                latitude = lat_lng_match.group(1)
                longitude = lat_lng_match.group(2)
                clinic_location = {'latitude': latitude, 'longitude': longitude}
            else:
                clinic_location = 'N/A'
        else:
            clinic_location = 'N/A'

        address_tag = soup.find('p', {'class': 'c-profile--clinic__address', 'data-qa-id': 'clinic-address'})
        clinic_address = address_tag.get_text(strip=True) if address_tag else 'N/A'
        
        return {
            'name': doctor_name,
            'specializations': specializations,
            'experience': experience,
            'profile_image_url': profile_image_url,
            'consultation_fee': consultation_fee,
            'summary': doctor_summary,
            'clinic_location': clinic_location,
            'clinic_address': clinic_address,
            'profile_url': profile_url
        }
    else:
        print(f"Failed to retrieve profile data: {response.status_code}")
        return None
    
def prompt_generate(doctor):
    prompt = (
        "### Instruction: \n"
        "You are a Doctor recommendation expert. "
        "Your job is to go through what a Doctor has written about themselves and summarize it. "
        "You will be given Doctor's name, experience, specializations, experience and their clinic location. "
        "Use this information to generate a good summary while highlight the things mentioned in bold. "
        "You may use ** ** to highlight these information. "
        "### Input: \n"
        f"Doctor's name: {doctor['name']} \n"
        f"Doctor's specializations: {doctor['specializations']} \n"
        f"Doctor's experience: {doctor['experience']} \n"
        f"Doctor's self summary: {doctor['summary']} \n"
        f"Doctor's clinic's address: {doctor['clinic_address']} \n"
        "### Output: \n"
    )
    return prompt

def doctor_summary(doctor):
    doctor_prompt = prompt_generate(doctor)
    base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    try:
        payload = {
            "contents": [{
                "parts": [{"text": doctor_prompt}]
            }]
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(
            f"{base_url}?key={APIConstants.gemini_api}",
            headers=headers,
            data=json.dumps(payload)
        )
        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
                return generated_text
        else:
            return f"Error: {response.status_code}, {response.text}"
    except Exception as e:
        return f"An error occurred while generating content: {e}"

def find_doctors(lat, lng, rad, speciality):
    doctors = find_doctors_google(lat, lng, rad)
    cities = set()
    localities = set()

    for doctor in doctors:
        cities.add(format_string(doctor['city']))
        localities.add(format_string(doctor['locality']))

    def fetch_doctors_by_city(city):
        fetched_doctors = []
        doctors = practo_search(city, speciality)
        for doctor in doctors:
            if doctor['locality'] in localities:
                fetched_doctors.append(doctor)
        return fetched_doctors

    def fetch_profiles(doctor):
        return fetch_doctor_profile(doctor['profile'])

    def add_summary(doctor):
        summary = doctor_summary(doctor)  
        doctor['generated_summary'] = summary
        return doctor

    final_doctors = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        all_doctors = []

        future_to_city = {executor.submit(fetch_doctors_by_city, city): city for city in cities}
        for future in concurrent.futures.as_completed(future_to_city):
            all_doctors.extend(future.result())

        future_to_profiles = [executor.submit(fetch_profiles, doctor) for doctor in all_doctors]
        intermediate_doctors = []
        for future in concurrent.futures.as_completed(future_to_profiles):
            intermediate_doctors.append(future.result())

        future_to_summaries = [executor.submit(add_summary, doctor) for doctor in intermediate_doctors]
        for future in concurrent.futures.as_completed(future_to_summaries):
            final_doctors.append(future.result())

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

    symptom_embeddings = model.encode([symptoms] * len(practo_specializations), convert_to_numpy=True)
    specialization_embeddings = model.encode(practo_specializations, convert_to_numpy=True)
    max_match_index = np.argmax([np.dot(symptom_embeddings[i], specialization_embeddings[i]) for i in range(len(practo_specializations))])

    speciality = practo_specializations[max_match_index]
    doctors = find_doctors(lat, lng, radius, speciality)
    return jsonify(doctors)

@app.route('/')
def homepage():
    return render_template('homepage.html')

if __name__ == '__main__':
    app.run(debug=True)