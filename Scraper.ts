import puppeteer from 'puppeteer';
import fs from 'fs';
import { v5 as uuidv5 } from 'uuid';
import moment from 'moment';

const NAMESPACE = '12345678-1234-5678-1234-567812345678'; // Replace with a fixed UUID namespace

function generateEventUUID(title: string, date: string, location: string): string {
    const name = `${title}_${date}_${location}`;
    return uuidv5(name, NAMESPACE);
}

async function scrollToBottom(page: puppeteer.Page, maxClicks: number = 15): Promise<void> {
    for (let i = 0; i < maxClicks; i++) {
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(1000);
    }
}

function formatDate(dateStr: string): [string, string] | null {
    console.log("Original date string:", dateStr);
    if (!dateStr) {
        console.log("Erro: String de data vazia.");
        return null;
    }

    const patterns = [
        { regex: /(\w+) (\d+) AT (\d{1,2}:\d{2}\s*(?:AM|PM)) – (\w+) (\d+) AT (\d{1,2}:\d{2}\s*(?:AM|PM)) (\d{4}) EDT/, monthFormat: 'MMM' },
        { regex: /(\w+), (\w+) (\d+), (\d{4}) AT (\d{1,2}:\d{2}\s*(?:AM|PM)) – (\d{1,2}:\d{2}\s*(?:AM|PM))/, monthFormat: 'MMMM' }
    ];

    for (const { regex, monthFormat } of patterns) {
        const match = regex.exec(dateStr);
        if (match) {
            let startMonth, startDay, startTime, endMonth, endDay, endTime, year;
            if (match.length === 8) {
                [, startMonth, startDay, startTime, endMonth, endDay, endTime, year] = match;
            } else if (match.length === 7) {
                [, , startMonth, startDay, year, startTime, endTime] = match;
                endDay = startDay;
                endMonth = startMonth;
            }

            const startDate = moment(`${startDay} ${startMonth} ${year} ${startTime}`, `DD ${monthFormat} YYYY hh:mm A`);
            const endDate = moment(`${endDay} ${endMonth} ${year} ${endTime}`, `DD ${monthFormat} YYYY hh:mm A`);

            if (endDate.isBefore(startDate)) {
                endDate.add(1, 'days');
            }

            const formattedStartDate = startDate.format("DD/MM/YYYY [at] hh:mm A");
            const formattedEndDate = endDate.format("DD/MM/YYYY [at] hh:mm A");
            console.log("Formatted start date:", formattedStartDate);
            console.log("Formatted end date:", formattedEndDate);
            return [formattedStartDate, formattedEndDate];
        }
    }

    console.log("Erro: Formato de data inválido.");
    return null;
}

async function scrapeEventbriteEvents(browser: puppeteer.Browser, url: string, maxPages: number = 3): Promise<any[]> {
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'networkidle2' });
    await page.setViewport({ width: 1280, height: 800 });

    const allEvents: any[] = [];

    for (let currentPage = 1; currentPage <= maxPages; currentPage++) {
        console.log(`Scraping page ${currentPage}`);
        await scrollToBottom(page);
        const events = await page.$$eval('.discover-search-desktop-card', cards => cards.map(card => {
            const titleElement = card.querySelector('.event-card__title');
            const descriptionElement = card.querySelector('.event-card__description');
            const dateElement = card.querySelector('.event-card__date');
            const locationElement = card.querySelector('.location-info__address-text');
            const priceElement = card.querySelector('.event-card__price');
            const imageElement = card.querySelector('.event-card__image');
            const eventLinkElement = card.querySelector('.event-card-link');

            return {
                title: titleElement?.textContent?.trim() || null,
                description: descriptionElement?.textContent?.trim() || null,
                date: dateElement?.textContent?.trim() || null,
                location: locationElement?.textContent?.trim() || null,
                price: priceElement?.textContent?.trim() || "Price not informed",
                imageURL: imageElement ? (imageElement as HTMLImageElement).src : null,
                eventLink: eventLinkElement ? (eventLinkElement as HTMLAnchorElement).href : null
            };
        }));

        for (const event of events) {
            if (event.eventLink) {
                await page.goto(event.eventLink, { waitUntil: 'networkidle2' });
                const title = await page.$eval('h1.event-title', el => el.textContent?.trim() || '');
                const description = await page.$eval('p.summary', el => el.textContent?.trim() || 'No Description');
                const date = await page.$eval('span.date-info__full-datetime', el => el.textContent?.trim() || '');
                const location = await page.$eval('p.location-info__address-text', el => el.textContent?.trim() || '');
                const imageURL = await page.$eval('img.event-card-image', el => (el as HTMLImageElement).src);
                const priceElement = await page.$('span.eds-text-bm');
                const price = priceElement ? await priceElement.evaluate(el => el.textContent?.trim() || 'Price not informed') : 'Price not informed';
                const organizerElement = await page.$('div.descriptive-organizer-info-mobile__name');
                const organizer = organizerElement ? await organizerElement.evaluate(el => el.textContent?.trim() || 'Unknown') : 'Unknown';

                const [formattedStartDate, formattedEndDate] = formatDate(date) || ['', ''];
                const eventUUID = generateEventUUID(title, formattedStartDate, location);

                const eventInfo = {
                    title,
                    description,
                    date: formattedStartDate,
                    location,
                    price,
                    imageURL,
                    eventLink: event.eventLink,
                    organizer,
                    UUID: eventUUID
                };

                allEvents.push(eventInfo);
                console.log(`Scraped event: ${title}`);
            }
        }

        const nextButton = await page.$('button[data-spec="page-next"]');
        if (nextButton) {
            await nextButton.click();
            await page.waitForTimeout(3000);
        } else {
            console.log("No more pages.");
            break;
        }
    }

    await page.close();
    return allEvents;
}

