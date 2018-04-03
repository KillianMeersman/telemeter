from distutils.core import setup

setup(
    name = "telemeter",
    packages = ["telemeter"],
    version = "2.0",
    description = "Gets information about monthly Telenet internet usage",
    author = "Killian Meersman",
    author_email = "killian.meersman@gmail.com",
    url = "https://github.com/KillianMeersman/telemeter",
    download_url = "https://github.com/KillianMeersman/telemeter/archive/v2.0.tar.gz",
    keywords = ["telemeter", "telenet", "scraper"],
    classifiers = [],
    install_requires = [
        "requests",
        "pyyaml",
        "selenium"
    ]
)
