#	when you want to just print a single page to the CLI this is what we use
#	pretty simple, only hits the db to do the domain parsing

# standard python libs
import re
import json

# custom webxray classes
from webxray.ParseURI import ParseURI
from webxray.PhantomDriver import PhantomDriver

class OutputPrinter:
	def __init__(self):
		self.uri_parser = ParseURI()
	# end init

	def report(self, uri):
		phantom_driver = PhantomDriver('--ignore-ssl-errors=true --ssl-protocol=any', 'wbxr_logger.js')
		phantom_output = phantom_driver.execute(uri, 90)
		
		if re.match('^FAIL.+', phantom_output):
			print("\tERROR URI: "+uri+"\n\t\tExiting on: "+phantom_output)
			exit()
	
		origin_domain_pubsuffix_tld = self.uri_parser.get_domain_pubsuffix_tld(uri)
		origin_domain = origin_domain_pubsuffix_tld[0]
		origin_pubsuffix = origin_domain_pubsuffix_tld[1]
		origin_tld = origin_domain_pubsuffix_tld[2]

		# parse out the json from our phantom_output
		try:
			data = json.loads(re.search('(\{.+\})', phantom_output).group(1))
		except Exception as e:
			print("\t\tException: %s" % e)
			print("\t\tphantom_output was unreadable")
			print(phantom_output[:100])
			return ''

		print("\n\t------------------{ URI }------------------")
		print("\t"+uri)
		print("\n\t------------------{ Final URI }------------------")
		print("\t"+data["final_uri"])
		print("\n\t------------------{ Domain }------------------")
		print("\t"+origin_domain)
		print("\n\t------------------{ Title }------------------")
		print("\t"+data["title"])
		print("\n\t------------------{ Description }------------------")
		print("\t"+data["meta_desc"])

		print("\n\t------------------{ 3rd Party Cookies }------------------")
		cookie_list = []
		for cookie in data["cookies"]:
			# get domain, pubsuffix, and tld from cookie
			# we have to append http b/c the parser will fail, this is a lame hack, should fix
			cookie_domain_pubsuffix_tld = self.uri_parser.get_domain_pubsuffix_tld("http://"+cookie["domain"])
			cookie_domain = cookie_domain_pubsuffix_tld[0]
			cookie_pubsuffix = cookie_domain_pubsuffix_tld[1]
			cookie_tld = cookie_domain_pubsuffix_tld[2]
			
			# print external cookies
			if origin_domain not in cookie_domain:
				cookie_list.append(re.sub("^\.", "", cookie["domain"])+" -> "+cookie["name"])#+" = "+cookie["value"])

		cookie_list.sort()
		for cookie in cookie_list:
			print("\t"+cookie)

		print("\n\t------------------{ External Requests }------------------")
		requested_domains = []
		for request in data["requested_uris"]:
			# if the request starts with "data" we can't parse tld anyway, so skip
			if re.match('^(data|about|chrome).+', request):
				continue

			# get domain, pubsuffix, and tld from request
			requested_domain_pubsuffix_tld = self.uri_parser.get_domain_pubsuffix_tld(request)
			requested_domain = requested_domain_pubsuffix_tld[0]
			requested_pubsuffix = requested_domain_pubsuffix_tld[1]
			requested_tld = requested_domain_pubsuffix_tld[2]
				
			if origin_domain not in requested_domain:
				if requested_domain not in requested_domains:
					requested_domains.append(requested_domain)
		
		requested_domains.sort()

		for domain in requested_domains:
			print("\t"+domain)
	# end report()
# end class OutputPrinter
