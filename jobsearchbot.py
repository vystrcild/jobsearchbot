import requests
from bs4 import BeautifulSoup
import json
from sqlalchemy import create_engine, Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
import time
import os
from dotenv import load_dotenv
import logging.config

load_dotenv()
logging.config.fileConfig('logging.ini', disable_existing_loggers=False)
logger = logging.getLogger("debugLogger")

# Innit DB connection & innit ORM base class
engine = create_engine("sqlite:///db.db")
conn = engine.connect()
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

# Discord bot webhook
webhook = os.environ["DISCORD_URL"]


class Jobs(Base):
    """
    DB table Jobs
    """
    __tablename__ = "jobs"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    position_name = Column("position_name", String)
    company_name = Column("company_name", String)
    link = Column("link", String)
    location = Column("location", String)
    portal = Column("portal", String)
    portal_logo = Column("portal_logo", String)
    posted = Column("posted", String, default="not-posted")
    __table_args__ = (UniqueConstraint('position_name', 'company_name', name='uq_1'),
                      )    # In case of same job offer on different portals (eliminate duplicates)


# Create table(s) if not created yet
Base.metadata.create_all(engine)


class JobPortal:
    def fetch_data(self, url):
        r = requests.get(url)
        soup = BeautifulSoup(r.content, "html.parser")
        return soup

    def insert_db(self):
        try:
            data = self.create_dict()
            for i in data:
                try:
                    session.add(Jobs(**i))
                    session.commit()
                except SQLAlchemyError:
                    session.rollback()
        except AttributeError:
            # Log errors while parsing data
            logger.exception(f"Error while parsing data for {self.__class__.__name__}")


class Jobscz(JobPortal):
    def __init__(self):
        self.url = "https://www.jobs.cz/prace/brno/?q%5B%5D=python&date=7d&locality%5Bradius%5D=0"
        soup = JobPortal.fetch_data(self, self.url)
        self.results = soup.find_all("div", class_="standalone search-list__item")[1:]

    def create_dict(self):
        job_positions = []
        for result in self.results:
            job_position = {}
            if result.find("a", class_="search-list__main-info__title__link") is None:
                pass
            else:
                job_position["portal"] = "jobs.cz"
                job_position["portal_logo"] = "https://www.mimir.nu/wp-content/uploads/2016/09/logo-jobs-cz-200x200.png"
                job_position["position_name"] = result.find("a",
                                                            class_="search-list__main-info__title__link").get_text()
                job_position["company_name"] = result.find("div",
                                                           class_="search-list__main-info__company").get_text().strip()
                job_position["link"] = result.find("a", class_="search-list__main-info__title__link")["href"]
                job_position["location"] = result.find("div", class_="search-list__main-info__address") \
                    .find_all("span")[1].get_text().strip()
                job_positions.append(job_position)
        return job_positions


class Startupjobs(JobPortal):
    def __init__(self):
        url = "https://www.startupjobs.cz/api/nabidky?location[]=ChIJEVE_wDqUEkcRsLEUZg-vAAQ&technological-tag[]" \
              "=908&page=1"
        r = requests.get(url)
        r_dict = json.loads(r.content.decode('utf-8'))
        self.results = r_dict["resultSet"]

    def create_dict(self):
        job_positions = []
        for result in self.results:
            job_position = {}
            job_position["portal"] = "startupjobs.cz"
            job_position["portal_logo"] = "https://pbs.twimg.com/profile_images/1343501052646199296/cLKa00_w_400x400" \
                                          ".jpg"
            job_position["position_name"] = result["name"]
            job_position["company_name"] = result["companyName"]
            job_position["link"] = result["detail"]
            job_position["location"] = ", ".join(str(elem) for elem in result["locations"])
            job_positions.append(job_position)
        return job_positions


class Juniorguru(JobPortal):
    def __init__(self):
        self.url = "https://junior.guru/jobs/"
        soup = JobPortal.fetch_data(self, self.url)
        self.results = soup.find_all("li", class_="jobs__item")

    def create_dict(self):
        job_positions = []
        for result in self.results:
            job_position = {}
            job_position["portal"] = "junior.guru"
            job_position["portal_logo"] = "https://junior.guru/static/images/logo.svg"
            job_position["position_name"] = result.find("h3", class_="jobs__title").get_text()
            job_position["company_name"] = result.find("p", class_="jobs__company").find("span").get_text()
            job_position["link"] = result.find("a", class_="jobs__link")["href"]
            job_position["location"] = result.find("p", class_="jobs__location").get_text()
            job_positions.append(job_position)
        return job_positions


class Jobsik(JobPortal):
    def __init__(self):
        self.url = "https://www.jobsik.cz/search/?category=Python&region=Brno"
        soup = JobPortal.fetch_data(self, self.url)
        if soup.find("p", class_="alert alert-warning"):
            self.results = []
        else:
            self.results = soup.find_all("div", class_="job-item")

    def create_dict(self):
        job_positions = []
        for result in self.results:
            job_position = {}
            job_position["portal"] = "jobsik.cz"
            job_position["portal_logo"] = "https://www.dobraprace.cz/images/web/cenik-logo-js.png"
            job_position["position_name"] = result.find("a", class_="job-item__link").get_text()
            job_position["company_name"] = result.find("span", class_="job-item__company").get_text()
            job_position["link"] = "https://www.jobsik.cz" + result.find("a", class_="job-item__link")["href"]
            job_position["location"] = result.find("span", class_="job-item__place--district").get_text()
            job_positions.append(job_position)
        return job_positions


