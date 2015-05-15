# webXray
webXray is a tool for detecting third-party HTTP requests on large numbers of web pages and matching them to the companies which receive user data.  

More information may be found on the [project website](http://webxray.org).

# Why
Third-party HTTP requests are the lowest-level mechanism by which user data may be surreptitiously disclosed to unknown parties on the web. This may be for perfectly benign reasons, such as an embedded a picture from another site, or it may be a form of surveillance utilizing tracking pixels, cookies, or even sophisticated fingerprinting techniques.

# How
As a departure from existing tools, webXray facilitates the identification of the real-world entities to which requests are made by correlating domain request with the owners of domains. In other words, webXray allows you to see which companies are monitoring which pages.

The core of webXray is a python program which ingests addresses of webpages, passes them to the headless web browser PhantomJS, and parses requests in order to determine those which go to domains which are exogenous to the primary (or first-party) domain of the site. This data is then stored in MySQL for later analysis.

# Who
webXray was originally developed for academic research, but may be used by anybody with an interest in the hidden structures of the web, privacy, and surveillance.

# Dependencies
This program needs the following to run:

	Python 3.4+ 			https://www.python.org
	PhantomJS 1.9+ 			http://phantomjs.org
	MySQL					https://www.mysql.com
	MySQL Python Connector	https://dev.mysql.com/downloads/connector/python/
	
I have had the best luck with going with the "Platform Independent" version of MySQL Python Connector.  Make sure you use Python3 to install it.

# Installation

If the dependencies above are met all you need to do is clone this repo:

	git clone https://github.com/timlib/webXray.git

If you need additional help the webXray website has detailed instructions for [Ubuntu](http://webxray.org/#ubuntu) and [Mac OS X](http://webxray.org/#mac).

# First Run
To start webXray in interactive mode type:

	python3 run_webxray.py -i

The prompts will guide you to scanning the top 1,000 Alexa websites.

# Using webXray to Analyze Your Own List of Pages
The entire point of webXray is to allow you to analyze pages of your choosing.  In order to do so, first place all of the page addresses you wish to scan into a text file and place this file in the "page\_lists" directory.  Make sure your addresses start with "http", if not, webXray will not recognize them as valid addresses.  Once you have placed your page list in the proper directory you may run webXray in interactive mode and it will allow you to select your page list.  Easy-peasy.

# Viewing Reports
Use the interactive mode to guide you to generating an analysis.  When it is completed it will be output to the '/reports' directory.  This will contain a number of csv files; they are:

* db\_summary: a basic report of how many pages loaded, how many errors, basic stats
* summary\_by\_tld: gives more stats on how many domains are contacted, cookies, javascript, etc.
* domains-by-tld: the most frequently contacted domains, by tld
* elements-by-tld: most frequent elements, any type<
* elements-by-tld-image: most frequent elements, images
* elements-by-tld-javascript:	most frequent elements, javascript
* orgs-by-tld: this is the most interesting bit, shows all the top companies who own the domains which are being contacted - relies on the data in webxray/resources/org\_domains/org\_domains.json which was compiled manually and should be expanded.
* network: pairings between page domains and tracker domains, you can import this info to data viz software to do cool stuff - this is something worth heavy tweaking if it's of particular interest to you!

# Important Note on Speed
webXray can analyze many pages in parallell and has achieved speeds up to 30,000 pages per hour.  However, out-of-the-box webXray is configured to only scan four pages in parallell.  If you think your system can handle more (and chances are it can!), open the 'run\_webxray.py' file and search for the string 'pool\_size' - when you find that there are instructions on how to increase the numbers of pages you can do concurrently.  The bigger you can make pool\_size, the faster you will go.

# License
webXray is FOSS and licensed under GPLv3, see LICENSE.md for details.