import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
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

def scrape_facebook_events(driver, url, selectors, max_scroll=50):
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
        try:
            driver.get(event_url)
        except TimeoutException:
            print(f"Timeout ao carregar o evento: {event_url}")
            continue
        except WebDriverException as e:
            print(f"Erro do WebDriver ao carregar o evento: {event_url} - {e}")
            continue

        time.sleep(2)  # Allow event page to load
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

        all_events.append(event_info)
        unique_event_titles.add(event_title)

        driver.back()

    return all_events if all_events else None

def scrape_eventbrite_events(driver, url, selectors, max_pages=45):
    driver.get(url)
    driver.implicitly_wait(20)

    all_events = []

    for page in range(max_pages):
        try:
            print(f"Scraping page {page + 1}")
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
                    if not event_link.startswith('https'):
                        event_link = 'https://www.eventbrite.com' + event_link

                    print(f"Accessing event link: {event_link}")
                    driver.get(event_link)
                    time.sleep(2)

                    try:
                        event_page_content = driver.page_source
                        event_page = BeautifulSoup(event_page_content, 'html.parser')

                        title_element = event_page.find('h1', class_='event-title css-0')
                        title = title_element.text.strip() if title_element else None
                        print(f"Title: {title}")

                        description_element = event_page.find('p', class_='summary')
                        description = description_element.text.strip() if description_element else None
                        print(f"Description: {description}")

                        price_default_element = event_page.find('div', class_='conversion-bar__panel-info')
                        if price_default_element:
                            price_default = price_default_element.text.strip()
                        else:
                            price_default = "undisclosed price"

                        price_element = event_page.find('span', class_='eds-text-bm eds-text-weight--heavy')
                        price = price_element.text.strip() if price_element else price_default
                        print(f"Price: {price}")

                        date_element = event_page.find('span', class_='date-info__full-datetime')
                        date = date_element.text.strip() if date_element else None
                        print(f"Date: {date}")

                        location_element = event_page.find('p', class_='location-info__address-text')
                        location = location_element.text.strip() if location_element else None
                        print(f"Location: {location}")

                        ImageURL = event.find('img', class_='event-card-image')['src']
                        print(f"ImageURL: {ImageURL}")

                        price_number = None
                        if price:
                            price_matches = re.findall(r'\d+\.?\d*', price)
                            if price_matches:
                                price_number = float(price_matches[0])

                        latitude, longitude = get_coordinates(location)
                        print(f"Coordinates: {latitude}, {longitude}")

                        organizer_element = event_page.find('div', class_='descriptive-organizer-info-mobile__name')
                        organizer = organizer_element.text.strip() if organizer_element else None
                        print(f"Organizer: {organizer}")

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
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-spec='page-next']"))
                )
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
        },
        {
            'name': 'Facebook',
            'url': 'https://www.facebook.com/events/explore/montreal-quebec/102184499823699/',
            'selectors': {
                'event': {'tag': 'div', 'class': 'x1qjc9v5 x9f619 x78zum5 xdt5ytf x5yr21d x6ikm8r x10wlt62 xexx8yu x10ogl3i xg8j3zb x1k2j06m xlyipyv xh8yej3'}
            },
            'max_scroll': 50
        }
    ]

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--start-maximized")  # Abrir navegador em tela cheia

    driver = webdriver.Chrome(options=chrome_options)

    all_events = []
    for source in sources:
        print(f"Scraping events from: {source['name']}")
        if source['name'] == 'Eventbrite':
            events = scrape_eventbrite_events(driver, source['url'], source['selectors'], source['max_pages'])
            events_with_data = [event for event in events if sum(1 for value in event.values() if value is not None) > 10]
            all_events.extend(events_with_data)
        elif source['name'] == 'Facebook':
            events = scrape_facebook_events(driver, source['url'], source['selectors'], source['max_scroll'])
            events_with_data = [event for event in events if sum(1 for value in event.values() if value is not None) > 4]
            all_events.extend(events_with_data)
        else:
            print(f"Unsupported source: {source['name']}")
            continue

    # Filter out events with "Date: Null"
    filtered_events = [event for event in all_events if event['Date'] is not None]

    with open('events.json', 'w') as f:
        json.dump(filtered_events, f, indent=4)

    driver.quit()

if __name__ == "__main__":
    main()
