import os
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By


USER_AGENT = "Personal Telemeter scraper v2.0"


class UnauthorizedException(Exception):
    pass


class UsageDay(object):
    """Represents a day of internet usage"""

    def __init__(self, date, peak_usage, offpeak_usage):
        self.date = date
        self.peak_usage = peak_usage
        self.offpeak_usage = offpeak_usage

    def __str__(self):
        return "{} - PEAK: {} GB, OFF-PEAK: {} GB".format(self.date, self.peak_usage, self.offpeak_usage)


class Telemeter(object):
    """Telemeter object as presented by Telenet"""

    def __init__(self, peak_usage, offpeak_usage, squeezed, max_usage, days, period_start, period_end):
        self.peak_usage = peak_usage
        self.offpeak_usage = offpeak_usage
        self.squeezed = squeezed
        self.max_usage = max_usage
        self.days = days
        self.period_start = period_start
        self.period_end = period_end

    @staticmethod
    def from_json(meter_json, service_limit):
        """Converts telemeter JSON and a service limit in GB to a Telemeter instance"""

        try:
            current_usage = meter_json["internetusage"][0]["availableperiods"][0]["usages"][0]
        except KeyError:
            raise RuntimeError("Unexpected JSON received")

        # Get period start & end date
        period_start = current_usage["periodstart"]
        period_start = datetime.strptime(
            period_start[:period_start.index('T')], "%Y-%m-%d")
        period_end = current_usage["periodend"]
        period_end = datetime.strptime(
            period_end[:period_end.index('T')], "%Y-%m-%d")

        # Enumerate days
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


def get_telemeter_cookies(username, password, timeout=3, headless=True):
    """Returns cookies after establishing a session using Firefox Gecko driver"""

    if headless:
        os.environ['MOZ_HEADLESS'] = '1'

    # Connect to webdriver
    profile = webdriver.FirefoxProfile()
    profile.set_preference("general.useragent.override", USER_AGENT)
    driver = webdriver.Firefox(profile)

    try:
        # login page
        driver.get("https://mijn.telenet.be")

        # wait for login button to load
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located(
            (By.CLASS_NAME, "login-button.tn-styling.ng-scope")))

        # Navigate to login form
        login_button_prt = driver.find_element_by_class_name(
            "login-button.tn-styling.ng-scope")
        login_button = login_button_prt.find_element_by_xpath(".//div")
        login_button.click()

        # Fill in login form
        user_field = driver.find_element_by_id("j_username")
        user_field.send_keys(username)
        pass_field = driver.find_element_by_id("j_password")
        pass_field.send_keys(password)
        pass_field.send_keys(Keys.RETURN)

        # Wait for main page to load
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, "pdPict")))

        # Get JSON endpoint, for some reason this has to be done with Selenium first.
        # Presumably some kind of authentication cookie or CSRF protection is the culprit
        driver.get("https://api.prd.telenet.be/ocapi/public/?p=internetusage")

        cookies = {}

        # Copy webdriver cookies to dictionary
        for cookie in driver.get_cookies():
            cookies[cookie["name"]] = cookie["value"]

        return cookies

    except TimeoutException:
        raise RuntimeError("Connection timed out")
    finally:
        driver.quit()


def get_telemeter_json(cookies):
    """Returns a tuple containing the Telemeter JSON and the max usage/month in GB"""

    # Firefox wraps JSON in HTML so just make a simple request with Selenium's cookies
    headers = {"User-Agent": USER_AGENT}

    # Get JSON endpoint again with raw request
    r = requests.get("https://api.prd.telenet.be/ocapi/public/?p=internetusage",
                     cookies=cookies, headers=headers)

    if r.status_code == 401:
        raise UnauthorizedException("Request returned 401")

    meter_json = json.loads(r.text)

    # Get max usage
    spec_url = meter_json["internetusage"][0]["availableperiods"][0]["usages"][0]["specurl"]
    r = requests.get(spec_url, cookies=cookies, headers=headers)

    # parse JSON
    spec_json = json.loads(r.text)
    service_limit = int(
        spec_json["product"]["characteristics"]["service_category_limit"]["value"])
    service_limit_unit = spec_json["product"]["characteristics"]["service_category_limit"]["unit"]

    if service_limit_unit == "MB":
        service_limit /= 1000
    elif service_limit_unit == "TB":
        service_limit *= 1000

    return (meter_json, service_limit)


def _main():
    from getpass import getpass
    import argparse

    parser = argparse.ArgumentParser(
        prog="Telenet Telemeter parser",
        description="""
                    This program queries the 'Mijn Telenet' site to retrieve data about a user's Telemeter.
                    It uses Selenium to do this so make sure you have the Gecko driver installed.

                    The program will try and read credentials from the following environment variables:

                    TELENET_USERNAME
                    TELENET_PASSWORD

                    If it cannot find these variables, the user will be prompted for username and password
                    """
    )
    parser.add_argument("--no-headless", dest='headless', default=True, action='store_false',
                        help="Run the Gecko driver with GUI")
    parser.add_argument("--no-cache", dest='cache', default=True, action='store_false',
                        help="Do not cache cookies")
    parser.add_argument("--cache-file", dest='cache_file', default='./cookies.json',
                        help="JSON file in which cookies are cached, default is ./cookies.json")
    args = parser.parse_args()

    if args.cache and os.path.isfile(args.cache_file):
        with open(args.cache_file, 'r') as f:
            cookies = json.loads(f.read())

        try:
            print("Using cached cookies")
            meter_json, service_limit = get_telemeter_json(cookies)
            print(Telemeter.from_json(meter_json, service_limit))
            return
        except UnauthorizedException:
            print("Cached cookies invalidated, removing")
            os.remove(args.cache_file)

    username = os.environ.get('TELENET_USERNAME', None)
    password = os.environ.get('TELENET_PASSWORD', None)

    if username is None:
        username = input('Username: ')

    if password is None:
        password = getpass('Password: ')

    print("Fetching cookies")
    cookies = get_telemeter_cookies(username, password, headless=args.headless)
    with open('cookies.json', 'w+') as f:
        f.write(json.dumps(cookies))

    print("Fetching Telemeter data")
    meter_json, service_limit = get_telemeter_json(cookies)
    print(Telemeter.from_json(meter_json, service_limit))


if __name__ == "__main__":
    _main()
