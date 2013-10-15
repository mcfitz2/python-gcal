import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "gcal",
    version = "0.0.1",
    author = "Micah Fitzgerald",
    author_email = "mifitzge@indiana.edu",
    description = ("Simple library that makes interacting with the Google Calendar API a little less painful"),
    license = "BSD",
    keywords = "",
#    url = "http://packages.python.org/an_example_pypi_project",
    packages=['gcal'],
#    long_description=read('README'),
#    classifiers=[
#        "Development Status :: 3 - Alpha",
#        "Topic :: Utilities",
#        "License :: OSI Approved :: BSD License",
#    ],
)
