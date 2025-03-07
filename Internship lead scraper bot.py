import os
import time
import re
import csv
import keyboard
import urllib.parse
from collections import deque
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

###############################################################################
# Mappings for location, company size, and industry.
# Update these values if LinkedIn’s filter codes change.
###############################################################################
location_mapping = {
    "london": "90009496",
    "new york": "103644278",
    "san francisco": "103300454",
    "los angeles": "102264575",
    "chicago": "102261253",
    "boston": "102260243"
}

company_size_mapping = {
    "1": "B",  # 1-10 employees
    "2": "C",  # 11-50 employees
    "3": "D",  # 51-200 employees
    "4": "E",  # 201-500 employees
    "5": "F",  # 501-1000 employees
    "6": "G",  # 1001-5000 employees
    "7": "H",  # 5001-10000 employees
    "8": "I"   # 10001+ employees
}

industry_mapping = {
    "accommodation services": "2190",
    "administrative and support services": "1912",
    "construction": "48",
    "consumer services": "91",
    "education": "1999",
    "entertainment providers": "28",
    "farming, ranching, forestry": "201",
    "financial services": "43",
    "government administration": "75",
    "holding companies": "1905",
    "hospitals and health care": "14",
    "manufacturing": "25",
    "oil, gas, and mining": "332",
    "professional services": "1810",
    "real estate and equipment rental services": "1757",
    "retail": "27",
    "technology, information and media": "1594",
    "transportation, logistics, supply chain and storage": "116",
    "utilities": "59",
    "wholesale": "133"
}

###############################################################################
# User Console Inputs
###############################################################################
page_num = input("Enter the LinkedIn results page number to start from (default '1'): ").strip() or "1"
page_count = int(page_num)  # Initialize page counter

location_input = input("Enter the location (e.g. London, New York): ").strip().lower()
if location_input not in location_mapping:
    print(f"Location '{location_input}' not found in mapping. Defaulting to London.")
location_code = location_mapping.get(location_input, "90009496")
location_param = urllib.parse.quote(f'["{location_code}"]')

print("Select a company size:")
print("1 = 1-10 people")
print("2 = 11-50 people")
print("3 = 51-200 people")
print("4 = 201-500 people")
print("5 = 501-1000 people")
print("6 = 1001-5000 people")
print("7 = 5001-10000 people")
print("8 = 10001+ people")
company_size_choice = input("Enter your choice (default 1): ").strip() or "1"
if company_size_choice not in company_size_mapping:
    print(f"Company size choice '{company_size_choice}' not found. Defaulting to option 1.")
company_size_code = company_size_mapping.get(company_size_choice, "B")
company_size_param = urllib.parse.quote(f'["{company_size_code}"]')

industry_input = input("Enter the desired industry (e.g. financial services, construction): ").strip().lower()
if industry_input not in industry_mapping:
    print(f"Industry '{industry_input}' not found. Defaulting to financial services.")
industry_code = industry_mapping.get(industry_input, "43")
industry_param = urllib.parse.quote(f'["{industry_code}"]')

###############################################################################
# LinkedIn Credentials (Fill these in)
###############################################################################
LINKEDIN_EMAIL = ""      # <-- Put your email here
LINKEDIN_PASSWORD = ""   # <-- Put your password here

###############################################################################
# Build the LinkedIn Search URL dynamically using the user inputs
###############################################################################
START_URL = (
    "https://www.linkedin.com/search/results/companies/"
    f"?companyHqGeo={location_param}"
    f"&companySize={company_size_param}"
    f"&industryCompanyVertical={industry_param}"
    "&origin=FACETED_SEARCH"
    "&sid=v%40w"
    f"&page={page_num}"
)

###############################################################################
# CSV / Bot Settings
###############################################################################
LEADS_CSV = r"C:\Users\lukes\OneDrive\Desktop\Career\lead_contacts.csv"

running = False
seen_companies = set()
seen_emails = set()

TARGET_PREFIXES_WHITELIST = [
    "info@", "contact@", "hello@", "mail@", "support@", "team@",
    "enquiries@", "inquiries@", "help@", "admin@", "sales@", "office@"
]

###############################################################################
# Keyboard Hotkey (F8) to Pause/Resume
###############################################################################
def toggle_bot():
    global running
    running = not running
    print("Bot started." if running else "Bot stopped.")