async function scrapeFacebookEvents(browser: puppeteer.Browser, url: string, maxScroll: number = 50): Promise<any[]> {
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'networkidle2' });
    await page.setViewport({ width: 1280, height: 800 });

    const allEvents: any[] = [];

    await scrollToBottom(page, maxScroll);
    const events = await page.$$eval('div.x1qjc9v5', cards => cards.map(card => {
        const eventLinkElement = card.querySelector('a');
        return {
            eventLink: eventLinkElement ? (eventLinkElement as HTMLAnchorElement).href : null
        };
    }));

    for (const event of events) {
        if (event.eventLink) {
            await page.goto(event.eventLink, { waitUntil: 'networkidle2' });
            const title = await page.$eval('span.x1lliihq', el => el.textContent?.trim() || '');
            const descriptionElement = await page.$('div.xdj266r');
            const description = descriptionElement ? await descriptionElement.evaluate(el => el.textContent?.trim() || 'No Description') : 'No Description';
            const locationElement = await page.$('div.x1i10hfl');
            const location = locationElement ? await locationElement.evaluate(el => el.textContent?.trim() || 'Unknown') : 'Unknown';
            const dateElement = await page.$('div.x1e56ztr');
            const date = dateElement ? await dateElement.evaluate(el => el.textContent?.trim() || '') : '';
            const imageURL = await page.$eval('img.xz74otr', el => (el as HTMLImageElement).src);
            const organizerElement = await page.$('span.xt0psk2');
            const organizer = organizerElement ? await organizerElement.evaluate(el => el.textContent?.trim() || 'Unknown') : 'Unknown';

            const [formattedStartDate, formattedEndDate] = formatDate(date) || ['', ''];
            const eventUUID = generateEventUUID(title, formattedStartDate, location);

            const eventInfo = {
                title,
                description,
                date: formattedStartDate,
                location,
                imageURL,
                eventLink: event.eventLink,
                organizer,
                UUID: eventUUID
            };

            allEvents.push(eventInfo);
            console.log(`Scraped event: ${title}`);
        }
    }

    await page.close();
    return allEvents;
}

(async () => {
    const browser = await puppeteer.launch({ headless: true });

    const sources = [
        {
            name: 'Facebook',
            url: 'https://www.facebook.com/events/explore/montreal-quebec/102184499823699/',
            scraper: scrapeFacebookEvents,
            maxScroll: 50
        },
        {
            name: 'Eventbrite',
            url: 'https://www.eventbrite.com/d/canada--montreal/all-events/',
            scraper: scrapeEventbriteEvents,
            maxPages: 3
        }
    ];

    const allEvents: any[] = [];
    for (const source of sources) {
        console.log(`Scraping events from: ${source.name}`);
        const events = await source.scraper(browser, source.url, source.maxPages || source.maxScroll);
        if (events) {
            allEvents.push(...events);
        } else {
            console.log("No events found.");
        }
    }

    fs.writeFileSync('events.json', JSON.stringify(allEvents, null, 4));

    await browser.close();
})();
