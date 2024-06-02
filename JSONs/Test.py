import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import time
from geopy.geocoders import Nominatim
import re
from datetime import datetime, timedelta
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import openai

client = openai.OpenAI(api_key='sk-proj-yqr04pojS7nwwUqkp20TT3BlbkFJUcdzCafxVZa09BZm5ccV')

def generate_tags(title, description):
    predefined_tags = [
        {"id": "005a4420-88c3-11ee-ab49-69be32c19a11", "name": "Startup", "emoji": "🚀", "tagCategory": "Education"},
        {"id": "00fb7c50-3c47-11ee-bb59-7f5156da6f07", "name": "Reggae", "emoji": " 💚", "tagCategory": "Musique"},
        {"id": "00fe8220-3d0e-11ee-a0b5-a3a6fbdfc7e4", "name": "Squash", "emoji": "🏸", "tagCategory": "Sports"},
        {"id": "0159ac60-3d0c-11ee-a0b5-a3a6fbdfc7e4", "name": "Aquatics", "emoji": "🏊‍♂️", "tagCategory": "Sports"},
        {"id": "01785870-4ce5-11ee-931a-073fc9abbdfa", "name": "Karaoke", "emoji": "🎤", "tagCategory": "Leisure"},
        {"id": "06759f60-5c8d-11ee-8ae0-fb963ffbedc0", "name": "Holiday", "emoji": "🌞", "tagCategory": "Musique"},
        {"id": "0693e050-5c8e-11ee-8ae0-fb963ffbedc0", "name": "Roller Derby", "emoji": "🛼", "tagCategory": "Sports"},
        {"id": "099b2b90-4ce5-11ee-931a-073fc9abbdfa", "name": "Singing", "emoji": "🎤", "tagCategory": "Leisure"},
        {"id": "09dddaa0-573d-11ee-8b78-9b77053f08ef", "name": "Chess", "emoji": "♟", "tagCategory": "Leisure"},
        {"id": "0a3f4540-3c46-11ee-bb59-7f5156da6f07", "name": "Blues", "emoji": " 🎵", "tagCategory": "Musique"},
        {"id": "0ad207f0-3d0d-11ee-a0b5-a3a6fbdfc7e4", "name": "Golf", "emoji": "⛳", "tagCategory": "Sports"},
        {"id": "0b379d00-3d0c-11ee-a0b5-a3a6fbdfc7e4", "name": "Athletic Races", "emoji": "🏅", "tagCategory": "Sports"},
        {"id": "0cafac20-3d0e-11ee-a0b5-a3a6fbdfc7e4", "name": "Surfing", "emoji": "🏄‍♀️", "tagCategory": "Sports"},
        {"id": "0dc9b310-45df-11ee-837b-e184466a9b82", "name": "Book", "emoji": "📖", "tagCategory": "Leisure"},
        {"id": "108f37a0-3d0b-11ee-a0b5-a3a6fbdfc7e4", "name": "Fashion", "emoji": "🥻", "tagCategory": "Leisure"},
        {"id": "11164b60-4381-11ee-b8b1-a1b868b635cd", "name": "Punk", "emoji": "👩‍🎤", "tagCategory": "Musique"},
        {"id": "133a3370-3c47-11ee-bb59-7f5156da6f07", "name": "Religious", "emoji": "✝", "tagCategory": "Musique"},
        {"id": "1453a7c0-3d0d-11ee-a0b5-a3a6fbdfc7e4", "name": "Gymnastics", "emoji": "🤸‍♀️", "tagCategory": "Sports"},
        {"id": "15de0a70-45e3-11ee-837b-e184466a9b82", "name": "Hiking", "emoji": "🏃‍♂️", "tagCategory": "Sports"},
        {"id": "1859e020-6ec5-11ee-839e-4b70ecb92583", "name": "Cycling", "emoji": "🚴‍♂️", "tagCategory": "Sports"},
        {"id": "18f44470-6ec6-11ee-839e-4b70ecb92583", "name": "Fencing", "emoji": "🤺", "tagCategory": "Sports"},
        {"id": "19783bb0-45e3-11ee-837b-e184466a9b82", "name": "Yoga", "emoji": "🧘‍♂️", "tagCategory": "Sports"},
        {"id": "1b7e1210-3d0b-11ee-a0b5-a3a6fbdfc7e4", "name": "Photography", "emoji": "📸", "tagCategory": "Leisure"},
        {"id": "1cbfc5a0-3c46-11ee-bb59-7f5156da6f07", "name": "Jazz", "emoji": " 🎵", "tagCategory": "Musique"},
        {"id": "1d344290-3c46-11ee-bb59-7f5156da6f07", "name": "Pop", "emoji": "🎶", "tagCategory": "Musique"},
        {"id": "1d809850-3c47-11ee-bb59-7f5156da6f07", "name": "R&B", "emoji": " 🎶", "tagCategory": "Musique"},
        {"id": "1de59e30-3c47-11ee-bb59-7f5156da6f07", "name": "Rock", "emoji": "🎸", "tagCategory": "Musique"},
        {"id": "1e2c0d80-3c47-11ee-bb59-7f5156da6f07", "name": "Soul", "emoji": "🎶", "tagCategory": "Musique"},
        {"id": "1ec41b90-3c46-11ee-bb59-7f5156da6f07", "name": "Classical", "emoji": " 🎶", "tagCategory": "Musique"},
        {"id": "1f39ec90-3d0c-11ee-a0b5-a3a6fbdfc7e4", "name": "Baseball", "emoji": "⚾", "tagCategory": "Sports"},
        {"id": "201cbff0-3c47-11ee-bb59-7f5156da6f07", "name": "Country", "emoji": "🤠", "tagCategory": "Musique"},
        {"id": "21882c20-3c46-11ee-bb59-7f5156da6f07", "name": "Folk", "emoji": "🎻", "tagCategory": "Musique"},
        {"id": "2211e6d0-3c46-11ee-bb59-7f5156da6f07", "name": "Hip-Hop", "emoji": "🎤", "tagCategory": "Musique"},
        {"id": "226300e0-3d0b-11ee-a0b5-a3a6fbdfc7e4", "name": "Dance", "emoji": "💃", "tagCategory": "Leisure"},
        {"id": "2307f3e0-3c47-11ee-bb59-7f5156da6f07", "name": "Indie", "emoji": " 🎶", "tagCategory": "Musique"},
        {"id": "2401c100-3c46-11ee-bb59-7f5156da6f07", "name": "Metal", "emoji": "🤘", "tagCategory": "Musique"},
        {"id": "244cfde0-3c47-11ee-bb59-7f5156da6f07", "name": "Punk Rock", "emoji": "👩‍🎤", "tagCategory": "Musique"},
        {"id": "24883e40-3c46-11ee-bb59-7f5156da6f07", "name": "Reggaeton", "emoji": "🎵", "tagCategory": "Musique"},
        {"id": "24d07ab0-3d0d-11ee-a0b5-a3a6fbdfc7e4", "name": "Tennis", "emoji": "🎾", "tagCategory": "Sports"},
        {"id": "253b9e90-3d0d-11ee-a0b5-a3a6fbdfc7e4", "name": "Basketball", "emoji": "🏀", "tagCategory": "Sports"},
        {"id": "2602b960-3c47-11ee-bb59-7f5156da6f07", "name": "Gospel", "emoji": "🎶", "tagCategory": "Musique"},
        {"id": "263997d0-3c46-11ee-bb59-7f5156da6f07", "name": "Jazz", "emoji": " 🎶", "tagCategory": "Musique"},
        {"id": "274d8200-3c46-11ee-bb59-7f5156da6f07", "name": "Rap", "emoji": "🎤", "tagCategory": "Musique"},
        {"id": "27a4a0f0-3c47-11ee-bb59-7f5156da6f07", "name": "Rock and Roll", "emoji": "🎸", "tagCategory": "Musique"},
        {"id": "27fb1d20-3c47-11ee-bb59-7f5156da6f07", "name": "Ska", "emoji": "🎺", "tagCategory": "Musique"},
        {"id": "28ab7800-3c46-11ee-bb59-7f5156da6f07", "name": "Soul", "emoji": "🎶", "tagCategory": "Musique"},
        {"id": "290a1bb0-3c47-11ee-bb59-7f5156da6f07", "name": "Techno", "emoji": "🎧", "tagCategory": "Musique"},
        {"id": "2995c8b0-3c46-11ee-bb59-7f5156da6f07", "name": "World Music", "emoji": "🌍", "tagCategory": "Musique"}
    ]

    prompt = (
        f"You are a meticulous selector, trained on identifying relevant tags for events.\n" +
        f"Your task is to select, only from the list below, at most 5 tags that are very relevant for the event \"{title}\" (description: \"{description}\").\n" +
        f"Here are the exhaustive list of tags to select from:\n" +
        ''.join([f"{index+1}. {tag['name']} ({tag['tagCategory']})\n" for index, tag in enumerate(predefined_tags)]) +
        f"Only output the selected tags from this list, separated by comma.\n" +
        f"Do not output any other tag.\n" +
        f"If there is no relevant tag in the list, output 'NO TAG'."
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4-turbo",
            temperature=0,
            messages=[
                {"role": "system", "content": prompt}
            ]
        )
    except openai.error.OpenAIError as e:
        print(f"Erro na API OpenAI: {e}")
        return []

    response = completion.choices[0].message.content.strip()

    relevant_tags = []

    for predefined_tag in predefined_tags:
        if predefined_tag["name"] in response:
            relevant_tags.append(predefined_tag)

    return relevant_tags