keyboard.add_hotkey('F8', toggle_bot)

###############################################################################
# Chrome / Selenium Setup
###############################################################################
chrome_options = Options()
# Uncomment the line below to run headless:
# chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--remote-allow-origins=*")
chrome_options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=chrome_options)

###############################################################################
# Utility: Fast Scroll (one-time)
###############################################################################
def fast_scroll(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.5)

###############################################################################
# Utility: Scroll Down Page Fully
###############################################################################
def scroll_down_page(driver, wait_time=1, max_scrolls=5):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(wait_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

###############################################################################
# Cookie Acceptance Function
###############################################################################
def accept_cookies():
    possible_xpaths = [
        "//button[contains(text(),'Accept')]",
        "//button[contains(text(),'I Accept')]",
        "//button[contains(text(),'Accept All')]",
        "//button[contains(@class, 'cookie')]"
    ]
    for xp in possible_xpaths:
        try:
            button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, xp))
            )
            button.click()
            print("Accepted cookies using xpath:", xp)
            return True
        except Exception:
            continue
    return False

###############################################################################
# LinkedIn Login with Reduced Waits for Speed
###############################################################################
def linkedin_sign_in():
    for attempt in range(2):
        try:
            driver.get("https://www.linkedin.com/login")
            accept_cookies()
            email_field = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.clear()
            email_field.send_keys(LINKEDIN_EMAIL)
            password_field = driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(LINKEDIN_PASSWORD)
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Search')]"))
            )
            print("Signed in to LinkedIn successfully on attempt", attempt+1)
            return
        except Exception as e:
            print(f"Login attempt {attempt+1} failed:", e)
            time.sleep(1)
    print("All login attempts failed. Exiting.")
    exit(1)

###############################################################################
# Load Existing CSV
###############################################################################
def load_existing_leads(csv_path):
    if not os.path.isfile(csv_path):
        return
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers or len(headers) < 2:
                return
            for row in reader:
                if len(row) < 2:
                    continue
                c = row[0].strip()
                e = row[1].strip().lower()
                if c:
                    seen_companies.add(c)
                if e:
                    seen_emails.add(e)
    except Exception as ex:
        print("Error loading existing CSV data:", ex)

###############################################################################
# BFS Helpers
###############################################################################
def extract_domain_from_url(url):
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().lstrip("www.")
    except:
        return ""

def is_internal_url(link_url, domain):
    if not link_url or not domain:
        return False
    try:
        parsed = urlparse(link_url)
        return parsed.netloc.lower().endswith(domain)
    except:
        return False

def get_page_links(driver):
    elems = driver.find_elements(By.TAG_NAME, "a")
    return [e.get_attribute("href") for e in elems if e.get_attribute("href")]

###############################################################################
# Missing Functions Added
###############################################################################
def get_company_links_on_page():
    links = []
    try:
        elems = driver.find_elements(By.XPATH, "//a[contains(@href, '/company/')]")
        for elem in elems:
            href = elem.get_attribute("href")
            if href and href not in links:
                links.append(href)
    except Exception as e:
        print("Error retrieving company links:", e)
    return links

def get_company_field():
    try:
        industry_elem = driver.find_element(By.XPATH, "//*[contains(text(),'Industry')]/following-sibling::*")
        return industry_elem.text.strip() if industry_elem else ""
    except Exception:
        return ""

def find_email_in_page():
    email = find_mailto_emails(driver)
    if email:
        return email
    return find_emails_in_text(driver.page_source)

###############################################################################
# Scrape External Site for Email with Increased Waits and Full Scroll
###############################################################################
def scrape_site_for_email(driver, homepage_url, max_pages=3):
    visited = set()
    domain = extract_domain_from_url(homepage_url)
    queue = deque([homepage_url])
    visited.add(homepage_url)
    while queue and len(visited) <= max_pages:
        current_url = queue.popleft()
        driver.execute_script("window.open(arguments[0]);", current_url)
        WebDriverWait(driver, 15).until(lambda d: len(d.window_handles) >= 2)
        site_tab = driver.window_handles[-1]
        driver.switch_to.window(site_tab)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        handle_investor_prompt()
        fast_scroll(driver)
        scroll_down_page(driver, wait_time=1, max_scrolls=5)
        email = find_mailto_emails(driver)
        if not email:
            page_source = driver.page_source
            email = find_emails_in_text(page_source)
        if email:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            return email
        for link in get_page_links(driver):
            if is_internal_url(link, domain) and link not in visited:
                visited.add(link)
                queue.append(link)
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
    return None

