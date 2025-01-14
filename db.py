import concurrent
from concurrent.futures import ThreadPoolExecutor
import re 
import requests
import json
from bs4 import BeautifulSoup

import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import asyncio

from typing import Optional, List

from constants import APIConstants, practo_specializations

class Doctor:
    def __init__ (
        self,
        name: Optional[str] = None,
        specializations: Optional[str] = None,
        experience: Optional[str] = None,
        profile_image_url: Optional[str] = None,
        consultation_fee: Optional[str] = None,
        summary: Optional[str] = None,
        generated_summary: Optional[str] = None,
        profile_url: Optional[str] = None,
        address: Optional[str] = None,
        landmark: Optional[str] = None,
        locality: Optional[str] = None,
        city: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None
    ):
        self.name = name
        self.specializations = specializations
        self.experience = experience
        self.profile_image_url = profile_image_url
        self.consultation_fee = consultation_fee
        self.summary = summary
        self.generated_summary = generated_summary
        self.profile_url = profile_url
        self.address = address
        self.landmark = landmark
        self.locality = locality
        self.city = city
        self.lat = lat 
        self.lng = lng
    
    def to_json(self):
        return {
            "name": self.name,
            "specializations": self.specializations,
            "experience": self.experience,
            "profile_image_url": self.profile_image_url,
            "consultation_fee": self.consultation_fee,
            "summary": self.summary,
            "generated_summary": self.generated_summary,
            "profile_url": self.profile_url,
            "address": self.address,
            "landmark": self.landmark,
            "locality": self.locality,
            "city": self.city,
            "lat": self.lat,
            "lng": self.lng
        }


def format_string(string: str):
    return string.lower().replace(" ", "-")


def find_localities_google(latitude, longitude, radius=500):
    base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": APIConstants.google_api,
        "location": f"{latitude},{longitude}",
        "radius": radius,
        "keyword": "business OR landmark OR locality"
    }

    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        results = response.json().get("results", [])
        localities = []
        for result in results:
            address = result.get("vicinity")
            locality = address.split(",")[-2].strip() if address and len(address.split(",")) > 1 else None
            city = address.split(",")[-1].strip() if address else None

            localities.append({
                "name": result.get("name"),
                "locality": format_string(locality),
                "city": format_string(city),
                "address": address,
                "type": result.get("types", []),
            })
        return localities
    else:
        return {"error": f"Error: {response.status_code}, {response.text}"}


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
            doctors.append(Doctor( 
                locality=doctor_info["locality"],
                city=doctor_info["city"],
                ))
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

                doctors.append(Doctor(
                    name=doctor_name,
                    experience=doctor_experience,
                    locality=format_string(practice_locality[:-1]),
                    city=format_string(practice_city),
                    profile_url=profile_link
                ))
        else:
            break
    return doctors


def fetch_doctor_profile(doctor: Doctor):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = requests.get(doctor.profile_url, headers=headers)
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
            else:
                latitude = None
                longitude = None
        else:
            latitude = None
            longitude = None

        address_tag = soup.find('p', {'class': 'c-profile--clinic__address', 'data-qa-id': 'clinic-address'})
        clinic_address = address_tag.get_text(strip=True) if address_tag else 'N/A'

       
        address = clinic_address
        landmark = None

        if "Landmark: " in clinic_address:
            parts = clinic_address.split("Landmark: ")
            address = parts[0].strip()
            landmark = parts[1].strip()

        return Doctor(
            name=doctor_name,
            specializations=specializations,
            experience=experience,
            profile_image_url=profile_image_url,
            consultation_fee=consultation_fee,
            generated_summary = doctor_summary,
            profile_url=doctor.profile_url,
            address=address,
            landmark=landmark,
            locality=doctor.locality,
            city=doctor.city,
            lat=latitude,
            lng=longitude,
        )
        
    else:
        print(f"Failed to retrieve profile data: {response.status_code}")
        return None
    
def prompt_generate(doctor: Doctor):
    prompt = (
        "### Instruction: \n"
        "You are a Doctor recommendation expert. "
        "Your job is to go through what a Doctor has written about themselves and summarize it. "
        "You will be given Doctor's name, experience, specializations, experience and their clinic location. "
        "Use this information to generate a good summary and keep it short while highlight the things mentioned in bold. "
        "You may use ** ** to highlight these information. "
        "### Input: \n"
        f"Doctor's name: {doctor.name} \n"
        f"Doctor's specializations: {doctor.specializations} \n"
        f"Doctor's experience: {doctor.experience} \n"
        f"Doctor's self summary: {doctor.summary} \n"
        f"Doctor's consultation fee in Rupees: {doctor.consultation_fee} \n"
        "### Output: \n"
    )
    return prompt

def doctor_summary(doctor: Doctor):
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
                doctor.generated_summary = generated_text
                return doctor
        else:
            return doctor
    except Exception as e:
        return f"An error occurred while generating content: {e}"

