#
#	Welcome to webXray!
#
#	This program needs the following to run:
#		Python 3.4 				https://www.python.org
#		phantomjs 1.9+ 			http://phantomjs.org
#		MySQL					https://www.mysql.com
#		MySQL Python Connector	https://dev.mysql.com/downloads/connector/python/ (go with platform independent)
#	
#	webXray will try to alert you to failed dependencies, so if you are having
#	 issues make sure above is installed
#
#	This file is may be all you are ever be exposed to.  It has an interactive mode
#		'-i' which is what most people will need for small to moderate sets of pages (eg < 10k).
#		However, if you are doing big sets you may want to use the unattended options '-c' and '-a'.
#		Run with '-h' for details.
#
#	An important option to set is pool_size which determines how many parallel processes are run,
#		 look at the collect() function for details and to adjust.
#

# before anything test we are on right version of python!
import sys
if sys.version_info[0] < 3:
	print('Python 3.4 or above is required for webXray to function; please check your installation.')
	exit()
if sys.version_info[1] < 4:
	print('Python 3.4 or above is required for webXray to function; please check your installation.')
	exit()

# standard python 3.4 libs
import os
import re
import time
from optparse import OptionParser

# set up a global mysql driver, in the future you could use other db drivers here
# if the mysql connector is not installed this fails gracefully
from webxray.MySQLDriver import MySQLDriver
sql_driver = MySQLDriver()

# databases are stored with a 'wbxr_' prefix, this function helps select a database in interactive mode
def select_wbxr_db():
	wbxr_dbs = sql_driver.get_wbxr_dbs_list()

	for index,db_name in enumerate(wbxr_dbs):
		print('\t\t[%s] %s' % (index, db_name[5:]))

	max_index = len(wbxr_dbs)-1
	
	# loop until we get acceptable input
	while True:
		selected_db_index = input("\n\tPlease select database by number: ")
		if selected_db_index.isdigit():
			selected_db_index = int(selected_db_index)
			if selected_db_index >= 0 and selected_db_index <= max_index:
				break
			else:
				print('\t\t You entered an invalid string, please select a number in the range 0-%s.' % max_index)
				continue
		else:
			print('\t\t You entered an invalid string, please select a number in the range 0-%s.' % max_index)
			continue

	selected_db_name = wbxr_dbs[selected_db_index]
	return selected_db_name
# end select_wbxr_db

def quit():
	print('------------------')
	print('Quitting, bye bye!')
	print('------------------')
	exit()
# end quit

# this is what most people should be dealing with
def interaction():
	print('\tWould you like to:')
	print('\t\t[C] Collect Data')
	print('\t\t[A] Analyze Data')
	print('\t\t[Q] Quit')

	# loop until we get acceptable input
	while True:
		selection = input("\tSelection: ").lower()
		
		if selection 	== 'c':
			break
		elif selection 	== 'a':
			break
		elif selection 	== 'q':
			quit()
		else:
			print('\t\tValid selections are C, A, and Q.  Please try again.')
			continue

	# we are collecting new data
	if selection == 'c':
		print('\t===============')
		print('\tCollecting Data')
		print('\t===============')
		print('\tWould you like to:')
		print('\t\t[C] Create a New Database')
		print('\t\t[A] Add to an Existing Database')
		print('\t\t[Q] Quit')
	
		# loop until we get acceptable input
		while True:
			selection = input("\tSelection: ").lower()
		
			if selection 	== 'c':
				break
			elif selection 	== 'a':
				break
			elif selection 	== 'q':
				quit()
			else:
				print('\t\tValid selections are C, A, and Q.  Please try again.')
				continue

		if selection == 'c':
			# collect - new db
			print('\t----------------------')
			print('\tCreating New Database')
			print('\t----------------------')
			print('\tDatabase name must be alpha numeric, and may contain a "_"; maximum length is 20 characters.')
			# loop until we get acceptable input
			while True:
				new_db_name = input('\tEnter new database name: ').lower()

				if len(new_db_name) <= 20 and re.search('^[a-zA-Z0-9_]*$', new_db_name):
					print('\tNew db name is "%s"' % new_db_name)
					break
				else:
					print('\tName was invalid, try again.')
					continue
			# go create new db here, set current_db_name to what it is
			sql_driver.create_wbxr_db(new_db_name)
			# add db prefix here
			current_db_name = 'wbxr_'+new_db_name
		elif selection == 'a':	
			# collect - add to db
			print('\t---------------------------')
			print('\tAdding to Existing Database')
			print('\t---------------------------')
			print('\tThe following webXray databases are available:')
			
			current_db_name = select_wbxr_db()
	
			# we do [5:] so we strip off the 'wbxr_' on the output
			print('\tUsing database: %s' % current_db_name[5:])
		
		# we have figured out the db situation, now move on to collection	
		print('\t--------------------')
		print('\tSelecting Page List')
		print('\t--------------------')
		print('\tPlease select from the available files in the "page_lists" directory:')

		# webXray needs a file with a list of page URIs to scan, these files should be kept in the
		#	'page_lists' directory.  this function shows all available page lists and returns
		#	the name of the selected list.
		files = os.listdir(path='./page_lists')
		if len(files) is 0:
			print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
			print('ERROR: No page lists found, check page_lists directory.')
			print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
			quit()

		# print out options
		print('\tPage Lists Available:')
		for index,file in enumerate(files):
			print('\t\t[%s] %s' % (index, file))

		# loop until we get acceptable input
		while True:
			selection = input("\n\tChoose a page list by number: ")
			if selection.isdigit():
				selection = int(selection)
				if selection >= 0 and selection <= len(files):
					break
				else:
					print('\tInvalid choice, try again.')
					continue
			else:
				print('\tInvalid choice, try again.')
				continue

		pages_file_name = files[selection]

		
		print('\tPages file is "%s"' % pages_file_name)
		
		print('\t------------------')
		print('\tBeginning webXray')
		print('\t------------------')		
		time.sleep(1)
	
		collect(current_db_name, pages_file_name)

		print('\t---------------------')
		print('\t Collection Finished!')
		print('\t---------------------')
		
		# let's us go back to analyze
		interaction()
	elif selection == 'a':	
		# analyze
		print('\t==============')
		print('\tAnalyzing Data')
		print('\t==============')

		print('\t-----------------------------------------------------------')
		print('\tThe following webXray databases are available for anlaysis:')
		print('\t-----------------------------------------------------------')
		
		current_db_name = select_wbxr_db()

		# we do [5:] so we strip off the 'wbxr_' on the output
		print('\tUsing database: %s' % current_db_name[5:])

		# going to do the report now
		report(current_db_name)
		
		# restart interaction
		interaction()