def scroll_to_bottom(driver, max_scroll=1):
    for _ in range(max_scroll):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

def format_date(date_str):
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
                end_month = start_month

            start_date = datetime.strptime(f"{start_day} {start_month} {year} {start_time}", f"%d %B %Y %I:%M %p")
            end_date = datetime.strptime(f"{end_day} {end_month} {year} {end_time}", f"%d %B %Y %I:%M %p")

            if end_date <= start_date:
                end_date += timedelta(days=1)

            formatted_start_date = start_date.strftime("%d/%m/%Y at %I:%M %p")
            formatted_end_date = end_date.strftime("%d/%m/%Y at %I:%M %p")
            return (formatted_start_date, formatted_end_date)

    return None

def get_coordinates(location_text):
    if location_text is None:
        print("Localização não encontrada para o evento.")
        return None, None

    geolocator = Nominatim(user_agent="event_scraper")

    try:
        location_obj = geolocator.geocode(location_text + ", Montreal, Quebec", exactly_one=True)
        if location_obj:
            return location_obj.latitude, location_obj.longitude
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Erro ao obter coordenadas para {location_text}: {e}")

    try:
        street_address = location_text.split(',')[0]
        street_location = geolocator.geocode(street_address + ", Montreal, Quebec", exactly_one=True)
        if street_location:
            return street_location.latitude, street_location.longitude
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Erro ao obter coordenadas para {street_address}: {e}")

    return None, None

