import setuptools

with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="telemeter",
    version="3.0.0",
    author="Killian Meersman",
    author_email="hi@killianm.dev",
    description="Retrieves information about Telenet internet usage",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/KillianMeersman/telemeter",
    packages=setuptools.find_packages(),
    keywords="telenet telemeter",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "requests",
    ]
)