def find_mailto_emails(driver):
    mailto_links = driver.find_elements(By.XPATH, "//a[starts-with(@href, 'mailto:')]")
    for link in mailto_links:
        mail_href = link.get_attribute("href")
        if mail_href:
            raw = mail_href.replace("mailto:", "").split("?")[0].strip()
            if raw and is_valid_email(raw):
                return raw
    return None

def find_emails_in_text(page_source):
    emails = re.findall(r'[\w\+._%\-]+@[\w\.\-]+\.\w+', page_source)
    if not emails:
        return None
    for email in emails:
        if is_valid_email(email):
            return email
    return None

###############################################################################
# Email Validation
###############################################################################
def is_valid_email(email: str) -> bool:
    email_lower = email.lower()
    if not any(email_lower.startswith(prefix) for prefix in TARGET_PREFIXES_WHITELIST):
        return False
    return True

###############################################################################
# Potential Investor/Disclaimer Popup
###############################################################################
def handle_investor_prompt():
    disclaimers_xpaths = [
        "//button[contains(text(),'Accept')]",
        "//button[contains(text(),'Agree')]",
        "//button[contains(text(),'Continue')]",
        "//button[contains(text(),'Confirm')]",
        "//button[contains(text(),'Yes')]",
        "//button[contains(text(),'Proceed')]",
        "//button[contains(text(),'I certify')]",
        "//button[contains(text(),'I acknowledge')]",
        "//button[contains(text(),'I agree')]",
    ]
    for xp in disclaimers_xpaths:
        try:
            disclaim_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, xp))
            )
            disclaim_btn.click()
            time.sleep(0.5)
            print(f"Clicked disclaimer/investor button: {xp}")
            break
        except:
            pass

###############################################################################
# Attempt to Click "About" Tab on LinkedIn
###############################################################################
def click_about_tab_if_possible():
    possible_selectors = [
        "//a[@data-control-name='page_member_main_nav_about_tab']",
        "//a[contains(@href,'/about/')]",
        "//a[text()='About']",
        "//li/a[contains(text(),'About')]",
    ]
    for sel in possible_selectors:
        try:
            about_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, sel))
            )
            about_btn.click()
            WebDriverWait(driver, 2).until(EC.title_contains("About"))
            return True
        except:
            pass
    return False

###############################################################################
# Process LinkedIn Company
###############################################################################
def process_company(company_url):
    company_name = None
    email = None
    field = ""
    try:
        if "/admin/" in company_url:
            print("Skipping invalid link:", company_url)
            return None, None, None
        driver.execute_script("window.open(arguments[0]);", company_url)
        WebDriverWait(driver, 8).until(lambda d: len(d.window_handles) >= 2)
        comp_tab = driver.window_handles[-1]
        driver.switch_to.window(comp_tab)
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(0.5)
        if click_about_tab_if_possible():
            print("Clicked About tab.")
        else:
            print("No About tab found.")
        time.sleep(0.5)
        title_text = driver.title
        if ": About" in title_text:
            company_name = title_text.split(": About")[0].strip()
        elif "|" in title_text:
            company_name = title_text.split("|")[0].strip()
        else:
            company_name = title_text.strip()
        company_name = re.sub(r'^\(\d+\)\s*', '', company_name)
        print("Inferred company name:", company_name)
        field = get_company_field()
        if field:
            print("Extracted field/service:", field)
        else:
            print("No field/service extracted.")
        fast_scroll(driver)
        website_url = None
        try:
            potential_links = driver.find_elements(
                By.XPATH,
                "//a[contains(@href,'http') and not(contains(@href,'linkedin.com'))]"
            )
            if potential_links:
                website_url = potential_links[0].get_attribute("href")
        except:
            pass
        if website_url:
            print("Found website URL:", website_url)
        else:
            print("No website URL found on LinkedIn page.")
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        if website_url:
            driver.execute_script("window.open(arguments[0]);", website_url)
            WebDriverWait(driver, 15).until(lambda d: len(d.window_handles) >= 2)
            site_tab = driver.window_handles[-1]
            driver.switch_to.window(site_tab)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            scroll_down_page(driver, wait_time=1, max_scrolls=5)
            try:
                contact_elems = driver.find_elements(By.XPATH, "//*[contains(translate(text(),'CONTACT','contact'), 'contact')]")
                for elem in contact_elems:
                    if elem.is_displayed() and elem.is_enabled():
                        try:
                            elem.click()
                            print("Clicked on a Contact link.")
                            break
                        except Exception:
                            continue
            except Exception as e:
                print("Error clicking Contact link:", e)
            email = find_email_in_page()
            if email:
                print("Found email:", email)
            else:
                print("No email found on external site.")
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
    except Exception as ex:
        print(f"Error processing {company_url}: {ex}")
    finally:
        while len(driver.window_handles) > 1:
            try:
                driver.switch_to.window(driver.window_handles[-1])
                driver.close()
            except:
                break
        driver.switch_to.window(driver.window_handles[0])
    return company_name, email, field

