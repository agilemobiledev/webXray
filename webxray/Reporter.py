#	webXray stores data in a relational db, but that isn't human-readable
#	so what this class does is analyze the data and exports it to csv files that can be
#	opened in other programs
#
#	most of the reports are also run on the top tlds (default 10), so you will be able to
#	see if your global trends ("*"), your .org, and your .com are different (they usually are!)
#
#	all the reports are stored in the /reports directory, they are
#		db_summary:					a basic report of how many pages loaded, how many 
#										errors, basic stats
#		summary_by_tld:				gives more stats on how many domains are contacted,
#										 cookies, javascript, etc.
#		domains-by-tld:				the most frequently contacted domains, by tld
#		elements-by-tld:			most frequent elements, any type
#		elements-by-tld-image:		most frequent elements, images
#		elements-by-tld-javascript:	most frequent elements, javascript
#		orgs-by-tld: 				this is the most interesting bit, shows all the top
#										companies who own the domains which are being contacted
#										- relies on the data in webxray/resources/org_domains/org_domains.json
#										which was compiled manually and should be expanded
#		network:					pairings between page domains and tracker domains, you
#										can import this info to data viz software to do
#										cool stuff - this is something worth heavy tweaking
#										if it's of particular interest to you!
#
#	most of the function documentation is inline below, so look there if you are interested
#

# standard python libraries
import os
import json
import operator
import statistics
import collections
from datetime import datetime

# custom class for managing mysql
from webxray.MySQLDriver import MySQLDriver

