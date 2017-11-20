import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import datetime
import time


class UsageDay():
    def __init__(self, date, peak_usage, offpeak_usage):
        self.date = date
        self.peak_usage = peak_usage
        self.offpeak_usage = offpeak_usage

    def __str__(self):
        return "{} - PEAK: {} OFF-PEAK: {}".format(self.date, self.peak_usage, self.offpeak_usage)


class Telemeter():
    def __init__(self, peak_usage, offpeak_usage, squeeze, detailed_usage,
                 peak_percentage, offpeak_percentage, squeeze_percentage):
        self.peak_usage = peak_usage
        self.offpeak_usage = offpeak_usage
        self.squeeze = squeeze
        self.detailed_usage = detailed_usage
        self.peak_percentage = peak_percentage
        self.offpeak_percentage = offpeak_percentage
        self.squeeze_percentage = squeeze_percentage

    def __str__(self):
        return "Telemeter: You have used {}% of your monthly usage\n\t{} GB peak usage\n\t{} GB off-peak usage".format(
            round(self.squeeze_percentage, 1),
            round(self.peak_usage, 1),
            round(self.offpeak_usage, 1))


def get_telemeter_json(username, password):
    profile = webdriver.FirefoxProfile()
    profile.set_preference("general.useragent.override", "Personal Telemeter scraper v2.0")
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

    driver.get("https://api.prd.telenet.be/ocapi/public/?p=internetusage,internetusagereminder")
    # print(driver.page_source)
    try:
        j = json.loads(driver.page_source)
        return j
    except Exception:
        raise Exception("Invalid credentials or no internet connection")


def get_telemeter(username, password):
    t_json = get_telemeter_json(username, password)
    days = len(t_json["days"]) * [None]

    current_year_str = "/{}".format(datetime.now().year)
    for idx, date_string in enumerate(t_json["days"]):
        days[idx] = UsageDay(datetime.strptime(date_string + current_year_str, "%d/%m/%Y").date(), t_json["detailedPeakUsage"][idx], t_json["detailedOffPeakUsage"][idx])

    return Telemeter(
        t_json["peakUsage"],
        t_json["offPeakUsage"],
        t_json["squeeze"],
        days,
        t_json["peakUsagePercentage"],
        t_json["offPeakUsagePercentage"],
        t_json["squeezePercentage"]
    )


if __name__ == "__main__":
    import yaml
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="the config file")
    args = parser.parse_args()

    with open(args.config, 'r') as config:
        y = yaml.load(config)
        username = y["username"]
        password = y["password"]

    print(get_telemeter(username, password))
