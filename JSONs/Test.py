import json
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from fuzzywuzzy import fuzz
import geopy
from geopy.geocoders import Nominatim
from unidecode import unidecode
import re
import openai

# OpenAI API Key
client = openai.OpenAI(api_key='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')

def generate_tags(title, description):
    predefined_tags = [
        {"id": "005a4420-88c3-11ee-ab49-69be32c19a11", "name": "Startup", "emoji": "🚀", "tagCategory": "Education"},
        # Add other predefined tags here...
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
    print(prompt)

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
    print('response:', response)

    relevant_tags = []

    for predefined_tag in predefined_tags:
        if predefined_tag["name"] in response:
            relevant_tags.append(predefined_tag)

    print("Relevant tags:", relevant_tags)
    return relevant_tags

def calculate_similarity(str1, str2):
    return fuzz.token_sort_ratio(str1, str2)

def scroll_to_bottom(driver, max_scroll=3):
    for _ in range(max_scroll):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

def format_date(date_str):
    print("Original date string:", date_str)

    if not date_str:
        print("Erro: String de data vazia.")
        return None

    match = re.match(r"(\w+), (\w+ \d{1,2}, \d{4}) AT (\d{1,2}:\d{2}\s*(?:AM|PM)) – (\d{1,2}:\d{2}\s*(?:AM|PM))", date_str)
    if match:
        day_of_week, date, start_time, end_time = match.groups()

        start_month = date.split()[0]
        start_month_num = datetime.strptime(start_month, '%B').month

        start_day, year = re.search(r"(\d{1,2}), (\d{4})", date).groups()

        formatted_start_date = f"{start_day}/{start_month_num:02d}/{year}"
        print("Formatted start date:", formatted_start_date)

        return formatted_start_date
    else:
        print("Erro: Formato de data inválido.")
        return None

def get_coordinates(location):
    if location is None:
        return None, None

    location = unidecode(location)
    geolocator = Nominatim(user_agent="event_scraper")
    retries = 3
    delay = 2

    for _ in range(retries):
        try:
            location = geolocator.geocode(location, addressdetails=True)
            if location:
                return location.latitude, location.longitude
        except geopy.exc.GeocoderUnavailable as e:
            time.sleep(delay)

    return None, None

def open_google_maps(latitude, longitude):
    return f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"

def get_location_details(latitude, longitude):
    geolocator = Nominatim(user_agent="event_scraper")
    retries = 3
    delay = 2

    for _ in range(retries):
        try:
            location = geolocator.reverse((latitude, longitude), language='en', addressdetails=True)
            if location:
                address = location.raw['address']
                city = address.get('city', None)
                country_code = address.get('country_code', None)
                return address, city, country_code
        except geopy.exc.GeocoderUnavailable as e:
            time.sleep(delay)

    return None, None, None

#### FACEBOOK ####
def scrape_facebook_events(driver, url, selectors, max_scroll=3):
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
            title = event_title_elem.text.strip()
            if any(calculate_similarity(title, existing_title) >= 90 for existing_title in unique_event_titles):
                driver.back()
                continue
            unique_event_titles.add(title)
        else:
            driver.back()
            continue

        description = event_page.find('div', class_='xdj266r x11i5rnm xat24cr x1mh8g0r x1vvkbs').text.strip() if event_page.find('div', class_='xdj266r x11i5rnm xat24cr x1mh8g0r x1vvkbs') else None

        location_div = event_page.find('div', class_='x1i10hfl xjbqb8w x1ejq31n xd10rxx x1sy0etr x17r0tee x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz xt0b8zv xzsf02u x1s688f')
        location_span = event_page.find('span', class_='xt0psk2')
        location_text = location_div.text.strip() if location_div else (location_span.text.strip() if location_span else None)

        if location_text:
            latitude, longitude = get_coordinates(location_text)
        else:
            latitude, longitude = None, None

        google_maps_url = open_google_maps(latitude, longitude)

        address_span = event_page.find('span', class_='x193iq5w xeuugli x13faqbe x1vvkbs xlh3980 xvmahel x1n0sxbx x1lliihq x1s928wv xhkezso x1gmr53x x1cpjm7i x1fgarty x1943h6x x4zkp8e x3x7a5m x1f6kntn xvq8zen xo1l8bm xi81zsa x1yc453h')
        address = address_span.text.strip() if address_span else None

        tags = generate_tags(title, description)

        location_details = {
            'Location': {
                'Location': location_text,
                'Address': address,
                'Latitude': latitude,
                'Longitude': longitude,
                'GoogleMaps_URL': google_maps_url,
                'City': None,
                'CountryCode': None
            }
        }

        address, city, country_code = get_location_details(latitude, longitude)

        location_details['Location']['Address'] = address
        location_details['Location']['City'] = city
        location_details['Location']['CountryCode'] = country_code

        if city is None and country_code is None:
            location_details['Location']['City'] = 'Montreal'
            location_details['Location']['CountryCode'] = 'ca'

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

        event_info = {
            'Title': title,
            'Description': description,
            'Date': format_date(date_text),
            **location_details,
            'ImageURL': event_page.find('img', class_='xz74otr x1ey2m1c x9f619 xds687c x5yr21d x10l6tqk x17qophe x13vifvy xh8yej3')['src'] if event_page.find('img', class_='xz74otr x1ey2m1c x9f619 xds687c x5yr21d x10l6tqk x17qophe x13vifvy xh8yej3') else None,
            'Organizer': event_page.find('span', class_='xt0psk2').text.strip() if event_page.find('span', class_='xt0psk2') else None,
            'Organizer_IMG': event_page.find('img', class_='xz74otr')['src'] if event_page.find('img', class_='xz74otr') else None,
            'EventUrl': event_url,
            'StartTime': start_time,
            'EndTime': end_time,
            'Tags': tags,
        }

        all_events.append(event_info)

        driver.back()

    return all_events if all_events else None

#### EVENTBRITE ####
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

def scrape_eventbrite_events(driver, url, selectors, max_pages=3):
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

                    title = event_page.find('h1', class_='event-title css-0').text.strip() if event_page.find('h1', class_='event-title css-0') else None
                    description = event_page.find('p', class_='summary').text.strip() if event_page.find('p', class_='summary') else None
                    price = event_page.find('div', class_='conversion-bar__panel-info').text.strip() if event_page.find('div', class_='conversion-bar__panel-info') else None
                    date = event_page.find('span', class_='date-info__full-datetime').text.strip() if event_page.find('span', class_='date-info__full-datetime') else None
                    location_element = event_page.find('p', class_='location-info__address-text')
                    location = location_element.text.strip() if location_element else None
                    tags = generate_tags(title, description)

                    price_number = None
                    if price:
                        price_matches = re.findall(r'\d+\.?\d*', price)
                        if price_matches:
                            price_number = float(price_matches[0])

                    latitude, longitude = get_coordinates(location)

                    organizer = event_page.find('a', class_='descriptive-organizer-info__name-link') if event_page.find('a', class_='descriptive-organizer-info__name-link') else None
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
                    event_info['Date'] = date
                    event_info['StartTime'], event_info['EndTime'] = extract_start_end_time(date)
                    event_info['Location'] = location
                    event_info['ImageURL'] = event_info.get('ImageURL')
                    event_info['Latitude'] = latitude
                    event_info['Longitude'] = longitude
                    event_info['Organizer'] = organizer.text.strip() if organizer else None
                    event_info['EventUrl'] = event_link
                    event_info['Tags'] = tags

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
                'event': {'tag': 'div', 'class': 'discover-search-desktop-card discover-search-desktop-card--hiddeable'},
                'Title': {'tag': 'h2', 'class': 'event-card__title'},
                'Description': {'tag': 'p', 'class': 'event-card__description'},
                'Date': {'tag': 'p', 'class': 'event-card__date'},
                'Location': {'tag': 'p', 'class': 'location-info__address-text'},
                'Price': {'tag': 'p', 'class': 'event-card__price'},
                'ImageURL': {'tag': 'img', 'class': 'event-card__image'},
                'Organizer': {'tag': 'a', 'class': 'event-card__organizer'},
                'Organizer_IMG': {'tag': 'svg', 'class': 'eds-avatar__background eds-avatar__background--has-border'}
            }
        }
    ]

    chrome_options = Options()

    driver = webdriver.Chrome(options=chrome_options)

    all_events = []
    unique_event_titles = set()
    duplicate_events = []

    for source in sources:
        if source['name'] == 'Facebook':
            events = scrape_facebook_events(driver, source['url'], source['selectors'])
        elif source['name'] == 'Eventbrite':
            events = scrape_eventbrite_events(driver, source['url'], source['selectors'])
        else:
            print(f"Fonte não suportada: {source['name']}")
            continue

        if events:
            for event in events:
                event_title = event.get('Title')
                if event_title not in unique_event_titles:
                    unique_event_titles.add(event_title)
                    all_events.append(event)
                else:
                    duplicate_events.append(event)

    # JSON File for unique events
    with open('unique_events.json', 'w') as f:
        json.dump(all_events, f, indent=4)

    # JSON File for duplicate events
    with open('duplicate_events.json', 'w') as f:
        json.dump(duplicate_events, f, indent=4)

    driver.quit()

if __name__ == "__main__":
    main()
