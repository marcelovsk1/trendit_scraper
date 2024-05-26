import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup
from datetime import datetime
import geopy
from geopy.geocoders import Nominatim
import geopy.exc
from unidecode import unidecode
import requests
import re

def scroll_to_bottom(driver, max_clicks=5):
    for _ in range(max_clicks):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

def calculate_similarity(str1, str2):
    return fuzz.token_sort_ratio(str1, str2)

def format_date(date_str, source):
    if date_str is None:
        print("Data recebida é None")
        return None

    date_str_lower = date_str.lower()
    source_lower = source.lower()

    if source_lower == 'eventbrite':
        patterns = [
            r'(\w{3})\s*(\d{1,2})\s*·',
            r'(?:débute le\s+)?(\w{3})[.,]\s*(\d{1,2})\s*(\w{3,})\s*(\d{4})',
            r'Débute le \w{3}\., (\d{1,2}) (\w{3}) (\d{4})',
            r'(\w+), (\w+) (\d{1,2})',
            r'(\w+) (\d{1,2})',
            r'\w+, (\d{1,2}) (\w{3}) \d{4}',
            r'Débute le \w{3}\., (\d{1,2}) (\w{3}) (\d{4})',
            r'Débute le \w{3}\., (\d{1,2}) (\w{3}) (\d{4})',
            r'Débute le \w{3}\., (\d{1,2}) (\w{3,}) (\d{4})',
            r'(?:\w{3,9}, )?(\w+) (\d{1,2})',
            r'(\w{3}), (\w{3}) (\d{1,2}), (\d{4})',
            r'(\w{3}), (\w{3}) (\d{1,2}), (\d{4}) \d{1,2}:\d{2} [AP]M',
            r'(\w{3})\s*(\d{1,2}), (\d{4})',
            r'(\w{3})[.,]\s*(\d{1,2})\s*(\w{3})\s*(\d{4})\s*(\d{2}:\d{2})',
            r'(\w{3})[.,]\s*(\d{1,2})\s*(\w{3})\s*(\d{4})'
        ]

        for pattern in patterns:
            date_match = re.search(pattern, date_str)
            if date_match:
                try:
                    if len(date_match.groups()) == 2:
                        month, day = date_match.groups()
                        year = datetime.now().year
                    elif len(date_match.groups()) == 3:
                        if pattern == r'(\w+), (\w+) (\d{1,2})':
                            _, month, day = date_match.groups()
                            year = datetime.now().year
                        else:
                            day_of_week, month, day, year = date_match.groups()
                    else:
                        month_map = {
                            'jan': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'apr': 'Apr', 'may': 'May', 'jun': 'Jun', 'jul': 'Jul', 'aug': 'Aug', 'sep': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'dec': 'Dec',
                            'janv': 'Jan', 'févr': 'Feb', 'mars': 'Mar', 'avr': 'Apr', 'mai': 'May', 'juin': 'Jun', 'juil': 'Jul', 'août': 'Aug', 'sept': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'déc': 'Dec',
                            'ene': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'mayo': 'May', 'jun': 'Jun', 'jul': 'Jul', 'ago': 'Aug', 'sep': 'Sep', 'oct': 'Oct', 'nov': 'Dic'
                        }
                        day_of_week, day, month, year = date_match.groups()
                        month = month_map[month[:3].lower()]

                    date_str_formatted = f"{day} {month} {year}"
                    start_date = datetime.strptime(date_str_formatted, '%d %b %Y')
                    return start_date.strftime('%d/%m/%Y')
                except ValueError as e:
                    print(f"Erro ao converter a data: {e}")
                    continue
        print("Nenhuma correspondência encontrada na string de data")
        return None
    else:
        print("Fonte não suportada")
        return None

def format_location(location_str, source):
    if location_str is None:
        return {
            'Location': None,
            'Street': None,
            'City': None,
            'Province': None,
            'PostalCode': None,
            'CountryCode': None
        }

    if source == 'Facebook' or source == 'Eventbrite':
        return {
            'Location': location_str.strip(),
            'City': 'Montreal',
            'CountryCode': 'ca'
        }
    elif source == 'Google':
        api_key = 'YOUR_GOOGLE_API_KEY'
        url = f'https://maps.googleapis.com/maps/api/geocode/json?address={location_str}&key={api_key}'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'OK' and len(data['results']) > 0:
                result = data['results'][0]
                address_components = result['address_components']
                formatted_address = result['formatted_address']
                street = next((component['long_name'] for component in address_components if 'route' in component['types']), None)
                city = next((component['long_name'] for component in address_components if 'locality' in component['types']), None)
                province = next((component['short_name'] for component in address_components if 'administrative_area_level_1' in component['types']), None)
                postal_code = next((component['long_name'] for component in address_components if 'postal_code' in component['types']), None)
                country_code = next((component['short_name'] for component in address_components if 'country' in component['types']), None)

                return {
                    'Location': formatted_address.strip(),
                    'Street': street,
                    'City': city,
                    'Province': province,
                    'PostalCode': postal_code,
                    'CountryCode': country_code
                }

        return {
            'Location': location_str.strip(),
            'City': 'Montreal',
            'CountryCode': 'ca'
        }
    else:
        return {
            'Location': location_str.strip(),
            'City': 'Montreal',
            'CountryCode': 'ca'
        }

