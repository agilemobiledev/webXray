-- parsing out info from uris is time consuming
-- so we use this table to only do it once, index on hash
-- for quick look-up

-- kill old tables
DROP TABLE IF EXISTS sub_domain_tld;

CREATE TABLE IF NOT EXISTS sub_domain_tld(
	sub_domain_md5 VARCHAR(32) UNIQUE,
	sub_domain MEDIUMTEXT,
	domain_md5 VARCHAR(32),
	domain MEDIUMTEXT,
	pubsuffix_md5 VARCHAR(32),
	pubsuffix VARCHAR(255),
	tld_md5 VARCHAR(32),
	tld VARCHAR(255),
	PRIMARY KEY(sub_domain_md5)	
);
