# this class handles all of the mysql database work, no sql is to be found elsewhere in the
#	code base
#
# the general idea is that if somebody wants to add support for new db (eg sqlite, postgres, etc)
#	you only need to copy this class and rewrite the functions to support the new db type
#
# likewise, as little 'logic' is in this class as possible - that should be handled elsewhere

import os
import datetime

# mysql connector from: https://dev.mysql.com/downloads/connector/python/
try:
	import mysql.connector
	from mysql.connector import errorcode
except:
	print('!'*55)
	print('ERROR: mysql connector does not appear to be installed.')
	print('!'*55)
	exit()

class MySQLDriver:
	def __init__(self, db_name = ''):
		# dbname is optional, but if not exist functions relying on it will fail
		#  so if debugging, look here if you are getting weird failures!
	
		mysql_config = {
			'user': 'root',
			'password': '',
			'host': '127.0.0.1',
			'database': db_name,
			'raise_on_warnings': False,
		}
		
		# raise on warnings could also be true
		try:
			self.db_conn = mysql.connector.connect(**mysql_config)
		except mysql.connector.Error as err:
			if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
				print('Username or password may be wrong, check MySQLDriver config, exiting.')
				exit()
			elif err.errno == errorcode.ER_BAD_DB_ERROR:
				print('Database "%s" does not exist, exiting.' % db_name)
				exit()
			else:
				print('Error: %s ' % err)
				exit()

		self.db = self.db_conn.cursor()
	# end __init__

	#-----------------#
	# GENERAL PURPOSE #
	#-----------------#

	def db_switch(self, db_name):
		# switch to this db
		self.db.execute('USE %s' % db_name)
	# end db_switch

	def fetch_query(self, query):
		# returns query results
		self.db.execute(query)
		return self.db.fetchall()
	# end run_query

	def commit_query(self, query):
		# commits a query
		self.db.execute(query)
		self.db_conn.commit()
		return True
	# end add_domain

	def check_db_exist(self, db_name):
		self.db.execute("SHOW DATABASES LIKE '%s'" % db_name)
		if len(self.db.fetchall()) == 1:
			return True;
		else:
			return False;
	# end check_db_exist

	def get_wbxr_dbs_list(self):
		# grab list of all databases, only return those with wbxr_ prefix
		
		self.db.execute('show databases')
		wbxr_dbs = []

		for result in self.db.fetchall():
			if result[0][0:5] == 'wbxr_':
				wbxr_dbs.append(result[0])

		return wbxr_dbs
	# end get_wbxr_dbs_list

	def close(self):
		self.db.close()
		self.db_conn.close()
		return
	# end mysql_close

	def fatal(self, msg):
		print('FATAL ERROR: %s' % msg)
		print('EXITING.')
		exit()
	# fatal

	#-------------#
	# DB Creation #
	#-------------#

	def create_wbxr_db(self, db_name):
		new_db_name = 'wbxr_'+db_name

		# create the new db
		try:
			self.db.execute('create database %s' % new_db_name)
			self.db_conn.commit()
		except:
			print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
			print('ERROR: Could not create database.  Check if it already exists.')
			print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
			quit()

		# switch to this db
		self.db.execute('USE %s' % new_db_name)

		# create new tables
		db_init_file = open(os.path.join(os.path.dirname(__file__), './resources/db/mysql/wbxr-compact.sql'), 'r')
		for query in db_init_file:
			# skip lines that are comments
			if "-" in query[0]: continue
			# lose whitespace
			query = query.strip()
			# push to db
			self.db.execute(query)
			self.db_conn.commit()
		print('\tSuccess!')
	# end create_wbxr_db

	def create_sub_domain_tld_db(self):
		# create the new db
		try:
			self.db.execute('CREATE DATABASE IF NOT EXISTS sub_domain_tld')
			self.db_conn.commit()
		except:
			print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
			print('ERROR: Could not create uri parser database.')
			print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
			exit()

		# switch to this db
		self.db.execute('USE sub_domain_tld')
	
		# create new tables
		db_init_file = open(os.path.join(os.path.dirname(__file__), './resources/db/mysql/sub_domain_tld-compact.sql'), 'r')
		for query in db_init_file:
			# skip lines that are comments
			if "-" in query[0]: continue
			# lose whitespace
			query = query.strip()
			# push to db
			self.db.execute(query)
			self.db_conn.commit()
	# end create_wbxr_db

	#-----------------------#
	# INGESTION AND STORING #
	#-----------------------#	

	def page_exists(self, uri):
		self.db.execute("SELECT COUNT(*) FROM page WHERE start_uri_md5 = MD5(%s)", (uri,))
		if self.db.fetchone()[0]:
			return True
		else:
			return False	
	# end page_exists

	def item_exists(self, table, field, item):
		# return true given item is in the db
		self.db.execute("SELECT COUNT(*) FROM "+table+" WHERE "+field+" = %s", (item,))
		if self.db.fetchone()[0]:
			return True
		else:
			return False
	# end item_exists

	def get_id(self, table, field, value):
		# all the tables are indexed on 'id', this finds it for any table
		self.db.execute("SELECT id FROM "+table+" WHERE "+field+" = (%s)", (value, ))

		try:
			return str(self.db.fetchone()[0])
		except:
			return 'Not Found'
	# end get_id

	def add_domain(self, domain, ccsld_tld, tld):
		# add a new domain record to db, ignores dupes
		# returns id of newly added row
		self.db.execute("INSERT IGNORE INTO domain (domain_md5, domain, pubsuffix_md5, pubsuffix, tld_md5, tld) VALUES (MD5(%s), %s, MD5(%s), %s, MD5(%s), %s)", (domain, domain, ccsld_tld, ccsld_tld, tld, tld))
		self.db_conn.commit()
		self.db.execute("SELECT id FROM domain WHERE domain_md5 = MD5(%s)", (domain,))
		return self.db.fetchone()[0]
	# end add_domain

	def add_page(self, title, meta_desc, start_uri, start_uri_no_args, start_uri_args, final_uri, final_uri_no_args, final_uri_args, source, requested_uris, received_uris, domain_id):
		# page is unique on start_uri, this can be changed in future revisions to allow time-series
		# returns id of newly added row
		self.db.execute('''INSERT IGNORE INTO page (
							title, meta_desc, 
							start_uri_md5, start_uri, start_uri_no_args, start_uri_args,
							final_uri_md5, final_uri, final_uri_no_args, final_uri_args, 
							source, requested_uris, received_uris, domain_id
					 	) VALUES (
					 		%s, %s, 
					 		MD5(%s), %s, %s, %s, 
					 		MD5(%s), %s, %s, %s, 
					 		%s, %s, %s, %s)''', 
						(title, meta_desc, start_uri, start_uri, start_uri_no_args, start_uri_args, final_uri, final_uri, final_uri_no_args, final_uri_args, source, requested_uris, received_uris, domain_id))
		self.db_conn.commit()
		self.db.execute("SELECT id FROM page WHERE start_uri_md5 = MD5(%s)", (start_uri,))
		return self.db.fetchone()[0]
	# end add_page

	def add_element(self, name, full_uri, element_uri, recieved, element_extension, element_type, args, element_domain_id):
		# unique on uri
		# the element is basically any unique 3rd party request
		# not timestamped b/c page is, and we aren't currently processing element content
		# returns id of newly added row
		self.db.execute('''INSERT IGNORE INTO element (
								name, 
								full_uri_md5, full_uri,
								element_uri_md5, element_uri,
								received,
								extension, type,
								args, domain_id) 
							VALUES (
								%s, 
								MD5(%s), %s,
								MD5(%s), %s,
								%s,
								%s, %s,
								 %s, %s)''', 
							(name, full_uri, full_uri, element_uri, element_uri, recieved, element_extension, element_type, args, element_domain_id))
		self.db_conn.commit()
		self.db.execute("SELECT id FROM element WHERE full_uri_md5 = MD5(%s)", (full_uri,))
		return self.db.fetchone()[0]
	# end add_element

	def add_cookie(self, name, secure, path, domain, expires, httponly, expiry, value, domain_id):
		# collect all the cookies!
		# returns the id of the newly added cookie
		self.db.execute("INSERT INTO cookie (name, secure, path, domain, expires, httponly, expiry, value, domain_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
							(name, secure, path, domain, expires, httponly, expiry, value, domain_id))
		self.db_conn.commit()
		
		# I'm a little worried about lastrowid here in a race condition, worth thinking about more
		return self.db.lastrowid
	# end add_cookie

	# REFACTOR:
	#	do we need to str() these values?
	def add_element_to_page(self, element_id, page_id):
		# creates relationship between element and the page
		self.db.execute("INSERT IGNORE INTO page_element_junction (page_id, element_id) VALUES (%s, %s)", 
									(str(page_id), str(element_id)))
		self.db_conn.commit()
		return
	# end add_element_to_page

	def add_cookie_to_page(self, cookie_id, page_id):
		# creates relationship between cookie and the page
		self.db.execute("INSERT IGNORE INTO page_cookie_junction (page_id, cookie_id) VALUES (%s, %s)", 
								(str(page_id), str(cookie_id)))
		self.db_conn.commit()
		return
	# end add_cookie_to_page

	def log_error(self, uri, msg):
		# if a uri doesn't load/process we log it for later review
		# on a re-run of a set we duplicate errors, so check if exist first
		self.db.execute('SELECT COUNT(*) FROM error WHERE uri = %s AND msg = %s', (uri, msg))
		if not self.db.fetchone()[0]:
			self.db.execute("INSERT IGNORE INTO error (uri, msg, recorded) VALUES (%s,%s,%s)", 
										(uri, msg, datetime.datetime.now()))
			self.db_conn.commit()
		# turn this condition on to get error messages to console
