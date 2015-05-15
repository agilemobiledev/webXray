# this class does the main work of sorting out the page address to process
#
# the list of pages **must** be in the ./page_lists directory or it will not work
#
# when checking page addresses it skips over binary documents (at least ones with known extensions)
# 	and makes sure we aren't duplicating pages that have already been analyzed
# 	this means it is safe to re-run on the same list as it won't duplicate entries, but it
#	*will* retry pages that may not have loaded for whatever reasons

# standard python libs
import re
import sys
import random
import urllib.request
from multiprocessing import Pool

# custom webxray classes
from webxray.PhantomDriver	import PhantomDriver
from webxray.OutputStore	import OutputStore
from webxray.MySQLDriver	import MySQLDriver

class Collector:
	def __init__(self, db_name, pages_file_name):
		self.db_name = db_name
		self.pages_file_name = pages_file_name
	# end __init__

	def process_uri(self, uri):
		sql_driver 		= MySQLDriver(self.db_name)
		output_store 	= OutputStore(self.db_name)
		phantom_driver 	= PhantomDriver('--ignore-ssl-errors=true --ssl-protocol=any', 'wbxr_logger.js')

		# this can be higher or lower depending on network load
		# generally, 90 seems to be fine, so keep with it
		try:
			phantom_output = phantom_driver.execute(uri, 90)
		except:
			print("\t\t%-50s Phantomjs Did Not Return." % uri[:50])
			sql_driver.log_error(uri, "FAIL: Phantomjs Did Not Return.")
			return	

		if re.match('^FAIL.+', phantom_output):
			print("\t\t%-50s Phantom Error\n\t%s" % (uri[:50], phantom_output))
			sql_driver.log_error(uri, phantom_output)
		else:
			print("\t\t%-50s %s" % (uri[:50], output_store.store(uri, phantom_output)))
	
		# closes our db connections
		sql_driver.close()
		output_store.close()
		return
	# process_uri

	def run(self, pool_size):
		try:
			uri_list = open('./page_lists/'+self.pages_file_name, 'r')
		except:
			print('File "%s" does not exist, file must be in ./page_lists directory.  Exiting.' % self.pages_file_name)
			exit()
		sql_driver = MySQLDriver(self.db_name)

		# sort out what uris we are processing from the list
		uris_to_process = []

		count = 0
		
		print('\t------------------------')
		print('\t Building List of Pages ')
		print('\t------------------------')
				
		for uri in uri_list:
			# skip lines that are comments
			if "#" in uri[0]: continue
		
			count += 1
		
			# drop trailing '/, clean off white space, make lower, create cli-safe uri
			# with parse.quote, but exclude :/ b/c of http://
			uri = re.sub('/$', '', urllib.parse.quote(uri.strip(), safe=":/").lower())

			# if it is a m$ office or other doc, skip
			if re.match('.+(pdf|ppt|pptx|doc|docx|txt|rtf|xls|xlsx)$', uri):
				print("\t\t%s | %-50s Not an HTML document, Skipping." % (count, uri[:50]))
				continue

			# skip if in db already
			if sql_driver.page_exists(uri):
				print("\t\t%s | %-50s Exists in DB, Skipping." % (count, uri[:50]))
				continue
	
			# only add if not in list already
			if uri not in uris_to_process:
				print("\t\t%s | %-50s Adding." % (count, uri[:50]))
				uris_to_process.append(uri)
			else:
				print("\t\t%s | %-50s Already queued, Skipping." % (count, uri[:50]))

		print('\t----------------------------------')
		print('\t%s pages will now be webXray\'d'  % len(uris_to_process))
		print('\t\t...you can go take a walk. ;-)')
		print('\t----------------------------------')

		myPool = Pool(pool_size)
		myPool.map(self.process_uri, uris_to_process)
	# end collect
# end class Collector
