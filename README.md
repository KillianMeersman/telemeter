# Telenet Telemeter parser
## About
This program queries the 'Mijn Telenet' site to retrieve data about a user's monthly Telenet internet usage (a.k.a. telemeter).\
It uses Selenium to do this as the site uses Javascript everywhere, please make sure you have Firefox and the Gecko driver installed.

Can be run as a standalone script or used as a Python 3 module.
If used as a standalone script it prints telemeter info to the console.
Main argument is a YAML file with your username and password:

```yaml
username: <username>
password: <password>
```

This script is not necessarily deterministic, due to the nature of the Telenet site it might error on one run and succeed on the other. If this happens often try increasing the timeout on the get_telemeter_json function.

## Requirements
1. Mozilla Firefox
2. Gecko driver (https://github.com/mozilla/geckodriver/releases)
