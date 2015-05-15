#	this class receives JSON data from phantomjs, processes it and stores it in the db
#	designed to fail gracefully...

# standard python libs
import re
import json
import urllib.request

# webxray classes
from webxray.ParseURI import ParseURI
from webxray.MySQLDriver import MySQLDriver

class OutputStore:
	def __init__(self, dbname):
		self.uri_parser = ParseURI()
		self.sql_driver = MySQLDriver(dbname)
	# end init

	def store(self, uri, phantom_output):
		# parse out the json from our phantom_output
		# sometimes phantom prints out errors before the json, (despite us turning
		# it off!), so we match inside of the {}s to get json only
		try:
			data = json.loads(re.search('(\{.+\})', phantom_output).group(1))
		except Exception as e:
			self.sql_driver.log_error(uri, "Could Not Load JSON: %s" % e)
			return 'Could Not Load JSON'

		# we need to parse the domain to determine if requests are local or 3rd party
		# we need pubsuffix and tld for later analysis so store them now

		origin_domain_pubsuffix_tld = self.uri_parser.get_domain_pubsuffix_tld(uri)
		origin_domain = origin_domain_pubsuffix_tld[0]
		origin_pubsuffix = origin_domain_pubsuffix_tld[1]
		origin_tld = origin_domain_pubsuffix_tld[2]
		
		if re.match('^Exception.+', origin_domain):
			self.sql_driver.log_error(uri, 'Could not parse TLD for %s' % uri)
			return 'Could not parse TLD for %s' % uri

		page_domain_id = self.sql_driver.add_domain(origin_domain, origin_pubsuffix, origin_tld)

		# newFollowLogger is giving us the follow JSON data:
		# note source is null for now, but store anyway
