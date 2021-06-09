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


class UnauthorizedException(Exception):
    pass


class UsageDay(BaseModel):
    """Represents a day of internet usage"""

    date: datetime
    peak_usage: int
    offpeak_usage: int

    def __str__(self):
        peak_usage_gib = _kibibyte_to_gibibyte(self.peak_usage)
        offpeak_usage_gib = _kibibyte_to_gibibyte(self.offpeak_usage)
        return f"{self.date.strftime('%Y-%m-%d')}: {peak_usage_gib:4.2f} GiB\t{offpeak_usage_gib:4.2f} GiB"


class TelenetProductUsage(BaseModel):
    product_type: str
    squeezed: bool
    period_start: datetime
    period_end: datetime

    included_volume: int
    peak_usage: int
    offpeak_usage: int
    daily_usage: List[UsageDay]

    @classmethod
    def from_json(cls, data: dict):
        logger.debug(f"Parsing telemeter json: {json.dumps(data, indent=4)}")
        days = [
            UsageDay(
                date=datetime.strptime(x["date"], TELENET_DATETIME_FORMAT),
                peak_usage=x["peak"],
                offpeak_usage=x["offpeak"],
            )
            for x in data["totalusage"]["dailyusages"]
        ]

        return cls(
            product_type=data["producttype"],
            squeezed=data["squeezed"],
            period_start=datetime.strptime(
                data["periodstart"], TELENET_DATETIME_FORMAT
            ),
            period_end=datetime.strptime(data["periodend"], TELENET_DATETIME_FORMAT),
            included_volume=data["includedvolume"],
            peak_usage=data["totalusage"]["peak"],
            offpeak_usage=data["totalusage"]["offpeak"],
            daily_usage=days,
        )

    def __str__(self):
        peak_usage_gib = _kibibyte_to_gibibyte(self.peak_usage)
        offpeak_usage_gib = _kibibyte_to_gibibyte(self.offpeak_usage)
        return f"Usage for {self.product_type}: {peak_usage_gib:4.2f} GiB peak usage, {offpeak_usage_gib:4.2f} GiB offpeak usage"


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
        self.s.headers[
            "User-Agent"
        ] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36"

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
        self.s.get(
            f"https://login.prd.telenet.be/openid/oauth/authorize?client_id=ocapi&response_type=code&claims=%7B%22id_token%22%3A%7B%22http%3A%2F%2Ftelenet.be%2Fclaims%2Froles%22%3Anull%2C%22http%3A%2F%2Ftelenet.be%2Fclaims%2Flicenses%22%3Anull%7D%7D&lang=nl&state={state}&nonce={nonce}&prompt=login",
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

        self.s.headers["X-TOKEN-XSRF"] = self.s.cookies["TOKEN-XSRF"]

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
