# this reads org_domains.json, sorts it alpha, and write back out
# benefit is it allows us to just add new entries to the top of org_domains.json
# and not worry about keeping in order, otherwise somewhat pointless, likely
# could be reduced to 3 lines of code, but this works and I'm not in the mood to look at
# python docs

import json
		
if __name__ == '__main__':
	infile	= open('org_domains.json', 'r')
	data 	= json.load(infile)
	infile.close()

	outfile	= open('org_domains.json', 'w')

	data_sorted = sorted(data, key=lambda data:data['organization'].lower())
	outfile.write('[\n')

	# all but the last one
	max = len(data_sorted)
	current = 1
	
	for item in data_sorted:
		current += 1
		outfile.write('\t{\n')
		outfile.write('\t\t"organization"\t:\t"%s",\n' % item['organization'])
		outfile.write('\t\t"notes"\t\t\t:\t"%s",\n' % item['notes'])
		outfile.write('\t\t"country"\t\t:\t"%s",\n' % item['country'])
		outfile.write('\t\t"domains"\t\t:\t[\n')
		# loop through all but last as last does not end with ','
		sorted_domains = sorted(item['domains'])
		for domain in sorted_domains[:-1]:
			outfile.write('\t\t\t"%s",\n' % domain)
		outfile.write('\t\t\t"%s"\n' % sorted_domains[-1])
		outfile.write('\t\t]\n')
		
		if current <= max:
			outfile.write('\t},\n')
		else:
			outfile.write('\t}\n')

	# done looping, close the json
	outfile.write(']')
	outfile.close()
# end main