def extract_start_end_time(date_str):
    if date_str is None:
        return None, None

    if "-" not in date_str:
        start_time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)', date_str)
        if start_time_match:
            start_time = start_time_match.group(1)
            return start_time.strip(), None
        else:
            return None, None

    day_match = re.search(r'(\w+, \w+ \d{1,2}, \d{4} \d{1,2}:\d{2} (?:AM|PM))\s*-\s*(\w+, \w+ \d{1,2}, \d{4} \d{1,2}:\d{2} (?:AM|PM))', date_str)
    if day_match:
        start_time = day_match.group(1)
        end_time = day_match.group(2)
        return start_time.strip(), end_time.strip()

    date_str = re.sub(r'\b(?:lun(?:di)?|mon(?:day)?)\b', 'Monday', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\b(?:mar(?:di)?|tue(?:sday)?)\b', 'Tuesday', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\b(?:mer(?:credi)?|wed(?:nesday)?)\b', 'Wednesday', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\b(?:jeu(?:di)?|thu(?:rsday)?)\b', 'Thursday', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\b(?:ven(?:dredi)?|fri(?:day)?)\b', 'Friday', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\b(?:sam(?:edi)?|sat(?:urday)?)\b', 'Saturday', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\b(?:dim(?:anche)?|sun(?:day)?)\b', 'Sunday', date_str, flags=re.IGNORECASE)

    same_day_match = re.search(r'(\w+, \w+ \d{1,2}, \d{4} \d{1,2}:\d{2} (?:AM|PM))\s*-\s*(\d{1,2}:\d{2} (?:AM|PM))', date_str)
    if same_day_match:
        start_time = same_day_match.group(1)
        end_time = same_day_match.group(2)
        return start_time.strip(), end_time.strip()

    am_pm_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM))\s*-\s*(\d{1,2}:\d{2}\s*(?:AM|PM))', date_str)
    if am_pm_match:
        start_time, end_time = am_pm_match.groups()
        return start_time.strip(), end_time.strip()

    hrs_24_match = re.search(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', date_str)
    if hrs_24_match:
        start_time, end_time = hrs_24_match.groups()
        return start_time.strip(), end_time.strip()

    pm_match = re.search(r'(\d{1,2})pm', date_str, flags=re.IGNORECASE)
    if pm_match:
        start_hour = int(pm_match.group(1))
        if start_hour < 12:
            start_hour += 12
        start_time = f"{start_hour:02}:00"

        end_hour = start_hour + 2
        if end_hour >= 24:
            end_hour -= 12
        end_time = f"{end_hour:02}:00"

        return start_time.strip(), end_time

    am_match = re.search(r'(\d{1,2})am', date_str, flags=re.IGNORECASE)
    if am_match:
        start_hour = int(am_match.group(1))
        if start_hour == 12:
            start_hour = 0
        start_time = f"{start_hour:02}:00"

        end_hour = start_hour + 2
        if end_hour >= 12:
            end_hour -= 12
        end_time = f"{end_hour:02}:00"

        return start_time.strip(), end_time

    return None, None

def get_coordinates(location):
    geolocator = Nominatim(user_agent="event_scraper")
    retries = 3
    delay = 2

    if location is None:
        return None, None

    location = unidecode(location)

    for _ in range(retries):
        try:
            query_string = f"{location}, Montreal, Quebec, Canada"
            location = geolocator.geocode(query_string, addressdetails=True)
            if location:
                latitude = location.latitude
                longitude = location.longitude
                return latitude, longitude
            else:
                return None, None
        except geopy.exc.GeocoderUnavailable as e:
            time.sleep(delay)

    return None, None

def open_google_maps(latitude, longitude):
    google_maps_url = f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
    return google_maps_url

def scrape_eventbrite_events(driver, url, selectors, max_pages=20):
    driver.get(url)
    driver.implicitly_wait(20)

    all_events = []

    for _ in range(max_pages):
        try:
            page_content = driver.page_source
            webpage = BeautifulSoup(page_content, 'html.parser')
            events = webpage.find_all(selectors['event']['tag'], class_=selectors['event'].get('class'))

            for event in events:
                event_info = {}
                for key, selector in selectors.items():
                    if key != 'event':
                        element = event.find(selector['tag'], class_=selector.get('class'))
                        event_info[key] = element.text.strip() if element else None
                        if key == 'ImageURL':
                            img_element = event.find('img', class_='event-card__image')
                            event_info[key] = img_element['src'] if img_element and 'src' in img_element.attrs else None

                event_link_element = event.find('a', class_='event-card-link')
                if event_link_element:
                    event_link = event_link_element['href']
                    driver.get(event_link)
                    time.sleep(2)

                    try:
                        event_page_content = driver.page_source
                        event_page = BeautifulSoup(event_page_content, 'html.parser')

                        title_element = event_page.find('h1', class_='event-title css-0')
                        title = title_element.text.strip() if title_element else None

                        description_element = event_page.find('p', class_='summary')
                        description = description_element.text.strip() if description_element else None

                        price_default_element = event_page.find('div', class_='conversion-bar__panel-info')
                        if price_default_element:
                            price_default = price_default_element.text.strip()
                        else:
                            price_default = "undisclosed price"

                        price_element = event_page.find('span', class_='eds-text-bm eds-text-weight--heavy')
                        price = price_element.text.strip() if price_element else price_default

                        date_element = event_page.find('span', class_='date-info__full-datetime')
                        date = date_element.text.strip() if date_element else None

                        location_element = event_page.find('p', class_='location-info__address-text')
                        location = location_element.text.strip() if location_element else None

                        ImageURL = event.find('img', class_='event-card-image')['src']

                        price_number = None
                        if price:
                            price_matches = re.findall(r'\d+\.?\d*', price)
                            if price_matches:
                                price_number = float(price_matches[0])

                        latitude, longitude = get_coordinates(location)

                        organizer_element = event_page.find('div', class_='descriptive-organizer-info-mobile__name')
                        organizer = organizer_element.text.strip() if organizer_element else None

                        event_info['Title'] = title
                        event_info['Description'] = description
                        event_info['Price'] = price_number
                        event_info['Date'] = format_date(date, 'Eventbrite')
                        event_info['StartTime'], event_info['EndTime'] = extract_start_end_time(date)
                        event_info.update(format_location(location, 'Eventbrite'))
                        event_info['ImageURL'] = ImageURL
                        event_info['Latitude'] = latitude
                        event_info['Longitude'] = longitude
                        event_info['Organizer'] = organizer
                        event_info['EventUrl'] = event_link

                        if latitude is not None and longitude is not None:
                            map_url = open_google_maps(latitude, longitude)
                            event_info['GoogleMaps_URL'] = map_url

                        all_events.append(event_info)
                        print(f"Scraped event: {title}")

                    except Exception as e:
                        print(f"Error scraping event page: {e}")

                    finally:
                        driver.back()
                        time.sleep(2)
                else:
                    print("No event link found for event")

            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "button[data-spec='page-next']")
                next_button.click()
                time.sleep(3)
            except Exception as e:
                print("Error clicking next button or no more pages.")
                break

        except Exception as e:
            print(f"Error scraping events page: {e}")
            break

    return all_events

