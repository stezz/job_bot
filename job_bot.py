import logging
import requests
import base64
from email.utils import formataddr

from email_utils import Email
from email_utils import EmailConnection
from bs4 import BeautifulSoup
import os
import pickle

from configparser import ConfigParser

CONF_FILE = "config.ini"
CACHE_FILE = "cache.db"


def main():
    config = get_config(CONF_FILE)
    defaults = config["DEFAULT"]
    BASE_URL = defaults["base_url"]
    FIRST_PAGE = defaults["first_page"]
    url = BASE_URL + FIRST_PAGE

    results = get_page_data(url)
    # print(results)
    message = ""
    if results:
        for k in results.keys():
            message += "<b>{}</b> ({})<br>{}<br><br>".format(
                results[k]["position"], k, results[k]["skills"]
            )
        send_email("stefano.mosconi@blackbelts.fi", message, defaults)
    else:
        logger.info("No new jobs found")


# inspiration from https://datascience.blog.wzb.eu/2016/08/12/a-tip-for-the-impatient-simple-caching-with-python-pickle-and-decorators/
def cache_this(cachefile):
    """
    A function that creates a decorator which will use "cachefile"
    for caching the results of the decorated function "fn", checks for new results
    returns only the new results.
    """

    def decorator(fn):  # define a decorator for a function "fn"
        def wrapped(
            *args, **kwargs
        ):  # define a wrapper that will finally call "fn" with all arguments
            # if cache exists -> load it and return its content
            old_results = {}
            new_results = {}
            if os.path.exists(cachefile):
                with open(cachefile, "rb") as cachehandle:
                    logger.info("using cached result from '%s'" % cachefile)
                    old_results = pickle.load(cachehandle)

            # execute the function with all arguments passed
            res = fn(*args, **kwargs)

            for item in res.keys():
                if item not in old_results.keys():
                    new_results[item] = res[item]

            # write to cache file
            with open(cachefile, "wb") as cachehandle:
                logger.info("saving result to cache '%s'" % cachefile)
                pickle.dump(res, cachehandle)

            return new_results

        return wrapped

    return decorator  # return this "customized" decorator that uses "cachefile"


@cache_this(CACHE_FILE)
def get_page_data(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    joblist = {}
    jobul = soup.find("ul", {"class": "wrapper"})
    if jobul:
        for p in jobul.findAll("a"):
            link = p.get("href")
            title = p.find("h2")
            skills = ", ".join([i.text for i in p.findAll("li")])
            joblist[link] = {"position": title.text, "skills": skills}
    return joblist


def send_email(to_addr, message, config):
    defaults = config
    smtp_pwd = defaults["smtp_pwd"]
    smtp_user = defaults["smtp_user"]
    smtp_port = defaults["smtp_port"]
    smtp_server = defaults["smtp_server"]
    smtp_from = defaults["smtp_from"]

    logger.debug("Connecting to email server ({})".format(smtp_server))
    server_str = smtp_server + ":" + str(smtp_port)
    server = EmailConnection(server_str, smtp_user, smtp_pwd)

    to_addr = formataddr((smtp_from, smtp_user))
    from_addr = formataddr((smtp_from, smtp_user))
    subject = "New jobs found"
    mail = Email(
        from_=from_addr,
        to=to_addr,
        message_type="html",
        subject=subject,
        message=message,
        message_encoding="utf-8",
    )
    logger.info("Sending earning statements to {}".format(to_addr))
    server.send(mail)
    server.close()


def get_config(configfile):
    """Gets config options"""
    if os.path.exists(configfile):
        logger.debug("Found config file at {}".format(configfile))
        config = ConfigParser()
        config.read(configfile)
    else:
        logger.error(
            "Config file not found: {}. Please create and restart.".format(configfile)
        )
        config = None
    return config


# start main app
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
main()