class Reporter:
	def __init__(self, db_name, num_tlds, num_results, tracker_threshold = 0):
		self.db_name 			= db_name
		self.sql_driver 		= MySQLDriver(self.db_name)
		self.num_tlds 			= num_tlds
		self.num_results 		= num_results
		self.tracker_threshold	= tracker_threshold
		self.startTime			= datetime.now()
		self.pages_ok_count		= self.sql_driver.pages_ok_count()
		
		print('\t=============================')
		print('\t Checking Output Directories ')
		print('\t=============================')				
		
		self.setup_report_dir()
		
		print('\t===========================')
		print('\t Patching DB with Org Data ')
		print('\t===========================')		
		# update the domains to their owners	
		self.patch_org_data()
		print('\t\tSuccess!')
		
		print('\t=====================')
		print('\t Getting top %s tlds' % self.num_tlds)
		print('\t=====================')
		print('\t\tProcessing...')
		self.top_tlds = self.get_top_tlds(self.num_tlds)
		print(self.top_tlds)
		print('\t\tSuccess!')
		print('\t\tThe top tlds are:')
		for (tld, pages) in self.top_tlds:
			print('\t\t |- %s (%s)' % (tld,pages))

		# SPECIAL SAUCE, FOR EXPERTS: tracker domains!
		#
		# idea for this is you set a threshold of the number of sites a given domain
		#	is connected to - domains connecting to many sites may correlate those visits
		#	via referer strings etc, so we call these 'tracker domains'
		#
		# on a really large set of sites (e.g. 1M+) this works well but on small samples
		#  (e.g. 500) it doesn't work well at all as known tracker domains may only
		#  appear on a single site
		# 
		# this is off by default and unless you understand what you are doing...
		# 	DON'T USE THIS!
		#
		# longer-term we may want to train off a bigger corpus to find tracker domains and
		#	have them prepackaged
		#
		if tracker_threshold:
			print('\t=========================')
			print('\t Getting tracker domains ')
			print('\t=========================')
			print('\t\tProcessing...')
			self.tracker_domains = self.get_tracker_domains(self.tracker_threshold)
			print('\t\tSuccess!')
		else:
			self.tracker_domains = []

	# end __init__

	#########################
	#	HELPERS, GENERAL	#
	#########################

	def setup_report_dir(self):
		# create directory for where the reports go if not exist
		if os.path.exists('./reports') == False:
			print('\tMaking reporting directory.')
			os.makedirs('./reports')
		
		# set global report_path, trim off the wbxr_ prefix
		self.report_path = './reports/'+self.db_name[5:]
	
		# set up subdir for this database analysis
		if os.path.exists(self.report_path) == False:
			print('\tMaking subdirectory for reports.')
			os.makedirs(self.report_path)

		# just a notice
		print('\t\tWriting output to %s' % self.report_path)
	# setup_report_dir

	# reuse this a lot
	def write_csv(self, file_name, csv_rows):
		full_file_path = self.report_path+'/'+file_name 
		file_out = open(full_file_path, 'w')
		for row in csv_rows:
			file_out.write(row)
		file_out.close()
		print('\t\t'+'*'*40)
		print('\t\tOutput written to %s' % full_file_path)
	# write_csv

	# just fyi
	def print_runtime(self):
		print('~='*40)
		print("Finished!")
		print("Time to process: "+str(datetime.now()-self.startTime)+"\n")
		print('-'*80)
	# end print_runtime

	# X-(
	def fatal(self, msg):
		print('FATAL ERROR: %s' % msg)
		print('EXITING.')
		exit()
	# fatal

	#############################
	#	HELPERS, DATABASE/INIT	#
	#############################

	def patch_org_data(self):
		# in order to analyze what entities receive user data, we need to update
		#   the database with domain ownership records we have store previously
		#
		# we first clear out what is in there in case the new data has changed
		#    perhaps make this optional, on big dbs takes a while
		#
		print('\t\tFlushing extant org data...')
		self.sql_driver.reset_domains_orgs()

		# next we pull the org/domain pairings from the json file in the resources dir
		# and add to the db
		print('\t\tPatching with new org data...')
		raw_data = open(os.path.join(os.path.dirname(__file__), './resources/org_domains/org_domains.json'), 'r')
		json_data = json.load(raw_data)
	
		# the default id for orgs is 1, so we advance from there
		id = 1
		for item in json_data:
			id += 1
			self.sql_driver.add_org(id, item['organization'], item['notes'], item['country'])
			for domain in item['domains']:
				self.sql_driver.update_domain_org(id, domain)
	# end patch_org_data

	def get_top_tlds(self, limit, type = 'tld'):
		# finds the most common tlds from all the pages
		# type is default to tld, but pubsuffix also works
		# have to do some weird sorting b/c python is arbitrary and fucks up diff tests
		# returns array

		tlds = []

		for row in self.sql_driver.get_all_tlds(type):
			tlds.append(row[0])

		top_tlds = collections.Counter(tlds).most_common()
	
		# sort alphabetical
		top_tlds.sort()
	
		# sub-sort on num occurances
		top_tlds.sort(reverse=True, key=lambda item:item[1])

		# cut the array
		top_tlds = top_tlds[0:limit]

		# push in wild cards
		top_tlds.insert(0, ('*',self.pages_ok_count))
		
		return top_tlds
	# end get_top_tlds

	def get_tracker_domains(self, threshold = 0):
		# first finds all pairings of page domains and element domains
		#	note this is then unique on SITE, not on PAGE
		# returns the list of domains which appear on at least the threshold number
	
		domains = []
		for page_domain_element_domain in self.sql_driver.get_page_domain_element_domain_pairs():
			domains.append(page_domain_element_domain[1])

		# count up all the pairs, convert to items() so can process as tuples
		domain_counts = collections.Counter(domains).items()

		# put the return values here
		tracker_domains = []

		# check against threshold
		for domain_count in domain_counts:
			if domain_count[1] >= threshold:
				tracker_domains.append(domain_count[0])

		return tracker_domains
	# get_tracker_domains

	#########################
	# 	REPORTS, GENERAL	#
	#########################

	def header(self):
		# just outputs really basic data about how many records in db, etc.
		#
		print('\t=================')
		print('\t General Summary')
		print('\t=================')
	
		output_for_csv = []

		#write csv header
		output_for_csv.append('"Item","Value"\n')

		total_pages = self.sql_driver.pages_ok_count()

		print("\t\tTotal Pages OK:\t\t\t%s" % total_pages)
	
		output_for_csv.append('"Total Pages OK","%s"\n' % total_pages)
	
		total_pages_noload = self.sql_driver.pages_noload_count()
		total_pages_attempted = total_pages + total_pages_noload
	
		print("\t\tTotal Pages FAIL:\t\t%s" % total_pages_noload)
		output_for_csv.append('"Total Pages FAIL","%s"\n' % total_pages_noload)
	
		print("\t\tTotal Pages Attempted:\t\t%s" % total_pages_attempted)
		output_for_csv.append('"Total Pages Attempted","%s"\n' % total_pages_attempted)
	
		percent_pages_OK = int((total_pages/total_pages_attempted)*100)
	
		print("\t\t%% Pages OK:\t\t\t%s%%" % percent_pages_OK)
		output_for_csv.append('"%% Pages OK","%s"\n' % percent_pages_OK)
	
		total_errors = self.sql_driver.total_errors_count()
		print("\t\tTotal Errors:\t\t\t%s" % total_errors)
		output_for_csv.append('"Total Errors","%s"\n' % total_errors)
	
		total_cookies = self.sql_driver.total_cookie_count()
		print("\t\tTotal Cookies:\t\t\t%s" % total_cookies)
		output_for_csv.append('"Total Cookies","%s"\n' % total_cookies)
	
		total_pages_with_cookies = self.sql_driver.pages_w_cookie_count()
		print("\t\tPages with Cookies:\t\t%s" % total_pages_with_cookies)
		output_for_csv.append('"Pages with Cookies","%s"\n' % total_pages_with_cookies)

		percent_with_cookies = (total_pages_with_cookies/total_pages)*100
		print("\t\t%% Pages with Cookies:\t\t%s%%" % int(percent_with_cookies))
		output_for_csv.append('"%% Pages with Cookies","%s"\n' % int(percent_with_cookies))
	
		total_elements = self.sql_driver.total_element_count()
		print("\t\tTotal Elements Requested:\t%s" % total_elements)
		output_for_csv.append('"Total Elements Requested","%s"\n' % total_elements)

		total_elements_received = self.sql_driver.total_element_count(received = True)
		print("\t\tTotal Elements Received:\t%s" % total_elements_received)
		output_for_csv.append('"Total Elements Received","%s"\n' % total_elements_received)

		percent_element_received = int((total_elements_received/total_elements)*100)
		print('\t\t%% Elements Received:\t\t%s%%' % percent_element_received)
		output_for_csv.append('"%% Elements Received", "%s"\n' % percent_element_received)

		total_pages_with_elements = self.sql_driver.pages_w_element_count()
		print("\t\tPages with Elements:\t\t%s" % total_pages_with_elements)
		output_for_csv.append('"Pages with Elements","%s"\n' % total_pages_with_elements)

		percent_with_elements = (total_pages_with_elements/total_pages)*100
		print("\t\t%% Pages with Elements:\t\t%s%%" % int(percent_with_elements))
		output_for_csv.append('"%% Pages With Elements","%s"\n' % int(percent_with_elements))
		
		self.write_csv('db_summary.csv', output_for_csv)
		print('\t'+'-'*80+'\n')
	# header

	def get_network_ties(self):
		print('\t=============================')
		print('\t Processing Network Ties ')
		print('\t=============================')
		output_for_csv = []
		
		# can also include the page_org in the report, but commented out for now
		# at a later date this could be an option
		
