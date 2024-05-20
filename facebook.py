import json
from selenium import webdriver
from bs4 import BeautifulSoup
import time
from geopy.geocoders import Nominatim
import re
from datetime import datetime, timedelta
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

def scroll_to_bottom(driver, max_scroll=1):
    for _ in range(max_scroll):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

def format_date(date_str):
    print("Original date string:", date_str)
    if not date_str:
        print("Erro: String de data vazia.")
        return None

    patterns = [
        (r"(\w+) (\d+) AT (\d{1,2}:\d{2}\s*(?:AM|PM)) – (\w+) (\d+) AT (\d{1,2}:\d{2}\s*(?:AM|PM)) (\d{4}) EDT", '%b'),
        (r"(\w+), (\w+) (\d+), (\d{4}) AT (\d{1,2}:\d{2}\s*(?:AM|PM)) – (\d{1,2}:\d{2}\s*(?:AM|PM))", '%B')
    ]

    for pattern, month_format in patterns:
        match = re.match(pattern, date_str)
        if match:
            if len(match.groups()) == 7:
                start_month, start_day, start_time, end_month, end_day, end_time, year = match.groups()
            elif len(match.groups()) == 6:
                day_of_week, start_month, start_day, year, start_time, end_time = match.groups()
                end_day = start_day
                end_month = start_month  # Use start_month as end_month for single-day events

            start_date = datetime.strptime(f"{start_day} {start_month} {year} {start_time}", f"%d %B %Y %I:%M %p")
            end_date = datetime.strptime(f"{end_day} {end_month} {year} {end_time}", f"%d %B %Y %I:%M %p")

            if end_date <= start_date:
                end_date += timedelta(days=1)

            formatted_start_date = start_date.strftime("%d/%m/%Y at %I:%M %p")
            formatted_end_date = end_date.strftime("%d/%m/%Y at %I:%M %p")
            print("Formatted start date:", formatted_start_date)
            print("Formatted end date:", formatted_end_date)
            return (formatted_start_date, formatted_end_date)

    print("Erro: Formato de data inválido.")
    return None

def get_street_address(location):
    # Regular expression pattern to match street address
    pattern = r'^(\d+\s[A-Za-zÀ-ÿ0-9\s-]+)'

    # Try to find the street address pattern in the location string
    match = re.match(pattern, location)
    if match:
        return match.group(1)
    else:
        return None

def get_coordinates(location_text):
    if location_text is None:
        print("Localização não encontrada para o evento.")
        return None, None

    geolocator = Nominatim(user_agent="event_scraper")

    # Tenta obter as coordenadas diretamente na cidade de Montreal
    try:
        location_obj = geolocator.geocode(location_text + ", Montreal, Quebec", exactly_one=True)
        if location_obj:
            return location_obj.latitude, location_obj.longitude
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Erro ao obter coordenadas para {location_text}: {e}")

    # Se a tentativa direta falhar, tenta obter as coordenadas de partes do endereço
    try:
        # Extrai o nome da rua do endereço
        street_address = location_text.split(',')[0]
        street_location = geolocator.geocode(street_address + ", Montreal, Quebec", exactly_one=True)
        if street_location:
            return street_location.latitude, street_location.longitude
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Erro ao obter coordenadas para {street_address}: {e}")

    # Se ainda não conseguir obter coordenadas, retorna None
    print(f"Não foi possível obter coordenadas para {location_text}")
    return None, None


def open_google_maps(latitude, longitude):
    return f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"

def get_location_details(latitude, longitude):
    geolocator = Nominatim(user_agent="event_scraper")
    try:
        location = geolocator.reverse((latitude, longitude), exactly_one=True)
        if location:
            # address = location.address
            city = location.raw.get('address', {}).get('city')
            country_code = location.raw.get('address', {}).get('country_code')
            return city, country_code
        else:
            return None, None, None
    except Exception as e:
        print(f"An error occurred while fetching location details: {e}")
        return None, None, None



