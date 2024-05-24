import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_eventbrite_events(url, max_pages=5):
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    driver.implicitly_wait(10)

    all_events = []

    for page in range(max_pages):
        try:
            # Encontrar todos os links de eventos na página atual
            event_links = driver.find_elements(By.CSS_SELECTOR, "a.event-card-link")

            for event_link in event_links:
                event_url = event_link.get_attribute('href')
                driver.get(event_url)

                try:
                    # Esperar até que o título do evento esteja presente
                    title_element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "h1.expired-heading"))
                    )
                    title = title_element.text.strip()
                    all_events.append({"Title": title, "URL": event_url})
                    print(f"Scraped event: {title}")

                except Exception as e:
                    print(f"Erro ao raspar o evento: {e}")

                # Voltar para a página de índice
                driver.back()
                time.sleep(2)  # Esperar um pouco para garantir que a página seja carregada

            # Clicar no botão "Próxima Página"
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "button[data-spec='page-next']")
                next_button.click()
                time.sleep(3)  # Esperar um pouco para garantir que a próxima página seja carregada
            except Exception as e:
                print("Erro ao clicar no botão de próxima página ou não há mais páginas.")
                break

        except Exception as e:
            print(f"Erro ao processar a página: {e}")
            break

    driver.quit()

    # Salvar os resultados em um arquivo JSON
    with open('eventbrite_events.json', 'w') as f:
        json.dump(all_events, f, indent=4)

if __name__ == "__main__":
    scrape_eventbrite_events("https://www.eventbrite.com/d/canada--montreal/all-events/")