def open_google_maps(latitude, longitude):
    return f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"

def get_location_details(latitude, longitude):
    geolocator = Nominatim(user_agent="event_scraper")
    try:
        location = geolocator.reverse((latitude, longitude), exactly_one=True)
        if location:
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
    driver.implicitly_wait(20)
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

        time.sleep(2)
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
            driver.back()
            continue

        event_info = {
            'Title': event_title,
            'Description': description,
            'Date': format_date(date_text),
            'StartTime': start_time,
            'EndTime': end_time,
            **location_details,
            'EventUrl': event_url,
            'ImageURL': event_page.find('img', class_='xz74otr x1ey2m1c x9f619 xds687c x5yr21d x10l6tqk x17qophe x13vifvy xh8yej3')['src'] if event_page.find('img', class_='xz74otr x1ey2m1c x9f619 xds687c x5yr21d x10l6tqk x17qophe x13vifvy xh8yej3') else None,
            'Organizer': event_page.find('span', class_='xt0psk2').text.strip() if event_page.find('span', class_='xt0psk2') else None,
            'Organizer_IMG': event_page.find('img', class_='xz74otr')['src'] if event_page.find('img', class_='xz74otr') else None
        }

        event_tags = generate_tags(event_title, description)
        event_info['Tags'] = event_tags

        all_events.append(event_info)
        unique_event_titles.add(event_title)

        driver.back()

    return all_events if all_events else None

def scrape_eventbrite_events(driver, url, selectors, max_pages=35):
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
                        event_info['Date'] = format_date(date)
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

                        event_info['Tags'] = generate_tags(title, description)

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
            'name': 'Facebook',
            'url': 'https://www.facebook.com/events/explore/montreal-quebec/102184499823699/',
            'selectors': {
                'event': {'tag': 'div', 'class': 'x1qjc9v5 x9f619 x78zum5 xdt5ytf x5yr21d x6ikm8r x10wlt62 xexx8yu x10ogl3i xg8j3zb x1k2j06m xlyipyv xh8yej3'}
            }
        },
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

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-browser-side-navigation")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-features=NetworkService")
    options.add_argument("--disable-popup-blocking")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)

    all_events = []
    for source in sources:
        print(f"Scraping events from: {source['name']}")
        if source['name'] == 'Facebook':
            events = scrape_facebook_events(driver, source['url'], source['selectors'])
        elif source['name'] == 'Eventbrite':
            events = scrape_eventbrite_events(driver, source['url'], source['selectors'], source['max_pages'])

        if events is not None:
            all_events.extend(events)
        else:
            print(f"No events found for {source['name']}.")

    all_events = [event for event in all_events if all(event.get(key) is not None for key in ['Title', 'Date', 'Location'])]

    with open('events.json', 'w') as f:
        json.dump(all_events, f, indent=4)

    driver.quit()

if __name__ == "__main__":
    main()
