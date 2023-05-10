from RPA.Browser.Selenium import Selenium
import time
import urllib.request
import re
from function import create_file_directory, contains_amount, get_date, init_config, convert_string_to_list
from openpyxl import Workbook


class NYTimesScraper:
    def __init__(self, config):
        self.browser = Selenium()
        self.url = config["URL"]
        self.date_number = config["DATE_NUMBER"]
        self.phrase = config["PHRASE"]
        self.categories = config["CATEGORIES"]
        self.directory = config["DIRECTORY"]

    def open_nytimes(self):
        self.browser.open_available_browser(self.url)
        self.browser.maximize_browser_window()

    def search_for(self):
        button_search = "xpath://button[@data-test-id='search-button']"
        input_phrase = "xpath://input[@data-testid='search-input']"

        self.browser.wait_until_element_is_visible(button_search)
        self.browser.click_element(button_search)
        self.browser.wait_until_element_is_visible(input_phrase)
        self.browser.input_text(input_phrase, self.phrase)
        self.browser.press_keys(input_phrase, "ENTER")

    def apply_date(self):
        today, last = get_date(self.date_number)
        button_date = "xpath://button[@data-testid='search-date-dropdown-a']"
        label_dates = "xpath://button[@aria-label='Specific Dates']"
        input_date = "xpath://input[@id='startDate']"
        input_today = "xpath://input[@id='endDate']"

        self.browser.wait_until_element_is_visible(button_date)
        self.browser.click_element(button_date)
        self.browser.wait_until_element_is_visible(label_dates)
        self.browser.click_element(label_dates)
        self.browser.wait_until_element_is_visible(input_date)
        self.browser.input_text(input_date, last)
        self.browser.input_text(input_today, today)
        self.browser.press_keys(input_today, "ENTER")

    def apply_section(self):
        counter_section = 0
        list_category = convert_string_to_list(self.categories)
        button_section = "xpath://button[@data-testid='search-multiselect-button']"

        self.browser.wait_until_element_is_visible(button_section)
        self.browser.click_element(button_section)

        time.sleep(1)

        for section in list_category:
            input_seccion = f"xpath://span[text()='{section}']"
            try:
                self.browser.wait_until_element_is_visible(input_seccion, timeout=1)
                self.browser.click_element(input_seccion)
                counter_section += 1
            except Exception:
                print(f"Error finding the section: {section}")

        return counter_section

    def click_show_more(self):
        timeout = 10
        show_more_button = "xpath://button[@data-testid='search-show-more-button']"

        time.sleep(2)

        while self.browser.is_element_enabled(show_more_button, timeout):
            self.browser.set_focus_to_element(show_more_button)
            self.browser.click_element(show_more_button)
            time.sleep(2)

    def download_image(self, url, nombre_archivo):
        urllib.request.urlretrieve(url, nombre_archivo)

    def load_excel(self, result):
        name_file = create_file_directory(self.directory, self.phrase, "xlsx")
        wb = Workbook()
        ws = wb.active
        ws.append(["title", "date", "description", "name_file", "number_of_phrases", "contains_money"])
        for res in result:
            ws.append([
                res["title"],
                res["date"],
                res["description"],
                res["name_file"],
                res["number_of_phrases"],
                res["contains_money"]
            ])

        wb.save(name_file)
        
    def extract_news_data(self, titles, descriptions, images, dates):
        news_data = []

        for i in range(len(titles)):
            title = titles[i].text
            description = descriptions[i].text
            date = dates[i + 1].text
            src_image = images[i].get_attribute("src")

            name_file = create_file_directory(self.directory, self.phrase, "jpg")
            self.download_image(src_image, name_file)

            number_of_phrases = len(re.findall(self.phrase, title + description, re.IGNORECASE))
            contains_money = contains_amount(title, description)

            news_data.append({
                "title": title,
                "date": date,
                "description": description,
                "name_file": name_file,
                "number_of_phrases": number_of_phrases,
                "contains_money": contains_money
            })

        return news_data

    def load_news(self):
        element_title = "xpath://h4[@class='css-2fgx4k']"
        element_date = "xpath://span[@data-testid='todays-date']"
        element_description = "xpath://p[@class='css-16nhkrn']"
        element_img = "xpath://img[@class='css-rq4mmj']"

        self.click_show_more()

        self.browser.wait_until_page_contains_element(element_date)
        titles = self.browser.find_elements(element_title)
        descriptions = self.browser.find_elements(element_description)
        images = self.browser.find_elements(element_img)
        dates = self.browser.find_elements(element_date)

        news_data = self.extract_news_data(titles, descriptions, images, dates)
        self.load_excel(news_data)

    def run(self):
        try:
            self.open_nytimes()
            self.search_for()
            self.apply_date()
            counter_section = self.apply_section()
            if counter_section != 0:
                self.load_news()
            else:
                print("No se ingreso ninguna categoria valida")
        except TimeoutError as te:
            print("Error: A TimeoutError occurred: ", te)
        except Exception as e:
            print("Error: An unexpected error occurred: ", e)
        finally:
            self.browser.close_all_browsers()


def main():
    config = init_config("devdata\env.json")
    scraper = NYTimesScraper(config)
    scraper.run()


if __name__ == "__main__":
    main()
