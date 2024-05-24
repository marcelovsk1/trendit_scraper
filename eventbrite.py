import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
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
        # Tentando capturar datas que podem incluir o começo de eventos em um dia e terminar em outro
        patterns = [
            r'(\w{3})\s*(\d{1,2})\s*·',  # 'May 19 · 10pm'
            r'(?:débute le\s+)?(\w{3})[.,]\s*(\d{1,2})\s*(\w{3,})\s*(\d{4})',  # 'Débute le lun., 27 mai 2024'
            r'Débute le \w{3}\., (\d{1,2}) (\w{3}) (\d{4})',
            r'(\w+), (\w+) (\d{1,2})',
            r'(\w+) (\d{1,2})',
            r'\w+, (\d{1,2}) (\w{3}) \d{4}',
            r'Débute le \w{3}\., (\d{1,2}) (\w{3}) (\d{4})',
            r'Débute le \w{3}\., (\d{1,2}) (\w{3}) (\d{4})',
            r'Débute le \w{3}\., (\d{1,2}) (\w{3,}) (\d{4})',
            r'(?:\w{3,9}, )?(\w+) (\d{1,2})',  # Saturday, June 1
            r'(\w{3}), (\w{3}) (\d{1,2}), (\d{4})',  # 'Thu, May 23, 2024'
            r'(\w{3}), (\w{3}) (\d{1,2}), (\d{4}) \d{1,2}:\d{2} [AP]M',  # 'Thu, May 16, 2024 8:00 PM'
            r'(\w{3})\s*(\d{1,2}), (\d{4})',  # 'May 15, 2024'
            r'(\w{3})[.,]\s*(\d{1,2})\s*(\w{3})\s*(\d{4})\s*(\d{2}:\d{2})',  # 'mer. 29 mai 2024 08:00'
            r'(\w{3})[.,]\s*(\d{1,2})\s*(\w{3})\s*(\d{4})'  # General pattern for day abbreviation, date, month, year
        ]

        for pattern in patterns:
            date_match = re.search(pattern, date_str)
            if date_match:
                try:
                    # Extração dos grupos encontrados dependendo do padrão
                    if len(date_match.groups()) == 2:
                        month, day = date_match.groups()
                        year = datetime.now().year  # Assumir ano atual se não fornecido
                    elif len(date_match.groups()) == 3:
                        if pattern == r'(\w+), (\w+) (\d{1,2})':
                            _, month, day = date_match.groups()
                            year = datetime.now().year  # Assumir ano atual se não fornecido
                        else:
                            day_of_week, month, day, year = date_match.groups()
                    else:
                        month_map = {
                            'jan': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'apr': 'Apr', 'may': 'May', 'jun': 'Jun', 'jul': 'Jul', 'aug': 'Aug', 'sep': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'dec': 'Dec',
                            'janv': 'Jan', 'févr': 'Feb', 'mars': 'Mar', 'avr': 'Apr', 'mai': 'May', 'juin': 'Jun', 'juil': 'Jul', 'août': 'Aug', 'sept': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'déc': 'Dec',
                            'ene': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'mayo': 'May', 'jun': 'Jun', 'jul': 'Jul', 'ago': 'Aug', 'sep': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'dic': 'Dec'
                        }
                        day_of_week, day, month, year = date_match.groups()
                        month = month_map[month[:3].lower()]

                    # Formatar para datetime
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
            'City': 'Montreal',  # Como Montreal é a cidade padrão
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

        # If unable to fetch data from Google Geocoding API, return default values
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

    # If "-" is not present in the string, it means it is just a start time
    if "-" not in date_str:
        start_time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)', date_str)
        if start_time_match:
            start_time = start_time_match.group(1)
            return start_time.strip(), None
        else:
            return None, None

    # For events that start and end on different days
    day_match = re.search(r'(\w+, \w+ \d{1,2}, \d{4} \d{1,2}:\d{2} (?:AM|PM))\s*-\s*(\w+, \w+ \d{1,2}, \d{4} \d{1,2}:\d{2} (?:AM|PM))', date_str)
    if day_match:
        start_time = day_match.group(1)
        end_time = day_match.group(2)
        return start_time.strip(), end_time.strip()

    # Converta os dias da semana para inglês
    date_str = re.sub(r'\b(?:lun(?:di)?|mon(?:day)?)\b', 'Monday', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\b(?:mar(?:di)?|tue(?:sday)?)\b', 'Tuesday', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\b(?:mer(?:credi)?|wed(?:nesday)?)\b', 'Wednesday', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\b(?:jeu(?:di)?|thu(?:rsday)?)\b', 'Thursday', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\b(?:ven(?:dredi)?|fri(?:day)?)\b', 'Friday', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\b(?:sam(?:edi)?|sat(?:urday)?)\b', 'Saturday', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\b(?:dim(?:anche)?|sun(?:day)?)\b', 'Sunday', date_str, flags=re.IGNORECASE)

    # Pattern for start and end time in the same day
    same_day_match = re.search(r'(\w+, \w+ \d{1,2}, \d{4} \d{1,2}:\d{2} (?:AM|PM))\s*-\s*(\d{1,2}:\d{2} (?:AM|PM))', date_str)
    if same_day_match:
        start_time = same_day_match.group(1)
        end_time = same_day_match.group(2)
        return start_time.strip(), end_time.strip()

    # AM/PM Format
    am_pm_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM))\s*-\s*(\d{1,2}:\d{2}\s*(?:AM|PM))', date_str)
    if am_pm_match:
        start_time, end_time = am_pm_match.groups()
        return start_time.strip(), end_time.strip()

    # 24hrs Format
    hrs_24_match = re.search(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', date_str)
    if hrs_24_match:
        start_time, end_time = hrs_24_match.groups()
        return start_time.strip(), end_time.strip()

    # Handle times like "9pm" and "11pm"
    pm_match = re.search(r'(\d{1,2})pm', date_str, flags=re.IGNORECASE)
    if pm_match:
        start_hour = int(pm_match.group(1))
        if start_hour < 12:
            start_hour += 12
        start_time = f"{start_hour:02}:00"

        # Assume the event ends after the start time
        end_hour = start_hour + 2  # Adding 2 hours as a default duration
        if end_hour >= 24:
            end_hour -= 12
        end_time = f"{end_hour:02}:00"

        return start_time.strip(), end_time

    # Handle times like "9am" and "11am"
    am_match = re.search(r'(\d{1,2})am', date_str, flags=re.IGNORECASE)
    if am_match:
        start_hour = int(am_match.group(1))
        if start_hour == 12:
            start_hour = 0
        start_time = f"{start_hour:02}:00"

        # Assume the event ends after the start time
        end_hour = start_hour + 2  # Adding 2 hours as a default duration
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
            # Construa uma string de consulta específica para Montreal ou Quebec
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


def get_previous_page_image_url(driver):
    url = 'https://www.eventbrite.com/d/canada--montreal/all-events/?page=1'

    driver.get(url)

    if driver.page_source:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        img_tag = soup.find('img', class_='event-card-image')

        if img_tag:
            return img_tag['src']

    return None

def scrape_eventbrite_events(driver, url, selectors, max_pages=3):
    global event_id_counter

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

                event_link = event.find('a', href=True)['href']
                driver.get(event_link)

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
                        price_default = "undisclosed price"  # Modificação aqui

                    price_element = event_page.find('span', class_='eds-text-bm eds-text-weight--heavy')
                    price = price_element.text.strip() if price_element else price_default
                    price_element = event_page.find('span', class_='eds-text-bm eds-text-weight--heavy')
                    price = price_element.text.strip() if price_element else price_default

                    date_element = event_page.find('span', class_='date-info__full-datetime')
                    date = date_element.text.strip() if date_element else None

                    location_element = event_page.find('p', class_='location-info__address-text')
                    location = location_element.text.strip() if location_element else None

                    ImageURL = get_previous_page_image_url(driver)

                    # Isolando o número do preço usando expressões regulares
                    price_number = None
                    if price:
                        price_matches = re.findall(r'\d+\.?\d*', price)
                        if price_matches:
                            price_number = float(price_matches[0])


                    latitude, longitude = get_coordinates(location)

                    organizer = event_page.find('div', class_='descriptive-organizer-info-mobile__name') if event_page.find('div', class_='descriptive-organizer-info-mobile__name') else None
                    image_url_organizer = event_page.find('svg', class_='eds-avatar__background eds-avatar__background--has-border')
                    if image_url_organizer:
                        image_tag = image_url_organizer.find('image')
                        if image_tag:
                            event_info['Image URL Organizer'] = image_tag.get('xlink:href')
                        else:
                            event_info['Image URL Organizer'] = None
                    else:
                        event_info['Image URL Organizer'] = None

                    event_info['Title'] = title
                    event_info['Description'] = description
                    event_info['Price'] = price_number
                    event_info['Date'] = format_date(date, 'Eventbrite')
                    event_info['StartTime'], event_info['EndTime'] = extract_start_end_time(date)
                    event_info.update(format_location(location, 'Eventbrite'))  # Atualiza com os detalhes de localização
                    event_info['ImageURL'] = ImageURL
                    event_info['Latitude'] = latitude
                    event_info['Longitude'] = longitude
                    event_info['Organizer'] = organizer.text.strip() if organizer else None
                    event_info['EventUrl'] = event_link
                    # event_info['Tags'] = tags


                    if latitude is not None and longitude is not None:
                        map_url = open_google_maps(latitude, longitude)
                        event_info['GoogleMaps_URL'] = map_url

                    all_events.append(event_info)

                except Exception as e:
                    print("Error scraping event page:", e)

                finally:
                    driver.back()

            try:
                next_button = driver.find_element_by_link_text('Next')
                next_button.click()
            except Exception as e:
                print("Error clicking next button:", e)
                break

        except Exception as e:
            print("Error scraping events page:", e)
            break

    return all_events


def main():
    sources = [
        {
            'name': 'Eventbrite',
            'url': 'https://www.eventbrite.com/d/canada--montreal/all-events/',
            'selectors': {
                'event': {'tag': 'div', 'class': 'discover-search-desktop-card discover-search-desktop-card--hiddeable'},
                'Title': {'tag': 'h2', 'class': 'event-card__title'},
                'Description': {'tag': 'p', 'class': 'event-card__description'},
                'Date': {'tag': 'p', 'class': 'event-card__date'},
                'Location': {'tag': 'p', 'class': 'location-info__address-text'},
                'Price': {'tag': 'p', 'class': 'event-card__price'},
                'ImageURL': {'tag': 'img', 'class': 'event-card__image'},
                # 'Tags': {'tag': 'ul', 'class': 'event-card__tags'},
                'Organizer': {'tag': 'a', 'class': 'event-card__organizer'}
            },
            'max_pages': 30
        }
    ]

    chrome_options = Options()
    # Remova a opção "--headless" para mostrar o navegador
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    all_events = []
    for source in sources:
        print(f"Scraping events from: {source['name']}")
        if source['name'] == 'Eventbrite':
            events = scrape_eventbrite_events(driver, source['url'], source['selectors'])
            # Filtrar eventos com a maioria das tags em null
            events_with_data = [event for event in events if sum(1 for value in event.values() if value is not None) > 10]  # Defina o número mínimo de tags não nulas aqui
            all_events.extend(events_with_data)
        else:
            print(f"Unsupported source: {source['name']}")
            continue

    # JSON File
    with open('eventbrite.json', 'w') as f:
        json.dump(all_events, f, indent=4)

    driver.quit()

if __name__ == "__main__":
    main()
