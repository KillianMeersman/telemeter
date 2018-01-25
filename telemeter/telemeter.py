import os
import json
from datetime import datetime, timedelta
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


class UsageDay():
    def __init__(self, date, peak_usage, offpeak_usage):
        self.date = date
        self.peak_usage = peak_usage
        self.offpeak_usage = offpeak_usage

    def __str__(self):
        return "{} - PEAK: {} GB, OFF-PEAK: {} GB".format(self.date, self.peak_usage, self.offpeak_usage)


class Telemeter():
    def __init__(self, peak_usage, offpeak_usage, squeezed, max_usage, days, period_start, period_end):
        self.peak_usage = peak_usage
        self.offpeak_usage = offpeak_usage
        self.squeezed = squeezed
        self.max_usage = max_usage
        self.days = days
        self.period_start = period_start
        self.period_end = period_end

    def percentage_used(self):
        return (self.peak_usage / self.max_usage) * 100

    def days_remaining(self):
        return (self.period_end - datetime.now()).days

    def __str__(self):
        return """Telemeter: You have used {}% of your monthly usage (limit {}GB)
            {} GB peak usage
            {} GB off-peak usage
            {} days remaining""".format(
            round(self.percentage_used(), 1),
            self.max_usage,
            round(self.peak_usage, 1),
            round(self.offpeak_usage, 1),
            self.days_remaining())


def get_telemeter_json(username, password):
    USER_AGENT = "Personal Telemeter scraper v2.0"
    os.environ['MOZ_HEADLESS'] = '1'

    profile = webdriver.FirefoxProfile()
    profile.set_preference("general.useragent.override", USER_AGENT)
    driver = webdriver.Firefox(profile)

    driver.get("https://mijn.telenet.be")
    WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, "login-button.tn-styling.ng-scope")))
    login_button_prt = driver.find_element_by_class_name("login-button.tn-styling.ng-scope")
    login_button = login_button_prt.find_element_by_xpath(".//div")
    login_button.click()

    # Fill in login form
    user_field = driver.find_element_by_id("j_username")
    user_field.send_keys(username)
    pass_field = driver.find_element_by_id("j_password")
    pass_field.send_keys(password)
    pass_field.send_keys(Keys.RETURN)

    # Wait for main page to load (needed for certain cookies I guess)
    WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, "pdPict")))

    driver.get("https://api.prd.telenet.be/ocapi/public/?p=internetusage")
    # source = driver.find_element_by_tag_name('body').text

    # Firefox wraps JSON in HTML so just make a simple request with Selenium's cookies (too lazy to deal with it)
    headers = {"User-Agent": USER_AGENT}
    cookies = {}
    # Get Selenium cookies
    for cookie in driver.get_cookies():
        cookies[cookie["name"]] = cookie["value"]

    r = requests.get("https://api.prd.telenet.be/ocapi/public/?p=internetusage", cookies=cookies, headers=headers)
    source = r.text

    try:
        j = json.loads(source)

        # Get max usage
        r = requests.get(j["internetusage"][0]["availableperiods"][0]["usages"][0]["specurl"], cookies=cookies, headers=headers)
        pro_j = json.loads(r.text)
        service_limit = int(pro_j["product"]["characteristics"]["service_category_limit"]["value"])
        service_limit_unit = pro_j["product"]["characteristics"]["service_category_limit"]["unit"]
        if service_limit_unit == "MB":
            service_limit /= 1000
        elif service_limit_unit == "TB":
            service_limit *= 1000

        return j, service_limit
    except Exception:
        raise Exception("Could not parse JSON, perhaps invalid credentials or no internet connection")
    finally:
        driver.quit()


def get_telemeter(username, password):
    t_json, service_limit = get_telemeter_json(username, password)
    current_usage = t_json["internetusage"][0]
    last_updated = current_usage["lastupdated"]

    current_usage = current_usage["availableperiods"][0]["usages"][0]
    period_start = datetime.strptime(current_usage["periodstart"][:10:], "%Y-%m-%d")
    period_end = datetime.strptime(current_usage["periodend"][:10:], "%Y-%m-%d")

    days = len(current_usage["totalusage"]["dailyusages"]) * [None]

    for idx, day in enumerate(current_usage["totalusage"]["dailyusages"]):
        days[idx] = UsageDay(datetime.strptime(day["date"][:day["date"].index('T')], "%Y-%m-%d").date(),
                             day["peak"] / 1E6,
                             day["offpeak"] / 1E6
                             )

    return Telemeter(
        current_usage["totalusage"]["peak"] / 1E6,
        current_usage["totalusage"]["offpeak"] / 1E6,
        current_usage["squeezed"],
        service_limit,
        days,
        period_start,
        period_end
    )


if __name__ == "__main__":
    import yaml
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="yaml file containing username and password")
    args = parser.parse_args()

    with open(args.config, 'r') as config:
        y = yaml.load(config)
        username = y["username"]
        password = y["password"]

    print("Fetching info, please wait...")
    print(get_telemeter(username, password))