def main():
    sources = [
        {
            'name': 'Eventbrite',
            'url': 'https://www.eventbrite.com/d/canada--montreal/all-events/',
            'selectors': {
                'event': {'tag': 'div', 'class': 'discover-search-desktop-card'},
                'Title': {'tag': 'h2', 'class': 'event-card__title'},
                'Description': {'tag': 'p', 'class': 'event-card__description'},
                'Date': {'tag': 'p', 'class': 'event-card__date'},
                'Location': {'tag': 'p', 'class': 'location-info__address-text'},
                'Price': {'tag': 'p', 'class': 'event-card__price'},
                'ImageURL': {'tag': 'img', 'class': 'event-card__image'},
                'Organizer': {'tag': 'div', 'class': 'descriptive-organizer-info-mobile__name'}
            },
            'max_pages': 3
        }
    ]

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=chrome_options)

    all_events = []
    for source in sources:
        print(f"Scraping events from: {source['name']}")
        if source['name'] == 'Eventbrite':
            events = scrape_eventbrite_events(driver, source['url'], source['selectors'], source['max_pages'])
            events_with_data = [event for event in events if sum(1 for value in event.values() if value is not None) > 10]
            all_events.extend(events_with_data)
        else:
            print(f"Unsupported source: {source['name']}")
            continue

    with open('eventbrite.json', 'w') as f:
        json.dump(all_events, f, indent=4)

    driver.quit()

if __name__ == "__main__":
    main()