from RPA.Browser.Selenium import Selenium
import time
import urllib.request
import re
from function import create_file, contains_amount, get_date, create_directory
from RPA.Excel.Files import Files
from RPA.Tables import Tables
from RPA.Robocorp.WorkItems import WorkItems
import shutil

class SectionNotFoundError(Exception):
    pass

class NytimesSearcher:
    def __init__(self, url, date_number, phrase, categories, directory):
        self.url = url
        self.date_number = date_number
        self.phrase = phrase
        self.categories = categories
        self.directory = directory
        self.browser = Selenium()
        self.today, self.last = get_date(date_number)
        self.artifacts_dir = create_directory(directory, phrase)

    def search(self):
        try:
            self._open_nytimes()
            self._search_for()
            self._apply_date()
            self._apply_section()
            self._load_news()
            shutil.make_archive(self.artifacts_dir, 'zip', self.artifacts_dir)
        except SectionNotFoundError as snfe:
            print(snfe)
        except TimeoutError as te:
            print("Error: A TimeoutError occurred: ", te)
        except Exception as e:
            print("Error: An unexpected error occurred: ", e)
        finally:
            self.browser.close_all_browsers()

    def _open_nytimes(self):
        self.browser.open_available_browser(self.url)
        self.browser.maximize_browser_window()

    def _search_for(self):
        button_search = "xpath://button[@data-test-id='search-button']"
        input_phrase = "xpath://input[@data-testid='search-input']"
        self.browser.wait_until_element_is_visible(button_search)
        self.browser.click_element(button_search)
        self.browser.wait_until_element_is_visible(input_phrase)
        self.browser.input_text(input_phrase, self.phrase)
        self.browser.press_keys(input_phrase,"ENTER")

    def _apply_date(self):
        button_date = "xpath://button[@data-testid='search-date-dropdown-a']"
        label_dates = "xpath://button[@aria-label='Specific Dates']"
        input_date = "xpath://input[@id='startDate']"
        input_today = "xpath://input[@id='endDate']"
        self.browser.wait_until_element_is_visible(button_date)
        self.browser.click_element(button_date)
        self.browser.wait_until_element_is_visible(label_dates)
        self.browser.click_element(label_dates)
        self.browser.wait_until_element_is_visible(input_date)
        self.browser.input_text(input_date,self.last)
        self.browser.input_text(input_today,self.today)
        self.browser.press_keys(input_today,"ENTER")

    def _convert_string_to_list(self, Category):
        return ["Any"] if not Category else Category.split(',')

    def _apply_section(self):
        counter_section = 0
        list_category = self._convert_string_to_list(self.categories)
        button_section = "xpath://button[@data-testid='search-multiselect-button']"
        self.browser.wait_until_element_is_visible(button_section)
        self.browser.click_element(button_section)
        time.sleep(1)
        for section in list_category:
            input_seccion = f"xpath://span[text()='{section}']"
            try:
                self.browser.wait_until_element_is_visible(input_seccion,timeout=1)
                self.browser.click_element(input_seccion)
                counter_section +=1
            except Exception:
                raise SectionNotFoundError(f"Error finding the section: {section}")

    def _click_show_more(self):
        timeout = 10
        show_more_button= "xpath://button[@data-testid='search-show-more-button']"
        time.sleep(1)
        self.browser.press_key("tag=body","END")
        while(self.browser.is_element_enabled(show_more_button,timeout)):
            self.browser.set_focus_to_element(show_more_button)
            self.browser.click_element(show_more_button)
            self.browser.press_key("tag=body","END")
            time.sleep(1)

    def _download_image(self, url, file_name):
        urllib.request.urlretrieve(url, file_name)

    def _load_excel(self, result):
        ws = Files()
        tables = Tables()
        headers = ["title", "date", "description", "name_file", "number_of_phrases", "contains_money"]
        name_file = create_file(self.artifacts_dir, self.phrase,"xlsx")
        table = tables.create_table(data=result, columns=headers)
        ws.create_workbook(path=name_file,sheet_name=self.phrase,fmt="xlsx")
        ws.append_rows_to_worksheet(content=table,name=self.phrase,header=True)
        ws.save_workbook()

    def _extract_news_data(self, titles, descriptions, images, dates):
        news_data = []
        for i in range(len(titles)):
            title = titles[i].text
            description = descriptions[i].text
            date = dates[i+1].text
            src_image = images[i].get_attribute("src")
            name_file = create_file(self.artifacts_dir, self.phrase, "jpg")
            self._download_image(src_image, name_file)
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

    def _load_news(self):
        element_title = "xpath://li[@data-testid='search-bodega-result']//h4"
        element_date = "xpath://span[@data-testid='todays-date']"
        element_description = "//li[@data-testid='search-bodega-result']//a//p[1]"
        element_img = "xpath://li[@data-testid='search-bodega-result']//img"
        self._click_show_more()
        self.browser.wait_until_page_contains_element(element_date)
        titles = self.browser.find_elements(element_title)
        descriptions = self.browser.find_elements(element_description)
        images = self.browser.find_elements(element_img)
        dates = self.browser.find_elements(element_date)
        news_data = self._extract_news_data(titles, descriptions, images, dates)
        self._load_excel(news_data)

def main():
    wi = WorkItems()
    wi.get_input_work_item()
    url = wi.get_work_item_variable("URL")
    date_number = wi.get_work_item_variable("DATE_NUMBER")
    phrase = wi.get_work_item_variable("PHARASE")
    categories = wi.get_work_item_variable("CATEGORIES") 
    directory = wi.get_work_item_variable("DIRECTORY") 
    nytimes_searcher = NytimesSearcher(url, date_number, phrase, categories, directory)
    nytimes_searcher.search()

if __name__ == "__main__":
    main()