# 		output_for_csv.append('"page_domain","page_org","3p_domain","3p_org"\n')
		output_for_csv.append('"page_domain","3p_domain","3p_org"\n')
		for edge in self.sql_driver.get_network_ties():
# 			output_for_csv.append('"%s","%s","%s","%s"\n' % (edge[0],edge[1],edge[2],edge[3]))
			output_for_csv.append('"%s","%s","%s",\n' % (edge[0],edge[2],edge[3]))
		self.write_csv('network.csv', output_for_csv)
		print('\t'+'-'*80+'\n')
	# get_network_ties		
	
	def get_summary_by_tld(self):
		print('\t=============================')
		print('\t Processing Summaries by TLD ')
		print('\t=============================')
		output_for_csv = []
		output_for_csv.append('"TLD","N","% TOTAL","N W/3PE","% W/3PE","N W/COOKIE","% W/COOKIE","N W/JS","% W/JS","3P DOMAIN MEAN","3P DOMAIN MEDIAN","3P DOMAIN MODE" \n')

		# now do per-tld numbers
		for tld in self.top_tlds:
			print('\t\tGetting summary for %s' % tld[0])

			if tld[0] != '*':
				tld_filter = tld[0]
			else:
				tld_filter = ''

			total_pages 			= self.sql_driver.get_complex_page_count(tld_filter)
			total_pages_percent 	= (total_pages/self.pages_ok_count)*100
			total_pages_elements 	= self.sql_driver.get_complex_page_count(tld_filter, 'elements', self.tracker_domains)
			percent_with_elements 	= (total_pages_elements/total_pages)*100
			total_pages_cookies 	= self.sql_driver.get_complex_page_count(tld_filter, 'cookies', self.tracker_domains)
			percent_with_cookies 	= (total_pages_cookies/total_pages)*100
			total_pages_js 			= self.sql_driver.get_complex_page_count(tld_filter, 'javascript', self.tracker_domains)
			percent_with_js 		= (total_pages_js/total_pages)*100
			
			stats 	= self.get_page_3p_stats(tld[0])
			mean 	= stats[0]
			median 	= stats[1]
			mode 	= stats[2]

			output_for_csv.append('"%s","%s","%.2f","%s","%.2f","%s","%.2f","%s","%.2f","%.2f","%s","%s"\n' % (
				tld[0], 
				total_pages, 
				total_pages_percent, 
				total_pages_elements, 
				percent_with_elements, 
				total_pages_cookies, 
				percent_with_cookies, 
				total_pages_js, 
				percent_with_js,
				mean,
				median,
				mode))		
	
		self.write_csv('summary_by_tld.csv', output_for_csv)
	# end get_summary_by_tld
	
	#####################
	#	REPORTS, MAIN	#
	#####################

	def get_reports_by_tld(self, type='', sub_type=''):
		print('\t=============================')
		print('\tProcessing Top %s %s %s' % (self.num_results, type, sub_type))
		print('\t=============================')
	
		# keep output here
		csv_output = []

		# write out the header row for the csv
		if type is 'elements':
			csv_output.append('"TLD","TLD Rank","Intra-TLD Rank","Organization","Country", "Element","Extension","Type","Domain","Total Pages","Raw Count","Percent Total"\n')
		elif type is 'domains':
			csv_output.append('"TLD","TLD Rank","Intra-TLD Rank","Domain","Organization","Country","Number of Pages","Raw Count","Percent Total"\n')
		elif type is 'orgs':
			csv_output.append('"TLD","TLD Rank","Intra-TLD Rank","Organization","Country","Number of Pages","Raw Count","Percent Total"\n')
		else:
			self.fatal('Wrong type specified in get_reports_by_tld, must be "elements", "domains", or "orgs".')

		tld_count = 0
	
		for tld in self.top_tlds:
			current_tld = tld[0]
			total_pages = tld[1]

			print('\t\tcurrently on: '+current_tld)
		
			# filter on current page tld
			if tld[0] != '*':
				tld_filter = tld[0]
				tld_count += 1
			else:
				tld_filter = ''

			# get results with specified filter
			results_rows = self.get_results_rows(total_pages, type, sub_type, tld_filter)

			current_row = 0
			# loop results
			for result_row in results_rows:
				current_row += 1
				if type is 'elements':
					csv_row = '"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%.2f"\n' % (
						current_tld,
						tld_count,
						current_row, 
						result_row[0][0], 	# org_name
						result_row[0][1], 	# country
						result_row[0][2], 	# element
						result_row[0][3], 	# extension
						result_row[0][4], 	# type
						result_row[0][5], 	# domain
						total_pages,
						result_row[1], 		# raw_count
						(result_row[1]/total_pages)*100)
				elif type is 'domains':
					total_item = result_row[1]
					csv_row = '"%s","%s","%s","%s","%s","%s","%s","%s","%.2f"\n' % (
						current_tld,
						tld_count,
						current_row, 
						result_row[0][0], 	# domain_name
						result_row[0][1], 	# org_name
						result_row[0][2], 	# org_country
						total_pages, 
						total_item, 
						(total_item/total_pages)*100)
				elif type is 'orgs':
					total_item = result_row[1]
					csv_row = '"%s","%s","%s","%s","%s","%s","%s","%.2f"\n' % (
						current_tld,
						tld_count,
						current_row, 
						result_row[0][0], 		# org_name
						result_row[0][1], 		# org_country
						total_pages,
						total_item, 
						(total_item/total_pages)*100)
				csv_output.append(csv_row)
				if current_row >= self.num_results: break

		# write out csv
		file_name = type + '-by-tld'
	
		# this really only applied to elements at present
		if sub_type:
			file_name += '-' + sub_type
		
		file_name += '.csv'	

		# store the report
		self.write_csv(file_name, csv_output)
	# end get_reports_by_tld	

	def get_results_rows(self, total_pages, type, sub_type = '', tld_filter=''):
		# this queries the db to get all elements, domains, or orgs
		# next they are counted to find the most common
		# and formatted to csv rows and returned
		
		# query the db
		if type is 'elements':
			# rows are (page.start_uri, org.name, element.element_uri, element.extension, element.type, element_domain.domain)
			query_results = self.sql_driver.get_elements(tld_filter, sub_type)
		elif type is 'domains':
			# rows are (page.start_uri, element_domain.domain, org.name)
			query_results = self.sql_driver.get_domains(tld_filter)
		elif type is 'orgs':
			# row are page.start_uri, org.name
			query_results = self.sql_driver.get_orgs(tld_filter)
		else:
			self.fatal('Type must be elements, domains, or orgs.')

		# count up the unique elements, domains, or orgs we are looking for
		results_counter = collections.Counter()
		for row in query_results:
			# remove first element in tuple as it is the page uri, now irrelevant
			# add rest to results counter as this is what we care about now
			results_counter[row[1:]] += 1


		# python's most_common() arbitrarily re-orders items with same value, making
		#	debugging a nightmare, so we have to double sort here
	
		# convert to list we can sort
		results_counter = results_counter.most_common()

		# sort alphabetical
		results_counter.sort()

		# sub-sort on num occurrences
		results_counter.sort(reverse=True, key=lambda item:item[1])

		return results_counter
	# end get_results_rows
	
	def get_page_3p_stats(self, tld = ''):
		# This function calls get_page_element_domain_pairs to get a list of tuples
		#	st. each tuple is a unique (page address, domain of an element) paring
		# This list of tuples is then iterated so that we count how many domains
		#	each page is linked to
		# IMPORTANT: get_page_element_domain_pairs is *already* sorted by page, otherwise
		#	 loop below would not work
		
		if tld == '*':
			tld = ''
		
		# init vars
		this_page_element_count = 0
		all_page_element_counts = []
		last_page = ''

		# run query, process rows
		for row in self.sql_driver.get_page_uri_element_domain_pairs(tld):
			# page has no tackers, count is zero
			if not row[1]:
				all_page_element_counts.append(0)
			# page has trackers, add count
			else:
				# this is the same page, increment count
				if row[0] == last_page:
					if self.tracker_domains:
						if row[1] in self.tracker_domains:
							this_page_element_count += 1
					else:
						this_page_element_count += 1
				# this is a new page, store our running count, reset to 1
				# update last_page
				else:
					if last_page != '': all_page_element_counts.append(this_page_element_count)
					last_page = row[0]
					if self.tracker_domains:
						if row[1] in self.tracker_domains:
							this_page_element_count = 1
						else:
							this_page_element_count = 0
					else:
						this_page_element_count = 1

		# if we have an outstanding value, give it an increment
		if this_page_element_count != 0:
			# enter the last value into the list
			all_page_element_counts.append(this_page_element_count)

		# mean and median should always be ok
		mean 	= statistics.mean(all_page_element_counts)
		median 	= statistics.median(all_page_element_counts)

		# but mode can throw an error, so catch here
		try:
			mode = statistics.mode(all_page_element_counts)
		except:
			mode = 'NULL'	

		return(mean, median, mode)
	# get_page_3p_stats
# end class Reporter