#	this class extracts the sub domain, full domain, and tld from a uri string
#	for.example.com gets parsed to "for.example.com", "example.com", and "com"
#
#	the mozilla public suffix list is used for identifying ccTLDs, this list is incomplete
#		however, so I have patched it with additional ccTLD info, look into the dir
#		/resources/pubsuffix to find relevant files
#
#	because this uses regex it is kinda slow - to help with this a database "sub_domain_tld"
#	  	is created and contains a hash table, this speeds things up a lot
#	this database is shared among all of your webxray runs so it grows in time
#		and may necessitate pruning if performance takes a hit

import os
import re

# set up new sql_driver
from webxray.MySQLDriver import MySQLDriver

class ParseURI:
	def __init__(self):
		# load up the tld list now as only hit it once this way
		self.pubsuffix_list = self.get_pubsuffix_list()

		# this is to speed up tlds lookup with hash table
		# we can share among all runs over time
		self.sql_driver = MySQLDriver()
		
		# check if sub_domain_tld exists, if not create one
		#    this should only really happen once
		#
		# bug?
		# when using pool this can be done several times in tandem
		#   resulting in some lost entries - e.g. two threads see db not exist the first
		#   one to break the tie will create a new blank db and add a new entry
		#	it is possible the slightly slower second thread will also create a blank db
		#	erasing the entry of the first thread, however, after the first round the db 
		#	should not be re-created again
		# 
		# it should be emphasized this db is ONLY used to speed up parsing the tld 
		#	(partially because my regex method is slow and should be refactored!)
		#	the data is this db is NOT used for analysis - thus deleting a few records
		#	will have a minor impact on speed for the first few entries, and then be
		#	wholly irrelevant
		#
		#   still...it irks me that this entire class could be smarter, so I will
		#		fix it another day
		
		if self.sql_driver.check_db_exist('sub_domain_tld') == False:
			self.sql_driver.create_sub_domain_tld_db()
		else:
			self.sql_driver.db_switch('sub_domain_tld')
	# end __init__

	def get_pubsuffix_list(self):
		# get the file from the local dir
		pubsuffix_raw_list = open(os.path.join(os.path.dirname(__file__), './resources/pubsuffix/patchedPublicSuffixList-20150514.txt'), 'r')
		pubsuffix_list = []

		for line in pubsuffix_raw_list:
				# the last part of the list is random shit we don't care about, so stop reading
				if re.match("^// ===BEGIN PRIVATE DOMAINS===", line):break
				# skip lines that are comments or blank, add others to list
				# also remove leading ., !, and * as it fucks up regex later
				if not re.match("^//.+$|^$", line):
					pubsuffix_list.append(re.sub('^[\!\*]\.?', '', line.strip()))

		# we sort long->short so we can match deeper TLD first (ie, ac.uk *before* .uk)
		pubsuffix_list.sort(key=len,reverse=True)

		# to speed things up we move the most common TLD to the front of the line
		# that said, if it's not one of these we take a MASSIVE performance hit
		popular_pubsuffixs = ['gov', 'co.uk', 'mil', 'org', 'net', 'edu', 'com']
		for popular_pubsuffix in popular_pubsuffixs:
			pubsuffix_list.remove(popular_pubsuffix)
			pubsuffix_list.insert(0, popular_pubsuffix)
		return pubsuffix_list
	# get_pubsuffix_list

	def get_domain_pubsuffix_tld(self, uri):
		# pull out the first chunk of the domain, possibly including subdomains
		# if this fails, the domain is fucked up (or not https? at least), kill
		# only handles if the domain is followed by $, ?, \, or / - other shit will break...
		# adding to handle with port at end, ie blah.com:8080, so rule is '|\:[0-9].+
		# adding \.? at the top to handle leading '.'
		try:
			sub_domain = re.search('^https?:\/\/\.?(.*?)(\:[0-9].+)?($|\/|\?|\\\\|=)', uri).group(1)
		except:
			return('Exception: Unable to parse: '+uri[:50], 'Exception: Unable to parse: '+uri[:50], 'Exception: Unable to parse: '+uri[:50])

		# strip off leading or trailing '.', this is fucking things up
		sub_domain = re.sub('(^\.|\.$)', '', sub_domain)

		# see if it is an ip address, if so return it
		# this is only ipv4 pattern though, maybe should thinking about ipv6?
		try:
			re.search('(^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$)', sub_domain).group(1)
			return (sub_domain, 'None', 'None')
		except:
			pass

		# first, we will see if it is in the db already
		record = self.sql_driver.sub_domain_exists(sub_domain)

		if record:
			return record

		# the pubsuffix list is large -> small, 
		# so the first match is the one we want
		# after we find it, break out and continue
		for pubsuffix_try in self.pubsuffix_list:
			if re.match(".+\."+pubsuffix_try+"$", sub_domain):
				pubsuffix = pubsuffix_try
				break

		# if we didn't find the pubsuffix we fail
		try:
			pubsuffix
		except:
			return('Exception: Unable to parse: '+uri[:50], 'Exception: Unable to parse: '+uri[:50], 'Exception: Unable to parse: '+uri[:50])

		# if we have sub.domain.tld_match, we just want domain.tld_match
		# there is no reason this should fail if we get this far, but try/except to be safe
		try:
			domain = re.search('(.*\.)?\.?(.*\.'+pubsuffix+')$', sub_domain).group(2)
		except:
			return('Exception: Unable to parse: '+uri[:50], 'Exception: Unable to parse: '+uri[:50], 'Exception: Unable to parse: '+uri[:50])

		# grab the tld off of the pubsuffix
		# if regex fails the tld and pubsuffix are the same
		try:
			tld = re.search('\.([0-9A-Za-z]+)$', pubsuffix).group(1).lower()
		except:
			tld = pubsuffix

		self.sql_driver.add_sub_domain_pubsuffix_tld(sub_domain, domain, pubsuffix, tld)
		return (domain, pubsuffix, tld)
	#end get_domain_pubsuffix_tld
	
	def close(self):
		# close mysql connection
		self.sql_driver.close()
		return
	# end close

#end ParseURI