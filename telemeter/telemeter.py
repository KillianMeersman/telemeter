import requests
import json
from datetime import datetime


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


def get_telemeter_json(username, password, identifier):
    USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1"
    headers = {'User-Agent': USER_AGENT}
    payload = {"j_username": username, "j_password": password, "rememberme": True}

    s = requests.Session()
    s.headers.update(headers)

    r = s.get("https://mijn.telenet.be")
    r = s.post("https://login.prd.telenet.be/openid/login.do", data=payload)
    r = s.get("https://mijn.telenet.be/mijntelenet/navigation/navigation.do?family=DEFAULT&identifier=DEFAULT")
    r = s.get("https://mijn.telenet.be/mijntelenet/telemeter/data/usageDetails.do?identifier={}".format(identifier))
    try:
        return r.json()["fup"]
    except json.decoder.JSONDecodeError:
        raise Exception("Invalid credentials or no internet connection")


def get_telemeter(username, password, identifier):
    t_json = get_telemeter_json(username, password, identifier)
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
        identifier = y["identifier"]

    print(get_telemeter(username, password, identifier))