def scrape_facebook_events(driver, url, selectors, max_scroll=30):
    driver.get(url)
    driver.implicitly_wait(20)  # Wait for elements to load
    all_events = []
    unique_event_titles = set()
    scroll_to_bottom(driver, max_scroll)
    page_content = driver.page_source
    webpage = BeautifulSoup(page_content, 'html.parser')
    events = webpage.find_all(selectors['event']['tag'], class_=selectors['event'].get('class'))

    for event in events:
        event_link = event.find('a', href=True)
        if not event_link:
            continue

        event_url = 'https://www.facebook.com' + event_link['href'] if event_link['href'].startswith('/') else event_link['href']
        driver.get(event_url)
        time.sleep(1)  # Allow event page to load
        event_page_content = driver.page_source
        event_page = BeautifulSoup(event_page_content, 'html.parser')

        event_title_elem = event_page.find('span', class_='x1lliihq x6ikm8r x10wlt62 x1n2onr6')
        if event_title_elem:
            event_title = event_title_elem.text.strip()
            if event_title in unique_event_titles:
                driver.back()
                continue
            unique_event_titles.add(event_title)
        else:
            driver.back()
            continue

        description = event_page.find('div', class_='xdj266r x11i5rnm xat24cr x1mh8g0r x1vvkbs').text.strip() if event_page.find('div', class_='xdj266r x11i5rnm xat24cr x1mh8g0r x1vvkbs') else None

        location_div = event_page.find('div', class_='x1i10hfl xjbqb8w x1ejq31n xd10rxx x1sy0etr x17r0tee x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz x1sur9pj xkrqix3 xzsf02u x1s688f')
        location_text = location_div.text.strip() if location_div else None

        # Ignore locations with text "See More..."
        if location_text and location_text.lower() == "see more":
            location_text = None

        latitude, longitude = get_coordinates(location_text)
        google_maps_url = open_google_maps(latitude, longitude)

        location_details = {
            'Location': location_text,
            'Latitude': latitude,
            'Longitude': longitude,
            'GoogleMaps_URL': google_maps_url
        }

        city, country_code = get_location_details(latitude, longitude)

        location_details['City'] = city
        location_details['CountryCode'] = country_code

        if city is None and country_code is None:
            location_details['City'] = 'Montreal'
            location_details['CountryCode'] = 'ca'

        date_text = event_page.find('div', class_='x1e56ztr x1xmf6yo').text.strip() if event_page.find('div', class_='x1e56ztr x1xmf6yo') else None
        print("Date text:", date_text)  # Add this line for debugging

        if date_text:
            match = re.search(r'(\d{1,2}:\d{2}\s?[AP]M)\s?–\s?(\d{1,2}:\d{2}\s?[AP]M)', date_text)
            if match:
                start_time, end_time = match.groups()
            else:
                if "at" in date_text.lower():
                    start_time = re.search(r'(\d{1,2}:\d{2}\s?[AP]M)', date_text).group(1)
                    end_time = None
                else:
                    start_time, end_time = None, None
        else:
            start_time, end_time = None, None

        if event_title is None or date_text is None or location_text is None:
            # Ignorar eventos com campos nulos
            driver.back()
            continue

        event_info = {
            'Title': event_title,
            'Description': description,
            'Date': format_date(date_text),  # Corrected to pass the original date
            'StartTime': start_time,
            'EndTime': end_time,
            **location_details,
            'EventUrl': event_url,
            'ImageURL': event_page.find('img', class_='xz74otr x1ey2m1c x9f619 xds687c x5yr21d x10l6tqk x17qophe x13vifvy xh8yej3')['src'] if event_page.find('img', class_='xz74otr x1ey2m1c x9f619 xds687c x5yr21d x10l6tqk x17qophe x13vifvy xh8yej3') else None,
            'Organizer': event_page.find('span', class_='xt0psk2').text.strip() if event_page.find('span', class_='xt0psk2') else None,
            'Organizer_IMG': event_page.find('img', class_='xz74otr')['src'] if event_page.find('img', class_='xz74otr') else None
        }

        # Call generate_tags function here passing event title and description
        # event_tags = generate_tags(event_title, description)
        # event_info['Tags'] = event_tags

        all_events.append(event_info)
        unique_event_titles.add(event_title)

        driver.back()

    return all_events if all_events else None

if __name__ == "__main__":
    sources = [
        {
            'name': 'Facebook',
            'url': 'https://www.facebook.com/events/explore/montreal-quebec/102184499823699/',
            'selectors': {
                'event': {'tag': 'div', 'class': 'x1qjc9v5 x9f619 x78zum5 xdt5ytf x5yr21d x6ikm8r x10wlt62 xexx8yu x10ogl3i xg8j3zb x1k2j06m xlyipyv xh8yej3'}
            }
        }
    ]

    driver = webdriver.Chrome()

    all_events = []
    for source in sources:
        print(f"Scraping events from: {source['name']}")
        if source['name'] == 'Facebook':
            events = scrape_facebook_events(driver, source['url'], source['selectors'])
            if events is not None:
                all_events.extend(events)
            else:
                print("No events found.")

    # Filtrar eventos com campos nulos
    all_events = [event for event in all_events if all(event.get(key) is not None for key in ['Title', 'Date', 'Location'])]

    # Save events to JSON file
    with open('facebook.json', 'w') as f:
        json.dump(all_events, f, indent=4)

    driver.quit()