# 		else:
# 			print("skipping duplicate error on %s" % uri)
		return
	# end log_error

	def add_sub_domain_pubsuffix_tld(self, sub_domain, domain, pubsuffix, tld):
		self.db.execute("INSERT IGNORE INTO sub_domain_tld (sub_domain_md5, sub_domain, domain_md5, domain, pubsuffix_md5, pubsuffix, tld_md5, tld) VALUES (MD5(%s), %s, MD5(%s), %s, MD5(%s), %s, MD5(%s), %s)", (sub_domain, sub_domain, domain, domain, pubsuffix, pubsuffix, tld, tld))
		self.db_conn.commit()
		return
	# end add_tld_record

	def sub_domain_exists(self, sub_domain):
		# return true given item is in the db
		self.db.execute("SELECT domain, pubsuffix, tld FROM sub_domain_tld WHERE sub_domain_md5 = MD5(%s)", (sub_domain,))
		try:
			return self.db.fetchone()
		except:
			return False
	# end tld_exists

	#------------------------#
	# ANALYSIS AND REPORTING #
	#------------------------#	

	# the first step for analysis is to assign companies to domains so we can track
	# corporate ownership; the next few functions update the database to do this after
	# the collection has been done
	
	def reset_domains_orgs(self):
		# to clean out the db before we add the new org/domain info
		# we first set all the domain.org_id values to default (1)
		# and then delete all the orgs except the default (1)
		self.db.execute('UPDATE domain SET org_id=1;')
		self.db.execute('DELETE FROM org WHERE id != 1;')
	# end reset_domains_orgs

	def add_org(self, id, name, notes, country):
		self.db.execute('INSERT IGNORE INTO org (id, name, notes, country) VALUES (%s,"%s","%s","%s");' % (id, name, notes, country))
		self.db_conn.commit()
	# end add_org

	def update_domain_org(self, id, domain):
		self.db.execute('UPDATE IGNORE domain SET org_id = %s WHERE domain = "%s";' % (id, domain))
		self.db_conn.commit()
	# end update_domain_org

	def get_all_tlds(self, type):
		if type == 'tld':
			query = 'SELECT domain.tld from page LEFT JOIN domain ON page.domain_id = domain.id';
		elif type == 'pubsuffix':
			query = 'SELECT domain.pubsuffix from page LEFT JOIN domain ON page.domain_id = domain.id'
		else:
			print('Invalid type used for get_all_tlds in MySQLDriver, exiting...')
			quit()
		
		self.db.execute(query)
		return self.db.fetchall()
	# end get_all_tlds
	
	def pages_ok_count(self):
		self.db.execute('SELECT COUNT(*) FROM page')
		return self.db.fetchone()[0]
	# end total_pages_count

	def pages_noload_count(self):
		self.db.execute('SELECT COUNT(*) FROM error WHERE msg LIKE "%FAIL%"')
		return self.db.fetchone()[0]
	# end pages_noload_count

	def total_errors_count(self):
		self.db.execute('SELECT COUNT(*) FROM error')
		return self.db.fetchone()[0]
	# end total_errors_count

	def total_cookie_count(self):
		self.db.execute('SELECT COUNT(*) FROM cookie')
		return self.db.fetchone()[0]
	# end total_cookie_count

	def pages_w_cookie_count(self):
		self.db.execute('SELECT COUNT(DISTINCT page_id) FROM page_cookie_junction')
		return self.db.fetchone()[0]
	# end total_cookie_count

	def total_element_count(self, received = False):
		if received:
			self.db.execute('SELECT COUNT(*) FROM element WHERE received = 1')
		else:
			self.db.execute('SELECT COUNT(*) FROM element')
		return self.db.fetchone()[0]
	# end total_element_count
	
	def pages_w_element_count(self):
		self.db.execute('SELECT COUNT(DISTINCT page_id) FROM page_element_junction')
		return self.db.fetchone()[0]
	# end pages_w_element_count
	
	def get_complex_page_count(self, tld_filter = '', type = '', tracker_domains = ''):
		# see if we have a list of tracker domain ids, if so make a filter
		# DON'T USE THIS UNLESS YOU KNOW HOW
		if tracker_domains:
			tracker_filter = '('
			for tracker_domain_name in tracker_domains:
				tracker_filter += "element_domain.domain = '%s' OR " % tracker_domain_name
			tracker_filter = tracker_filter[:-3]
			tracker_filter += ')'
		else:
			# if no filter, empty var
			tracker_filter = ''


		# if filtering on tld set up the query param
		if tld_filter:
			tld_filter = "page_domain.tld = '"+tld_filter+"'"

		# joins on domain for filters to work
		if type == 'elements':
			query = '''
				SELECT COUNT(DISTINCT page_id) FROM page_element_junction
				JOIN page ON page.id = page_element_junction.page_id
				JOIN domain page_domain ON page_domain.id = page.domain_id
				JOIN element ON element.id = page_element_junction.element_id
				JOIN domain element_domain ON element_domain.id = element.domain_id
			'''
		elif type == 'javascript':
			query = '''
				SELECT COUNT(DISTINCT page_id) FROM page_element_junction
				JOIN page ON page.id = page_element_junction.page_id
				JOIN domain page_domain ON page_domain.id = page.domain_id
				JOIN element ON element.id = page_element_junction.element_id
				JOIN domain element_domain ON element_domain.id = element.domain_id
				WHERE element.type = 'javascript'
			'''
		elif type == 'cookies':
			query = '''
				SELECT COUNT(DISTINCT page_id) FROM page_cookie_junction
				JOIN page ON page.id = page_cookie_junction.page_id
				JOIN domain page_domain ON page_domain.id = page.domain_id
				JOIN cookie ON cookie.id = page_cookie_junction.cookie_id
				JOIN domain element_domain ON element_domain.id = cookie.domain_id
			'''	
		else: #just get num pages
			query = '''
				SELECT COUNT(*) FROM page 
				JOIN domain page_domain ON page_domain.id = page.domain_id
			'''

		# this still feels ugly, should be fixed/refactored
		if type is 'elements' or type is 'cookies':
			if tld_filter and tracker_filter:
				query += ' WHERE '+tld_filter+' AND '+tracker_filter
			elif tld_filter:
				query += ' WHERE '+tld_filter
			elif tracker_filter:
				query += ' WHERE '+tracker_filter
		elif type is 'javascript':
			if tld_filter and tracker_filter:
				query += ' AND '+tld_filter+' AND '+tracker_filter
			elif tld_filter:
				query += ' AND '+tld_filter
			elif tracker_filter:
				query += ' AND '+tracker_filter
		else:
			if tld_filter:
				query += ' WHERE '+tld_filter

		self.db.execute(query)
		return self.db.fetchone()[0]
	# end get_complex_page_count

	def get_orgs(self, tld_filter = ''):

		query = '''	
			SELECT DISTINCT page.start_uri, org.name, org.country FROM page 
			LEFT JOIN page_element_junction ON page_element_junction.page_id = page.id
			LEFT JOIN element ON page_element_junction.element_id = element.id
			LEFT JOIN domain element_domain ON element_domain.id = element.domain_id
			LEFT JOIN domain page_domain ON page_domain.id = page.domain_id
			LEFT JOIN org on org.id = element_domain.org_id
			WHERE org.name != 'Default'
		'''
		
		# if filtering on tld set up the query param
		if tld_filter:
			query += "AND page_domain.tld = '"+tld_filter+"'"
	
		self.db.execute(query)
		return self.db.fetchall()
	# end get_orgs

	def get_domains(self, tld_filter=''):
		query = '''
			SELECT DISTINCT page.start_uri, element_domain.domain, org.name, org.country FROM page 
			JOIN page_element_junction ON page_element_junction.page_id = page.id
			LEFT JOIN element ON page_element_junction.element_id = element.id
			LEFT JOIN domain element_domain ON element_domain.id = element.domain_id
			LEFT JOIN domain page_domain ON page_domain.id = page.domain_id
			LEFT JOIN org on org.id = element_domain.org_id
		'''

		if tld_filter:
			query += " WHERE page_domain.tld = '"+tld_filter+"'"

		self.db.execute(query)
		return self.db.fetchall()
	# end get_domains
	
	def get_elements(self, tld_filter = '', sub_type = ''):
		# JOIN on page_element_junction rather than LEFT JOIN b/c we don't
		# care about pages w/out elements here
		query =	'''	
			SELECT DISTINCT page.start_uri, org.name, org.country, element.element_uri, element.extension, element.type, element_domain.domain FROM page 
			JOIN page_element_junction ON page_element_junction.page_id = page.id
			LEFT JOIN element ON page_element_junction.element_id = element.id
			LEFT JOIN domain element_domain ON element_domain.id = element.domain_id
			LEFT JOIN domain page_domain ON page_domain.id = page.domain_id
			LEFT JOIN org on org.id = element_domain.org_id
		'''

		# if filtering on tld set up the query param
		if tld_filter:
			tld_filter = "page_domain.tld = '"+tld_filter+"'"

		if sub_type and sub_type is not 'image' and sub_type is not 'javascript':
				self.fatal('Element type must be image or javascript, you put: "%s".' % sub_type)

		if tld_filter and sub_type:
			query += " WHERE "+tld_filter+" AND element.type = '"+sub_type+"'"
		elif tld_filter:
			query += " WHERE "+tld_filter
		elif sub_type:
			query += " WHERE element.type = '"+sub_type+"'"

		self.db.execute(query)
		return self.db.fetchall()
	# end get_domains

	def get_page_domain_element_domain_pairs(self):
		# returns all of the unique pairings between the domain of a page and that
		#	of an element
		query = '''
				SELECT DISTINCT page_domain.domain, element_domain.domain 
				FROM page
				LEFT JOIN page_element_junction ON page_element_junction.page_id = page.id
				LEFT JOIN element ON page_element_junction.element_id = element.id
				LEFT JOIN domain element_domain ON element_domain.id = element.domain_id
				LEFT JOIN domain page_domain ON page_domain.id = page.domain_id
		'''		
		self.db.execute(query)
		return self.db.fetchall()
	# end get_page_domain_element_domain_pairs
	
	def get_page_uri_element_domain_pairs(self, tld_filter):
		# pages with no elements return a single record with (page.final_uri, 'None')
		#	this is necessary to see which pages have no trackers and why we do not
		#	use a tracker filter here
		
		query = '''
			SELECT DISTINCT page.final_uri, element_domain.domain 
			FROM page
			LEFT JOIN page_element_junction ON page_element_junction.page_id = page.id
			LEFT JOIN element ON page_element_junction.element_id = element.id
			LEFT JOIN domain element_domain ON element_domain.id = element.domain_id
			LEFT JOIN domain page_domain ON page_domain.id = page.domain_id
		'''

		if tld_filter: 
			query += " WHERE page_domain.tld = '"+tld_filter+"'"
	
		# need this order by so loops are pre-sorted later
		query += ' ORDER BY page.final_uri'

		self.db.execute(query)
		return self.db.fetchall()
	# end get_page_element_domain_pairs
	
	def get_network_ties(self):
		# returns all of the unique pairings between the domain of a page and that
		#	of an element
		query = '''
				SELECT DISTINCT page_domain.domain, page_org.name, element_domain.domain, element_org.name
				FROM page
				LEFT JOIN page_element_junction ON page_element_junction.page_id = page.id
				LEFT JOIN element ON page_element_junction.element_id = element.id
				LEFT JOIN domain element_domain ON element_domain.id = element.domain_id
				LEFT JOIN domain page_domain ON page_domain.id = page.domain_id
				LEFT JOIN org element_org ON element_domain.org_id = element_org.id
				LEFT JOIN org page_org ON page_domain.org_id = page_org.id
		'''
		
		# to limit analysis to domains who we know the owner add following to above query		
		# WHERE element_org.id != 1
		
		self.db.execute(query)
		results = self.db.fetchall()
		return_list = []
		
		# should consider moving this to the Reporter class and keep this simple db calls
		for result in results:
			# add in a link from the page to itself if we don't have yet
			# probably a way more efficient way to do this, but want to catch the bus
			if (result[0], result[1], result[0], result[1]) not in return_list:
				return_list.append((result[0], result[1], result[0], result[1]))

			# only return those that don't have 'None' values
			if result[2]:
				return_list.append(result)

		# sort up here to be nice
		return sorted(return_list)
	# end get_network_ties
# end class MySQLDriver