###############################################################################
# Update CSV File
###############################################################################
def update_csv_file(company_name, email):
    global seen_companies, seen_emails
    if not company_name or not email:
        return
    c = company_name.strip()
    e = email.strip().lower()
    if c in seen_companies or e in seen_emails:
        print(f"Duplicate. Skipping: {c} -> {e}")
        return
    print("Writing CSV entry to:", os.path.abspath(LEADS_CSV))
    print("Row to be written:", [c, e])
    try:
        file_exists = os.path.isfile(LEADS_CSV) and os.path.getsize(LEADS_CSV) > 0
        with open(LEADS_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Company", "Email"])
            writer.writerow([c, e])
        seen_companies.add(c)
        seen_emails.add(e)
        print(f"Updated CSV with: {c} -> {e}")
    except Exception as ex:
        print("Error updating CSV:", ex)

###############################################################################
# Improved Next Page Function with Narrowed XPath and JS Click Fallback
###############################################################################
def click_next_page(max_retries=5):
    for attempt in range(max_retries):
        try:
            next_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[normalize-space(@aria-label)='Next']"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            try:
                next_button.click()
            except Exception as e:
                print("Normal click failed, trying JS click:", e)
                driver.execute_script("arguments[0].click();", next_button)
            WebDriverWait(driver, 8).until(EC.staleness_of(next_button))
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"Attempt {attempt+1} to click next page failed: {e}")
            time.sleep(2)
    return False

###############################################################################
# Main Loop
###############################################################################
def main_loop():
    global page_count
    while True:
        if running:
            print(f"\n--- Checking search results page (Page {page_count}) ---")
            accept_cookies()
            fast_scroll(driver)
            company_links = get_company_links_on_page()
            print(f"Found {len(company_links)} companies on this page.")
            if not company_links:
                print("No company links found. Exiting loop.")
                break
            for link in company_links:
                if not running:
                    print("Bot paused/stopped mid-loop. Returning.")
                    return
                print(f"\nScraping {link} ...")
                comp_name, comp_email, comp_field = process_company(link)
                if comp_name and comp_email:
                    update_csv_file(comp_name, comp_email)
                else:
                    print("No valid company data extracted; skipping CSV update.")
                time.sleep(0.5)
            if not click_next_page():
                print("Next page not found. Refreshing page and retrying...")
                driver.refresh()
                time.sleep(5)
                if not click_next_page():
                    print("Still no next page found after refresh. Exiting main loop.")
                    break
            else:
                page_count += 1
                print(f"Now on page {page_count}")
        else:
            time.sleep(1)

###############################################################################
# Script Entry
###############################################################################
if __name__ == '__main__':
    print("Working directory:", os.getcwd())
    print("CSV will be written to:", os.path.abspath(LEADS_CSV))
    load_existing_leads(LEADS_CSV)
    linkedin_sign_in()
    driver.get(START_URL)
    accept_cookies()
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/company/')]"))
    )
    print("Initial LinkedIn search page loaded.")
    running = True
    print("Bot started. Press F8 to pause/resume scraping.")
    main_loop()
    driver.quit()