class RecDB:
    def __init__(self, db_root="db"):
        self.db_root = db_root
        self.doctors_folder = os.path.join(self.db_root, "doctors")
        self.customers_folder = os.path.join(self.db_root, "customers")

    def create_city_folder(self, city_name):
        city_path = os.path.join(self.doctors_folder, city_name)
        os.makedirs(city_path, exist_ok=True)
        return city_path
    
    def specialization_folder(self, city_name, specialization):
        city_path = self.create_city_folder(city_name)
        specialization_path = os.path.join(city_path, specialization)
        os.makedirs(specialization_path, exist_ok=True)
        return specialization_path
    
    async def add_doctors(self, doctors: List[Doctor], speciality):
        for doctor in doctors:
            path = self.specialization_folder(doctor.city, speciality)
            path += "/data.parquet"
            if doctor.city == "gurugram":
                print(doctor.to_json())
            try:
                df = pd.read_parquet(path)
            except FileNotFoundError:
                df = pd.DataFrame(
                    columns=[
                        'name', 
                        'specializations',
                        'experience', 
                        'profile_image_url', 
                        'consultation_fee', 
                        'summary', 
                        'generated_summary', 
                        'profile_url', 
                        'address', 
                        'landmark', 
                        'locality', 
                        'city', 
                        'lat', 
                        'lng'
                        ]
                )
            df = pd.concat([df, pd.DataFrame([doctor.to_json()])], ignore_index=True)
            df.to_parquet(path, index=False)

    async def work_saving_doctors(self, doctors: List[Doctor], speciality):
        final_doctors = []
        def fetch_profiles(doctor: Doctor):
            return fetch_doctor_profile(doctor)

        def add_summary(doctor: Doctor):
            doctor: Doctor = doctor_summary(doctor)  
            return doctor

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_profiles = [executor.submit(fetch_profiles, doctor) for doctor in doctors]
            intermediate_doctors = []
            for future in concurrent.futures.as_completed(future_to_profiles):
                intermediate_doctors.append(future.result())

            future_to_summaries = [executor.submit(add_summary, doctor) for doctor in intermediate_doctors]
            for future in concurrent.futures.as_completed(future_to_summaries):
                final_doctors.append(future.result())

        await self.add_doctors(final_doctors, speciality)
        

    async def get_doctors(self, lat, lng, rad, speciality):
        list_localities = find_localities_google(lat, lng, rad)\

        cities = set()
        localities = set()
        for locality in list_localities:
            cities.add(locality['city'])
            localities.add(locality['locality'])

        print(cities)
        print(localities)

        def fetch_doctors_by_city(city):
            locality_doctors = []
            other_loc_doctors = []
            def search_doctor(city, speciality):
                path = self.specialization_folder(city, speciality)
                path += "/data.parquet"
                try:
                    df = pd.read_parquet(path)
                    doctors = []
                    for _, row in df.iterrows():
                        doctor = Doctor(
                            name=row.get("name"),
                            specializations=row.get("specializations"),
                            experience=row.get("experience"),
                            profile_image_url=row.get("profile_image_url"),
                            consultation_fee=row.get("consultation_fee"),
                            summary=row.get("summary"),
                            generated_summary=row.get("generated_summary"),
                            profile_url=row.get("profile_url"),
                            address=row.get("address"),
                            landmark=row.get("landmark"),
                            locality=row.get("locality"),
                            city=row.get("city"),
                            lat=row.get("lat"),
                            lng=row.get("lng")
                        )
                        doctors.append(doctor)
                    return doctors
                except FileNotFoundError:
                    doctors: List[Doctor] = practo_search(city, speciality)
                    return doctors
                
            doctors: List[Doctor] = search_doctor(city, speciality) 
            for doctor in doctors:
                if doctor.locality in localities:
                    locality_doctors.append(doctor)
                else:
                    other_loc_doctors.append(doctor)
            return locality_doctors, other_loc_doctors

        def fetch_profiles(doctor: Doctor):
            return fetch_doctor_profile(doctor)

        def add_summary(doctor: Doctor):
            doctor: Doctor = doctor_summary(doctor)  
            return doctor

        all_other_doctors = []
        all_locality_doctors = []
        final_doctors = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            loop = asyncio.get_event_loop()
            future_to_city = {loop.run_in_executor(executor, fetch_doctors_by_city, city): city for city in cities}
            
            for future in asyncio.as_completed(future_to_city):
                result = await future
                all_locality_doctors.extend(result[0])
                all_other_doctors.extend(result[1])
        

            if all_locality_doctors and all_locality_doctors[0].generated_summary is not None:
                return [doctor.to_json() for doctor in all_locality_doctors]

            future_to_profiles = [loop.run_in_executor(executor, fetch_profiles, doctor) for doctor in all_locality_doctors]
            intermediate_doctors = [await future for future in asyncio.as_completed(future_to_profiles)]

            future_to_summaries = [loop.run_in_executor(executor, add_summary, doctor) for doctor in intermediate_doctors]
            final_doctors = [await future for future in asyncio.as_completed(future_to_summaries)]

        asyncio.create_task(self.add_doctors(final_doctors, speciality))
        asyncio.create_task(self.work_saving_doctors(all_other_doctors, speciality))

        return [doctor.to_json() for doctor in final_doctors]

    
if __name__ == "__main__":
    db = RecDB()
    asyncio.run(db.get_doctors(28.625628, 77.433421, 5000, "ophthalmologist"))
