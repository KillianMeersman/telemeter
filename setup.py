from distutils.core import setup

setup(
    name = "telemeter",
    packages = ["telemeter"],
    version = "0.1",
    description = "Gets information about monthly telenet internet usage",
    author = "Killian Meersman",
    author_email = "killian.meersman@gmail.com",
    url = "https://github.com/KillianMeersman/telemeter",
    download_url = "",
    keywords = ["telemeter", "telenet", "scraper"],
    classifiers = []
    install_requires = [
        "requests",
        "pyyaml"
    ]
)