# end interaction

# both collect() and report() may either be called in interactive mode, or can be called
# via the CLI when running on large datasets

def collect(db_name, pages_file_name):
	# we use multiprocessing to speed up collection, and the pool_size can be set here
	#	('pool_size' being the number of parallel processes are run)
	#  on small sets you can leave it at '1' and it will be slow, but very stable
	#  on larger sets you should consider upping the pool_size to speed up your collection
	#  and fully leverage your resources
	#
	# the real limit on performance here is that phantomjs is a web browser, so uses lots of 
	#	cpu and mem
	#
	# roughly speaking, it is generally safe to run 4 concurrent processes for each GB of memory
	#	eg: 
	#		4gb = pool_size 16
	#		8gb = pool_size 32
	#
	# of course local performance may vary, so tuning this variable is advised if pushing
	#  over 1M pages - and if you are doing over 1M you should be tuning mysql as well!
	#
	# a sign your pool is too big is if the % of pages with 3p request goes way down - this 
	#	means network requests are being fired off or completed and you are losing data
	#
	# the best way to play with this is start low and do a run of 500 pages, then increment x2
	#	until your numbers start to go down, then ease back
	#
	pool_size = 16

	# custom classes
	from webxray.Collector import Collector
	Collector = Collector(db_name, pages_file_name)	
	Collector.run(pool_size)
# end collect

def report(db_name):
	from webxray.Reporter import Reporter
	
	# set how many tlds you want to examine and how many results
	# see Reporter.py for info on tracker_threshold - don't change until you read docs
	num_tlds	= 10
	num_results	= 100
	tracker_threshold = 0
		
	# set up a new reporter
	Reporter	= Reporter(db_name, num_tlds, num_results, tracker_threshold)

	# now get the reports
	Reporter.header()
	Reporter.get_summary_by_tld()
	Reporter.get_network_ties()
	Reporter.get_reports_by_tld('orgs')
	Reporter.get_reports_by_tld('domains')
	Reporter.get_reports_by_tld('elements')
	Reporter.get_reports_by_tld('elements', 'javascript')
	Reporter.get_reports_by_tld('elements', 'image')
	Reporter.print_runtime()
# end report

def single(uri):
	print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
	print('\tSingle Site Test On: %s' % uri)
	print('\t   (Will wait 20 seconds to load, 90 seconds for timeout.)')

	# set up the outputprinter, this avoids db except for uri processing
	from webxray.OutputPrinter import OutputPrinter
	output_printer = OutputPrinter()	
	output_printer.report(uri)
# single

if __name__ == '__main__':

	# for fun, and version info
	print('''   
              | |  \ \ / /                
 __      _____| |__ \ V / _ __ __ _ _   _ 
 \ \ /\ / / _ \ '_ \ > < | '__/ _` | | | |
  \ V  V /  __/ |_) / . \| | | (_| | |_| |
   \_/\_/ \___|_.__/_/ \_\_|  \__,_|\__, |
                                     __/ |
                                    |___/ 
                            	   [v 1.0]
    ''')

	# set up cli args
	parser = OptionParser()
	parser.add_option('-i', action='store_true', dest='interactive', help='Interactive Mode: Best for Small/Medium Size Datasets')
	parser.add_option('-a', action='store_true', dest='analyze', help='Analyze Unattended: Best for Large Datasets - Args: [db_name]')
	parser.add_option('-c', action='store_true', dest='collect', help='Collect Unattended: Best for Large Datasets - Args: [db_name] [page_file_name]')
	parser.add_option('-s', action='store_true', dest='single', help='Single Site: for One-Off Tests - Args [url to analyze]')
	(options, args) = parser.parse_args()

	mode = ''
	mode_count = 0
	
	# set mode, make sure we don't have more than one specified
	if options.interactive:
		mode = 'interactive'
		mode_count += 1

	if options.analyze:
		mode = 'analyze'
		mode_count += 1
		
	if options.collect:
		mode = 'collect'
		mode_count += 1
		
	if options.single:
		mode = 'single'
		mode_count += 1
		
	if mode_count == 0:
		print('Error: No mode specified!')
		parser.print_help()
		exit()
	elif mode_count > 1:
		print('Error: Too many modes specified!')
		parser.print_help()
		exit()

	# do what we're supposed to do		
	if mode == 'interactive':
		interaction()
	elif mode == 'analyze':
		# need to verify this is an actual db name
		try:
			db_name = args[0]
		except:
			print('Need a db name!')
			exit()
		report(db_name)
	elif mode == 'collect':
		try:
			# need to check 0 is page db name, 1 is file name
			db_name = args[0]
			page_file = args[1]
		except:
			print('Need a db name and pages file!')
			exit()
		collect(db_name, page_file)
	elif mode == 'single':
		# should check if this is actually a uri
		single(args[0])
	quit()
# main