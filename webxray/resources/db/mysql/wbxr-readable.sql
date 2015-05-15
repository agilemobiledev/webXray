-- kill old tables
-- if innodb must be done in reverse order b/c fucks up on FOREIGN keys
DROP TABLE IF EXISTS error;
DROP TABLE IF EXISTS page_cookie_junction;
DROP TABLE IF EXISTS page_element_junction;
DROP TABLE IF EXISTS cookie;
DROP TABLE IF EXISTS element;
DROP TABLE IF EXISTS page;
DROP TABLE IF EXISTS domain;
DROP TABLE IF EXISTS org;

-- create tables, seed with default org data
CREATE TABLE IF NOT EXISTS org(
	id INTEGER NOT NULL AUTO_INCREMENT,
  	name MEDIUMTEXT,
  	notes MEDIUMTEXT,
  	country MEDIUMTEXT,
	PRIMARY KEY(id)
);

-- 1 --> default
INSERT INTO org (id, name, notes, country) VALUES (1, 'Default', 'Default', 'Default');


CREATE TABLE IF NOT EXISTS domain(
	id INTEGER NOT NULL AUTO_INCREMENT,
	domain_md5 VARCHAR(32) UNIQUE,
	domain MEDIUMTEXT,
	pubsuffix_md5 VARCHAR(32),
	pubsuffix VARCHAR(255),
	tld_md5 VARCHAR(32),
	tld VARCHAR(255),
	org_id INTEGER DEFAULT '1',
	FOREIGN KEY (org_id) REFERENCES org(id),
	PRIMARY KEY(id)
);

CREATE TABLE IF NOT EXISTS page(
	id INTEGER NOT NULL AUTO_INCREMENT,
	time_series_num INTEGER,
	title MEDIUMTEXT,
	meta_desc MEDIUMTEXT,
	start_uri_md5 VARCHAR(32) UNIQUE,
	start_uri MEDIUMTEXT,
	start_uri_no_args MEDIUMTEXT,
	start_uri_args MEDIUMTEXT,
	final_uri_md5 VARCHAR(32),
	final_uri MEDIUMTEXT,
	final_uri_no_args MEDIUMTEXT,
	final_uri_args MEDIUMTEXT,
	source LONGTEXT,
	requested_uris MEDIUMTEXT,
	received_uris MEDIUMTEXT,
	domain_id INTEGER,
	accessed timestamp,
	FOREIGN KEY (domain_id) REFERENCES domain(id),
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS element(
	id INTEGER NOT NULL AUTO_INCREMENT,
	name MEDIUMTEXT,
	full_uri_md5 VARCHAR(32) UNIQUE,
	full_uri MEDIUMTEXT,
	element_uri_md5 VARCHAR(32),
	element_uri MEDIUMTEXT,
	extension VARCHAR(32),
	type VARCHAR(32),
	args MEDIUMTEXT,
	domain_id INTEGER,
	FOREIGN KEY (domain_id) REFERENCES domain(id),
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS cookie(
	id INTEGER NOT NULL AUTO_INCREMENT,
	name MEDIUMTEXT,
  	secure MEDIUMTEXT,
  	path MEDIUMTEXT,
  	domain MEDIUMTEXT,
	expires MEDIUMTEXT,
	httponly MEDIUMTEXT,
	expiry MEDIUMTEXT,
	value MEDIUMTEXT,
	captured timestamp,
	domain_id INTEGER,
	FOREIGN KEY (domain_id) REFERENCES domain(id),
	PRIMARY KEY (id)
 );

CREATE TABLE IF NOT EXISTS page_element_junction(
	page_id INTEGER,
	element_id INTEGER,
	FOREIGN KEY (page_id) REFERENCES page(id),
	FOREIGN KEY (element_id) REFERENCES element(id),
	UNIQUE KEY (page_id, element_id)
);

CREATE TABLE IF NOT EXISTS page_cookie_junction(
	page_id INTEGER,
	cookie_id INTEGER,
	FOREIGN KEY (page_id) REFERENCES page(id),
	FOREIGN KEY (cookie_id) REFERENCES cookie(id),
	UNIQUE KEY (page_id, cookie_id)
);

CREATE TABLE IF NOT EXISTS error(
	id INTEGER NOT NULL AUTO_INCREMENT,
	uri MEDIUMTEXT NOT NULL,
	msg MEDIUMTEXT NOT NULL,
	recorded timestamp NOT NULL,
	PRIMARY KEY(id)
);
