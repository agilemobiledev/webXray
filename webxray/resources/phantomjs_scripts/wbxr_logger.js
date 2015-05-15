/*
*	originally based on netlog.js example from phantomjs docs
*
*	major modification is that when a page has a chain of redirects phantomjs doesn't
*	follow all of them to completion so we wait for a set period of time (20sec) to
*	allow redirects to complete
*
*	note that this was significantly refactored after phantomjs 2 was released
*	so the code is not identical to the 1.9 version which was used to generate
*	earlier data sets and findings, further be on the lookout for bugs in
*	phantomjs 2!
*
*	example of a page with several redirects:
*	https://timlibert.me/redirects/1.html
*/

//enable, then empty cookie jar
phantom.cookiesEnabled = true;
phantom.clearCookies()

// set up vars
var page = require('webpage').create(),
    system = require('system'),
    address,
    requested_uris = [],
    received_uris = [],
    final_uri;

// go try to load the page
if (system.args.length === 1) {
    console.log('Usage: wbxr_logger.js <some URL>');
    phantom.exit(1);
} else {
    address = system.args[1];

	var final_uri = address;

	// pretend to be a different browser, helps with some shitty browser-detection redirects
	// may want to add future addition to spoof random UA strings
	page.settings.userAgent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/600.6.3 (KHTML, like Gecko) Version/8.0.6 Safari/600.6.3';

    // suppress errors from output
	page.onError = function (msg, trace) {}

	// keep track of what uri we are on so we can find redirects later
	page.onUrlChanged = function(targetUrl) {
	  final_uri = targetUrl;
	};

	// get all requests made
    page.onResourceRequested = function (request) {
    	// javascript returns -1 if item is not in array
    	if(requested_uris.indexOf(request.url) === -1){
	        requested_uris.push(request.url);
        }
    };

	// only get requests which successfully returned (OK)
    page.onResourceReceived = function (received) {
    	if(received.statusText == "OK" && received_uris.indexOf(received.url) === -1){
			received_uris.push(received.url);
		}
    };

	// python does a regex match on string 'FAIL' so this is non-arbitrary
	// and removing it will screw things up
    page.open(address, function (status) {
        if (status !== 'success') {
            console.log('FAIL to load the address '+address);

            // if there is no phantom.exit() the program will never return!
            phantom.exit();
        }
    });
}

// this timeout waits for 20 seconds, when done evaluates page data and prints JSON
// to console

setTimeout(function() {
	// get the page description, retreat to null
	meta_desc = page.evaluate(function() {
		var metas = document.getElementsByTagName('meta'), i, meta_desc = '';
		for (i = 0; i < metas.length; i++) {
			if(metas[i].name.match(/description/i)){
				meta_desc = metas[i].content;
			}
		}
		return meta_desc;
	});
	
	if(!meta_desc){
		meta_desc = 'NULL';
	}
	
	// get title, retreat to null
	title = page.title;
	if(!title){
		title = 'NULL';
	}

	// build the JSON format python will expect
	// note that you can return the source if you like, the db schema supports
	big_out = {
		final_uri: final_uri,
		title: title,
		meta_desc : meta_desc,
		requested_uris: requested_uris,
		received_uris: received_uris,
		cookies: phantom.cookies,
		// return source w/out line breaks
		// source: page.content.replace(/[\t\n\r]/g, ""),
		source: 'NULL',
	};

	// prints JSON to CLI, python reads this and processes
	console.log(JSON.stringify(big_out, undefined, 4));
	
	// if there is no phantom.exit() the program will never return!
	phantom.exit();
}, 20000);