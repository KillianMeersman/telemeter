import json
import logging
import os
from datetime import datetime
from typing import List

import requests
from pydantic import BaseModel

TELENET_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.0%z"


logger = logging.getLogger("telemeter")


def _kibibyte_to_gibibyte(kib):
    return kib / (2 ** 20)


class UsageDay(BaseModel):
    """Represents a day of internet usage"""

    date: datetime
    peak_usage: int
    offpeak_usage: int
    total_usage: int

    def __str__(self):
        date_str = self.date.strftime("%Y-%m-%d")
        if self.peak_usage or self.offpeak_usage:
            peak_usage_gib = _kibibyte_to_gibibyte(self.peak_usage)
            offpeak_usage_gib = _kibibyte_to_gibibyte(self.offpeak_usage)
            return (
                f"{date_str}: {peak_usage_gib:4.2f} GiB\t{offpeak_usage_gib:4.2f} GiB"
            )
        else:
            usage_gib = _kibibyte_to_gibibyte(self.total_usage)
            return f"{date_str}: {usage_gib:4.2f} GiB"


class TelenetProductUsage(BaseModel):
    product_type: str
    squeezed: bool
    period_start: datetime
    period_end: datetime

    included_volume: int
    peak_usage: int
    offpeak_usage: int
    total_usage: int
    daily_usage: List[UsageDay]

    @classmethod
    def from_json(cls, data: dict):
        logger.debug(f"Parsing telemeter json: {json.dumps(data, indent=4)}")
        days = [
            UsageDay(
                date=datetime.strptime(x["date"], TELENET_DATETIME_FORMAT),
                peak_usage=x.get("peak", 0),
                offpeak_usage=x.get("offpeak", 0),
                total_usage=x.get("included", 0),
            )
            for x in data["totalusage"]["dailyusages"]
        ]

        peak_usage = data["totalusage"].get("peak", 0)
        offpeak_usage = data["totalusage"].get("offpeak", 0)

        included_usage = data["totalusage"].get("includedvolume", 0)
        extended_usage = data["totalusage"].get("extendedvolume", 0)

        total_usage = peak_usage + offpeak_usage + included_usage + extended_usage

        return cls(
            product_type=data["producttype"],
            squeezed=data["squeezed"],
            period_start=datetime.strptime(
                data["periodstart"], TELENET_DATETIME_FORMAT
            ),
            period_end=datetime.strptime(data["periodend"], TELENET_DATETIME_FORMAT),
            included_volume=data["includedvolume"],
            peak_usage=peak_usage,
            offpeak_usage=offpeak_usage,
            total_usage=total_usage,
            daily_usage=days,
        )

    def __str__(self):
        if self.peak_usage or self.offpeak_usage:
            peak_usage_gib = _kibibyte_to_gibibyte(self.peak_usage)
            offpeak_usage_gib = _kibibyte_to_gibibyte(self.offpeak_usage)
            return f"Usage for {self.product_type}: {peak_usage_gib:4.2f} GiB peak usage, {offpeak_usage_gib:4.2f} GiB offpeak usage"
        else:
            usage_gib = _kibibyte_to_gibibyte(self.total_usage)
            included_gib = _kibibyte_to_gibibyte(self.included_volume)
            return f"Usage for {self.product_type}: {usage_gib:4.2f} GiB of {included_gib:4.2f} GiB"


class Telemeter(BaseModel):
    period_start: datetime
    period_end: datetime
    products: List[TelenetProductUsage]

    @classmethod
    def from_json(cls, data: dict):
        for period in data["internetusage"][0]["availableperiods"]:
            # '2021-02-19T00:00:00.0+01:00'
            start = datetime.strptime(period["start"], TELENET_DATETIME_FORMAT)
            end = datetime.strptime(period["end"], TELENET_DATETIME_FORMAT)
            products = [TelenetProductUsage.from_json(x) for x in period["usages"]]
            yield cls(period_start=start, period_end=end, products=products)

    def __str__(self):
        s = f"Telemeter for {self.period_start} to {self.period_end}"
        for product in self.products:
            s += f"\n\t {product}"
        return s


class TelenetSession(object):
    def __init__(self):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "TelemeterPython/3"

    def login(self, username, password):
        # Get OAuth2 state / nonce
        r = self.s.get(
            "https://api.prd.telenet.be/ocapi/oauth/userdetails",
            headers={
                "x-alt-referer": "https://www2.telenet.be/nl/klantenservice/#/pages=1/menu=selfservice"
            },
            timeout=10,
        )

        # Return if already authenticated
        if r.status_code == 200:
            return

        assert r.status_code == 401
        state, nonce = r.text.split(",", maxsplit=2)

        # Log in
        r = self.s.get(
            f'https://login.prd.telenet.be/openid/oauth/authorize?client_id=ocapi&response_type=code&claims={{"id_token":{{"http://telenet.be/claims/roles":null,"http://telenet.be/claims/licenses":null}}}}&lang=nl&state={state}&nonce={nonce}&prompt=login',
            timeout=10,
        )
        r = self.s.post(
            "https://login.prd.telenet.be/openid/login.do",
            data={
                "j_username": username,
                "j_password": password,
                "rememberme": True,
            },
            timeout=10,
        )
        assert r.status_code == 200

        self.s.headers["X-TOKEN-XSRF"] = self.s.cookies.get("TOKEN-XSRF")

        r = self.s.get(
            "https://api.prd.telenet.be/ocapi/oauth/userdetails",
            headers={
                "x-alt-referer": "https://www2.telenet.be/nl/klantenservice/#/pages=1/menu=selfservice",
            },
            timeout=10,
        )
        assert r.status_code == 200

    def userdetails(self):
        r = self.s.get(
            "https://api.prd.telenet.be/ocapi/oauth/userdetails",
            headers={
                "x-alt-referer": "https://www2.telenet.be/nl/klantenservice/#/pages=1/menu=selfservice",
            },
        )
        assert r.status_code == 200
        return r.json()

    def telemeter(self):
        r = self.s.get(
            "https://api.prd.telenet.be/ocapi/public/?p=internetusage,internetusagereminder",
            headers={
                "x-alt-referer": "https://www2.telenet.be/nl/klantenservice/#/pages=1/menu=selfservice",
            },
            timeout=10,
        )
        assert r.status_code == 200
        return next(Telemeter.from_json(r.json()))


def _main():
    import argparse
    from getpass import getpass

    parser = argparse.ArgumentParser(
        prog="Telenet Telemeter parser",
        description="""
                    This program queries the 'Mijn Telenet' site to retrieve data about a user's Telemeter.
                    """,
    )
    parser.add_argument(
        "--display-days",
        dest="display_days",
        default=False,
        action="store_true",
        help="Display usage per-day",
    )
    args = parser.parse_args()

    # Attempt to get the API data
    print("Fetching Telemeter data")
    username = os.environ.get("TELENET_USERNAME") or input("Email: ")
    password = os.environ.get("TELENET_PASSWORD") or getpass("Password: ")

    session = TelenetSession()
    session.login(username, password)
    telemeter = session.telemeter()
    print(telemeter)

    if args.display_days:
        print()
        for product in telemeter.products:
            print(f"Daily usage information for {product.product_type}")
            for day in product.daily_usage:
                print("\t", day)


if __name__ == "__main__":
    _main()