# 		big_out = {
# 			final_uri: final_uri,
# 			title: page.title,
# 			meta_desc : meta_desc,
# 			requested_uris: JSON.stringify(requested_uris),
# 			received_uris: JSON.stringify(received_uris),
# 			cookies: phantom.cookies,
# 			source: 'NULL',
# 		};

		# we are now storing uris with and without args and saving args
		# we must unquote to uri to get back to original state so can parse
		start_uri_original = urllib.parse.unquote(uri)

		try:
			start_uri_no_args = re.search('^(.+?)\?.+$', start_uri_original).group(1) # start uri no args
		except:
			start_uri_no_args = uri

		try:
			start_uri_args = re.search('^.+(\?.+)$', start_uri_original).group(1) # start uri args
		except:
			start_uri_args = 'NULL'
		
		# same for the final uri (this is where we are after potential redirects)
		final_uri = re.sub('\"', '', json.dumps(data["final_uri"]))
		final_uri_original = urllib.parse.unquote(final_uri)
		
		try:
			final_uri_no_args = re.search('^(.+?)\?.+$', final_uri_original).group(1) # start uri no args
		except:
			final_uri_no_args = final_uri

		try:
			final_uri_args = re.search('^.+(\?.+)$', final_uri_original).group(1) # start uri args
		except:
			final_uri_args = 'NULL'
	
		# add page
		# json.dumps to make sure strings go out ok for db
		page_id = self.sql_driver.add_page(								 
			str(re.sub('\"', '', json.dumps(data["title"]))),
			str(re.sub('\"', '', json.dumps(data["meta_desc"]))),
			uri, 
			start_uri_no_args, 
			start_uri_args,
			final_uri, 
			final_uri_no_args, 
			final_uri_args,
			str(re.sub('\"', '', json.dumps(data["source"]))),
			str(re.sub('\"', '', json.dumps(data["requested_uris"]))),
			str(re.sub('\"', '', json.dumps(data["received_uris"]))),
			page_domain_id)

		for cookie in data["cookies"]:
			# store external cookies, uri_parser fails on non-http, we should fix this
			# right now a lame hack is to prepend http://
			cookie_domain_pubsuffix_tld = self.uri_parser.get_domain_pubsuffix_tld("http://"+cookie["domain"])
			cookie_domain = cookie_domain_pubsuffix_tld[0]
			cookie_pubsuffix = cookie_domain_pubsuffix_tld[1]
			cookie_tld = cookie_domain_pubsuffix_tld[2]

			# something went wrong, but carry on...
			if re.match('^Exception.+', cookie_domain):
				self.sql_driver.log_error(uri, 'Error parsing cookie: '+cookie_domain)
				continue

			# this is a 3party cookie
			if origin_domain != cookie_domain:

				cookie_domain_id = self.sql_driver.add_domain(cookie_domain, cookie_pubsuffix, cookie_tld)
			
				# name and domain are required, so if they fail we just continue
				try: name = cookie["name"]
				except: continue
			
				try: domain = cookie_domain
				except: continue
			
				# these are optional, keep going with "N/A" vals
			
				try: secure = cookie["secure"]
				except: secure = "N/A"
			
				try: path = cookie["path"]
				except: path = "N/A"
			
				try: expires = cookie["expires"]
				except: expires = "N/A"
			
				try: httponly = cookie["httponly"]
				except: httponly = "N/A"
			
				try: expiry = cookie["expiry"]
				except: expiry = "N/A"
			
				try: value = cookie["value"]
				except: value = "N/A"
			
				cookie_id = self.sql_driver.add_cookie(	name, secure, path, domain, 
														expires, httponly, expiry, value, 
														cookie_domain_id)
				self.sql_driver.add_cookie_to_page(cookie_id, page_id)

		for request in data["requested_uris"]:
			# if the request starts with "data" we can't parse tld anyway, so skip
			if re.match('^(data|about|chrome).+', request):
				continue

			# get domain, pubsuffix, and tld from request
			requested_domain_pubsuffix_tld = self.uri_parser.get_domain_pubsuffix_tld(request)
			requested_domain = requested_domain_pubsuffix_tld[0]
			requested_pubsuffix = requested_domain_pubsuffix_tld[1]
			requested_tld = requested_domain_pubsuffix_tld[2]
			
			# see if we got back what we requested, if not a few things may have happened
			# 	* malformed uri
			#	* resource is gone or never existed
			#	* network latency (ie it didn't arrive in window specified)
			#	* we could be behind a firewall or censorship mechanism (eg gfw, golden shield)
			#	* our IP is blacklisted b/c we are totally a bot X-D
			# the point being, interpret this value with an open mind
			
			if request in data['received_uris']:
				recieved = '1'
			else:
				recieved = '0'
			
			# catch exceptions
			if re.match('^Exception.+', requested_domain):
				self.sql_driver.log_error(uri, 'Error parsing element request: '+request)
				continue

			# store new elements
			if origin_domain != requested_domain:
				full_uri = request
				try:
					element_uri = re.search('^(.+?)\?.+$', full_uri).group(1) # start uri no args
				except:
					element_uri = full_uri

				# attempt to parse off the extension
				try:
					element_extension = re.search('\.([0-9A-Za-z]+)$', element_uri).group(1).lower()
				except:
					element_extension = "NULL"
				
				# figure out what type of element it is
				if element_extension == 'png' or element_extension == 'jpg' or element_extension == 'jpgx' or element_extension == 'jpeg' or element_extension == 'gif' or element_extension == 'svg' or element_extension == 'bmp' or element_extension == 'tif' or element_extension == 'tiff' or element_extension == 'webp' or element_extension == 'srf':
					element_type = 'image'
				elif element_extension == 'js' or element_extension == 'javascript':
					element_type = 'javascript'
				elif element_extension == 'json' or element_extension == 'jsonp' or element_extension == 'xml':
					element_type = 'data_structured'
				elif element_extension == 'css':
					element_type = 'style_sheet'
				elif element_extension == 'woff' or  element_extension == 'ttf' or  element_extension == 'otf':
					element_type = 'font'
				elif element_extension == 'htm' or element_extension == 'html' or element_extension == 'shtml':
					element_type = 'page_static'
				elif element_extension == 'php' or element_extension == 'asp' or element_extension == 'jsp' or element_extension == 'aspx' or element_extension == 'ashx' or element_extension == 'pl' or element_extension == 'cgi' or element_extension == 'fcgi':
					element_type = 'page_dynamic'
				elif element_extension == 'swf' or element_extension == 'fla':
					element_type = 'Shockwave Flash'
				elif element_extension == 'NULL':
					element_type = 'NULL'
				else:
					element_type = 'unknown'

				try:
					args = re.search('^.+(\?.+)$', full_uri).group(1) # start uri args
				except:
					args = 'NULL'

				element_domain_id = self.sql_driver.add_domain(requested_domain, requested_pubsuffix, requested_tld)

				element_id = self.sql_driver.add_element("NULL", full_uri, element_uri, recieved, element_extension, element_type, args, element_domain_id)
				self.sql_driver.add_element_to_page(element_id, page_id)

		return 'Successfully Added to DB'
	# end report()
	
	def close(self):
		# close mysql connections
		self.uri_parser.close()
		self.sql_driver.close()
		return
	# end exit
# end class OutputStore