class Linkedin(JobPortal):
    def __init__(self):
        self.url = "https://www.linkedin.com/jobs/search?keywords=Python&location=Brno%2C%20Jihomoravsk%C3%BD%2C%20" \
                   "%C4%8Cesko&geoId=101164731&trk=public_jobs_jobs-search-bar_search-submit&redirect=false&position" \
                   "=1&pageNum=0"
        soup = JobPortal.fetch_data(self, self.url)
        self.results = soup.find_all("li", class_="result-card job-result-card result-card--with-hover-state")

    def create_dict(self):
        job_positions = []
        for result in self.results:
            job_position = {}
            job_position["portal"] = "linkedin"
            job_position["portal_logo"] = "https://www.freelogovectors.net/wp-content/uploads/2020/01/linkedin-logo.png"
            job_position["position_name"] = result.find("h3",
                                                        class_="result-card__title job-result-card__title").get_text()
            if result.find("a", class_="result-card__subtitle-link job-result-card__subtitle-link") is None:
                if result.find("a", class_="job-card-container__link") is None:
                    job_position["company_name"] = "Unknown"
                else:
                    job_position["company_name"] = result.find("a", class_="job-card-container__link").get_text()
            else:
                job_position["company_name"] = result.find("a", class_="result-card__subtitle-link "
                                                                       "job-result-card__subtitle-link").get_text()
            job_position["link"] = result.find("a", class_="result-card__full-card-link")["href"]
            job_position["location"] = result.find("span", class_="job-result-card__location").get_text()
            job_positions.append(job_position)
        return job_positions


class Nofluffjobs(JobPortal):
    def __init__(self):
        self.url = "https://nofluffjobs.com/cz/jobs/brno/python"
        soup = JobPortal.fetch_data(self, self.url)
        self.results = soup.find_all("a", class_="posting-list-item")

    def create_dict(self):
        job_positions = []
        for result in self.results:
            job_position = {}
            job_position["portal"] = "nofluffjobs.com"
            job_position["portal_logo"] = "https://nofluffjobs.com/images/logo_NFJ_FB.jpeg"
            job_position["position_name"] = result.find("h3").get_text().strip()
            job_position["company_name"] = result.find("span", class_="posting-title__company") \
                .get_text().split("v ")[1]
            job_position["link"] = "https://nofluffjobs.com" + result["href"]
            job_position["location"] = result.find("span", class_="posting-info__location").get_text().strip()
            job_positions.append(job_position)
        return job_positions


class Jobstack(JobPortal):
    def __init__(self):
        self.url = "https://www.jobstack.it/jobposts?positiontype=79&location=Brno&isDetail=0"
        soup = JobPortal.fetch_data(self, self.url)
        self.results = soup.find_all("li", class_="jobposts-item")

    def create_dict(self):
        job_positions = []
        for result in self.results:
            job_position = {}
            job_position["portal"] = "jobstack.it"
            job_position["portal_logo"] = "https://www.mamnapad.cz/wp-content/uploads/2017/07/jobstack-1.png"
            job_position["position_name"] = result.find("h3").get_text().strip()
            job_position["company_name"] = result.find("span", class_="jobposts-item_company icontext").find(
                "span").get_text()
            job_position["link"] = "https://www.jobstack.it" + result.find("a", class_="jobpost-mainlink")["href"]
            job_position["location"] = result.find("span",
                                                   class_="jobposts-item_location icontext").find("span").get_text()
            job_positions.append(job_position)
        return job_positions


class Indeed(JobPortal):
    def __init__(self):
        self.url = "https://cz.indeed.com/jobs?q=Python&l=Brno&radius=0&sort=date"
        soup = JobPortal.fetch_data(self, self.url)
        self.results = soup.find_all("div", class_="jobsearch-SerpJobCard")

    def create_dict(self):
        job_positions = []
        for result in self.results:
            job_position = {}
            job_position["portal"] = "indeed.com"
            job_position["portal_logo"] = "https://logos.bugcrowdusercontent.com/logos/31c9/4eb4/c1f21362" \
                                          "/77aca7a0c2e1d0a71ca2a2f404b6c17d_Untitled.png"
            job_position["position_name"] = result.find("a")["title"]
            if result.find("span", class_="company") is None:
                job_position["company_name"] = "???"
            else:
                if result.find("span", class_="company").find("a") is None:
                    job_position["company_name"] = result.find("span", class_="company").get_text().strip()
                else:
                    job_position["company_name"] = result.find("span", class_="company").find("a").get_text().strip()
            job_position["link"] = "https://cz.indeed.com" + result.find("a", class_="jobtitle turnstileLink")["href"]
            if result.find("span", class_="location") is None:
                job_position["location"] = result.find("div", class_="location").get_text()
            else:
                job_position["location"] = result.find("span", class_="location").get_text()
            job_positions.append(job_position)
        return job_positions


def insert_all_db():
    Jobscz().insert_db()
    Startupjobs().insert_db()
    Juniorguru().insert_db()
    Jobsik().insert_db()
    Linkedin().insert_db()
    Nofluffjobs().insert_db()
    Jobstack().insert_db()
    Indeed().insert_db()


def post_discord():
    query = session.query(Jobs).filter(Jobs.posted == "not-posted").all()
    for q in query:
        # Format discord message
        message = {}
        message["embeds"] = [
            {
                "title": q.position_name,
                "url": q.link,
                "color": 10010050,
                "fields": [
                    {
                        "name": "Company:",
                        "value": q.company_name,
                        "inline": True
                    },
                    {
                        "name": "Location:",
                        "value": q.location,
                        "inline": True
                    }
                ],
                "thumbnail": {
                    "url": q.portal_logo
                }
            }
        ]
        # Send to discord
        requests.post(webhook, json=message)

        # In case of testing let script sleep for 2 seconds because of Discord limit (30 messages/minute)
        time.sleep(2)

        # Label position so it's not posted multiple times
        q.posted = "posted"
        session.commit()


insert_all_db()
post_discord()
