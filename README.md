# Telemeter

This script fetches information about your monthly Telenet internet usage (a.k.a. the telemeter).\
Now uses Selenium as the new site won't even load properly without 1MB of javascript and I don't have the time to figure out all the necessary requests.

Returns a Telemeter object or prints telemeter info to the console.\
Main argument is a yaml file with your username and password:

username: <username>\
password: <password>

Make sure to install Firefox and the Gecko driver.\
https://github.com/mozilla/geckodriver/releases \
http://selenium-python.readthedocs.io/installation.html
