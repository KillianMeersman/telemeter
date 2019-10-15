# Telenet Telemeter parser
## About
This program queries the 'Mijn Telenet' site to retrieve data about a user's monthly Telenet internet usage (a.k.a. telemeter).\
It uses Selenium to fetch the necessary cookies, please make sure you have Firefox and the Gecko driver installed.
The cookies are cached so subsequent calls will be much faster.

Can be run as a standalone script or used as a module.
If used as a standalone script it prints telemeter info to the console, credentials can be provided via environment variables (TELENET_USERNAME, TELENET_PASSWORD), else the user will be prompted for credentials.

## Installation
``` pip install telemeter ```

## Requirements
1. Mozilla Firefox
2. Gecko driver (https://github.com/mozilla/geckodriver/releases)
