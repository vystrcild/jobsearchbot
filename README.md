# Job Search Bot


Simple web **scraper for few IT job portals** in the Czech Republic. Using **Discord webhook** to get notified about job offers automatically.

## Usage 
<img align="right" src="https://github.com/vystrcild/jobsearchbot/blob/main/static/jobbot.png?raw=true">

- Most of the websites inserting search filters inside url. Just create your desired filter and **change the urls** (or use XHR). 
- Create and use your [Discord webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)
- Run **jobsearchbot.py** 

I'm using SQLAlchemy to save job offers inside SQLite database just in case for further research of the companies.
