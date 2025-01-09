import requests
from bs4 import BeautifulSoup
import re
from dataclasses import dataclass

from sentence_transformers import SentenceTransformer
import numpy as np

@dataclass
class APIConstants:
    postman_api = "PMAK-677ff2c648c08b0001df02bf-ea7ee0a47c494d2d681361b0483309c11e"
    collection_uid = "26923816-960df2f2-e345-4209-98fc-f2e4f04a417d"
    google_api = "AIzaSyDAEjf-1pp9S7QW2lRVAsat5wMv52UlMmw"

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
                "html_attribution": re.search(r'href="(.*?)"', result.get("photos", [{}])[0].get("html_attributions", [])[0]).group(1) 
                if result.get("photos") and result.get("photos", [{}])[0].get("html_attributions") else None,
            }
            doctors.append(doctor_info)
        return doctors
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return []   

def practo_search(city, speciality):
    doctors = []

    for page in range(1, 4):
        url = f"https://www.practo.com/{city}/{speciality}?page={page}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        
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

def find_doctors(lat, lng, rad, speciality):
    doctors = find_doctors_google(lat, lng, rad)
    cities = set()
    localities = set()
    
    for doctor in doctors:
        cities.add(format_string(doctor['city']))
        localities.add(format_string(doctor['locality']))
    
    final_doctors = list()
    for city in cities:
        doctors = practo_search(city, speciality)
        for doctor in doctors:
            if doctor['locality'] in localities:
                final_doctors.append(doctor)

    for i, doctor in enumerate(final_doctors):
        doctor = fetch_doctor_profile(doctor['profile'])
        final_doctors[i] = doctor

    return final_doctors

def find_doctors_pipeline(lat, lng, rad, symptoms, model: SentenceTransformer):
    symptoms = [symptoms] * len(practo_specializations)
    emb1 = model.encode(symptom, convert_to_numpy=True)
    emb2 = model.encode(practo_specializations, convert_to_numpy=True)
    max_match = np.argmax(model.similarity(emb1, emb2).cpu().numpy())
    return find_doctors(lat, lng, rad, practo_specializations[max_match])
    


if __name__ == "__main__":
    symptom = str(input("How are you feeling today? > "))
    model = SentenceTransformer("all-MiniLM-L6-v2")
    doctors = find_doctors_pipeline(28.625628, 77.433419, 50000, symptom, model)
    print(doctors)