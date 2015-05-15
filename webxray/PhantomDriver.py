#	we need to run phantomjs under the subprocess module and send back JSON
#	it was easiest to segregate this into a separate class for maintainability
#	should be noted almost all development was done with 1.9 branch of phantomjs
#	the 2.x branch appears to work, but is new and a major change so somewhat unstable
#
#	another reason to segregate this is that if other options mature (eg slimerjs)
#	those could be swapped in easily by writing a new class

import os
import subprocess

class PhantomDriver:
	def __init__(self, phantom_args, script_name):
		# first check is phantomjs version is ok
		process = subprocess.Popen('phantomjs --version', shell=True, stdout=subprocess.PIPE)
		try:
			output, errors = process.communicate()
		except Exception as e:
			process.kill()
			self.die('phantomjs not returning version number, something must be wrong, check your installation!')
		
		try:
			phantomjs_version = float(output.decode('utf-8')[:3])
		except:
			self.die('phantomjs not returning version number, something must be wrong, check your installation!')

		if phantomjs_version < 1.9:
			self.die('you are running phantomjs version %s, webXray requires at least 1.9' % phantomjs_version)
		
		# looks good, build the command_string
		self.command_string = "phantomjs "+phantom_args+" "+os.path.join(os.path.dirname(__file__))+"/resources/phantomjs_scripts/"+script_name
	# end __init__

	def die(self, msg):
		print('!'*len(msg))
		print('ERROR: %s' % msg)
		print('!'*len(msg))
		exit()

	def execute(self, script_args, seconds_to_timeout):
		command = self.command_string+" '"+script_args+"'"
		process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)

		# make sure phantomjs has time to download/process the page
		# but if we get nothing after number of seconds specified, we move on
		try:
			output, errors = process.communicate(timeout=seconds_to_timeout)
		except Exception as e:
			process.kill()
			return("FAIL: Phantomjs Timed Out After %s Seconds" % seconds_to_timeout)

		# output will be weird, decode utf-8 to save heartache
		phantom_output = ''
		for out_line in output.splitlines():
			phantom_output += out_line.decode('utf-8')
		return phantom_output
	# end execute
# end class PhantomDriver