# webXray
webXray is a tool for detecting third-party HTTP requests on large numbers of web pages and matching them to the companies which receive user data.

# Why
Third-party HTTP requests are the lowest-level mechanism by which user data may be surreptitiously disclosed to unknown parties on the web. This may be for perfectly benign reasons, such as an embedded a picture from another site, or it may be a form of surveillance utilizing tracking pixels, cookies, or even sophisticated fingerprinting techniques.

# How
As a departure from existing tools, webXray facilitates the identification of the real-world entities to which requests are made by correlating domain request with the owners of domains. In other words, webXray allows you to see which companies are monitoring which pages.

The core of webXray is a python program which ingests addresses of webpages, passes them to the headless web browser PhantomJS, and parses requests in order to determine those which go to domains which are exogenous to the primary (or first-party) domain of the site. This data is then stored in MySQL for later analysis. Future revisions of webXray will implement SQLite for those wishing to investigate smaller volumes of pages without installing or managing a major database server.

# Who
webXray was originally developed for academic research, but may be used by anybody with an interest in the hidden structures of the web, privacy, and surveillance.

# Dependencies
This program needs the following to run:

	Python 3.4+ 			https://www.python.org
	PhantomJS 1.9+ 			http://phantomjs.org
	MySQL					https://www.mysql.com
	MySQL Python Connector	https://dev.mysql.com/downloads/connector/python/
	
I have had the best luck with going with the "Platform Independent" version of MySQL Python Connector.  Make sure you use Python3 to install it.

# Usage
Once you have met the above dependencies and downloaded webXray all you need to do is edit your MySQL configuration information in webxray/MySQLDriver.py.  Next, place a list of page addresses in the 'page\_lists' directory; webXray comes with an example page list which you may use on first run.  Once this is done simply run the command 'python3 run\_webxray.py -i'.  You will be given options to collect and analyze data; the first thing you must do is collect data so you may analyze it.  Data which has been analyzed will be saved to a directory titled 'reports'.  See webxray/Reports.py for more details.

# License
webXray is FOSS and licensed under GPLv3, see LICENSE.md for details.