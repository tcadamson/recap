from datetime import datetime
from requests import get
from sys import argv
import shutil
import json
import re
import os

SUCCESS = 200
IMG_URL_CLIP = 22
RECAP = '----[ Recap ]----'
EXCLUDE = '-------- AGDG Weekly Recap --------'
SCORE_INTERVAL = 5
MULT_INTERVAL = 0.5
MAX_MULT = 10.0
STREAK_INTERVAL = 1
SCALE = 1
FLAGS = {
	"export_scraped": True, # Write scraped dev/game data
	"export_scores": True, # Write raw score data
	"export_archive": True, # Write formatted scoring list with archive-related data
	# "export_recap": False # Write recap post which includes trimmed scoring list
}

now = datetime.now()
date = str(now.month) + '.' + str(now.day) + '.' + str(now.year)
parent = date
root = os.path.dirname(os.path.abspath(argv[0]))
last_tim = 1483976641887
tim_offset = 1
devs = []
ignore = [] # Set of game names to ignore for this pass if people submit entries twice for some reason

def clamp(arg, value):
	if arg < value:
		return value
	else:
		return arg

def query(filter, string, progress):
	try:
		result = re.search(filter, string).group(1).strip()
		# Replace special characters
		result = result.replace('&gt;', '>')
		result = result.replace('&lt;', '<')
		result = result.replace('&quot;', '"')
		result = result.replace('&#039;', '\'')
		result = result.replace('<wbr>', '')
		result = result.replace('&amp;', '&')
		result = result.replace('</span>', '') # Fix for when people greentext the form
		# result = result.replace('<br>', '') # Fix (sort of) for when people add line breaks
		if progress:
			temp = result
			filter = 'br>(.+?)<|br>(.+?)$'
			result = re.findall(filter, temp)
			# if len(result) > 0:
			#	result[0] = result[0].replace('< span class="quote">>', '')
			#	result[1] = result[1].replace('< span class="quote">>', '')
	except AttributeError:
		result = ''
	return result

def format(item):
	# Enforce at least one space between progress marker and text
	if item[1] != ' ':
		item = item[0:1] + ' ' + item[1:]
	return item

# Make sure needed files exist
if not os.path.isfile("recap.txt"):
	open('recap.txt','a').close()
if not os.path.isfile("score_data.txt"):
	open('score_data.txt','a').close()
if not os.path.isfile("score_archive.txt"):
	open('score_archive.txt','a').close()

# Scoring system
score_dict = {}
# open('scores.txt', 'w').close() # Uncomment to reset scores
scores = open('score_data.txt', 'r').readlines()
for line in scores:
	# print('line...')
	string = line.split('#')
	string[5] = string[5].replace('\n', '')
	reset = int(string[4]) - SCALE
	reset = clamp(reset, -1)
	inactive = int(string[5]) + SCALE
	score_dict[string[0]] = {"score": string[1], "mult": string[2], "streak": string[3], "reset": str(reset), "inactive": str(inactive)}

# Get threads to scrape, then scrape them
threads = open('threads.txt', 'r').readlines()
for thread in threads:
	url = 'https://a.4cdn.org/vg/thread/' + str.strip(thread, '\n') + '.json'

	# Fetch thread URL data
	thread = get(url)
	if thread.status_code != SUCCESS:
		raise Exception('Bad thread URL')

	# Create thread folder
	folder = re.search('thread/(.+?).json', url).group(1)
	path = root + '\\2017\\' + parent + '\\' + folder
	if (not os.path.isdir(path)) and (FLAGS.get("export_scraped")):
		os.makedirs(path)

	# Process thread data
	data = json.loads(thread.text)
	for post in data['posts']:
		if ('com' in post) and (RECAP in post['com']) and not (EXCLUDE in post['com']):
			comment = post['com']
			img_url = ''
			ext = ''
			tim = ''
			if not ('tim' in post):
				# img_url = 'https://my.mixtape.moe/fdqkwe.png'
				img_url = 'https://my.mixtape.moe/scaxyw.png'
				ext = '.png'
				tim = last_tim + tim_offset
			else:
				last_tim = post['tim']
				img_url = 'https://i.4cdn.org/vg/' + str(post['tim'])
				ext = post['ext']
				tim = str(post['tim'])
				if post['ext'] == '.webm':
					ext = 's.jpg'
				img_url = img_url + ext
			dev = {}
			dev['img_path'] = parent + '\\' + folder + '\\' + str(tim) + 'img' + ext
			dev['dat_path'] = parent + '\\' + folder + '\\' + str(tim) + 'dat.txt'
			dev['game'] = query('Game:(.+?)<br>', comment, 0)
			dev['name'] = query('Dev:(.+?)<br>', comment, 0)
			dev['tools'] = query('Tools:(.+?)<br>', comment, 0)
			dev['web'] = query('Web:(.+?)<br>', comment, 0)

			# Recap form optional args
			dev['title_change'] = query('NEW_TITLE:(.+?)<br>', comment, 0)
			# dev['color'] = query('Color:(.+?)<br>', comment, 0)
			# dev['halloween'] = query('Halloween:(.+?)<br>', comment, 0)
			# dev['holidays'] = query('Holidays:(.+?)<br>', comment, 0)

			dev['progress'] = []
			temp = query('Progress:(.*)', comment, 1)

			# Append string from relevant capture group
			for item in temp:
				if len(item[0]) > 0:
					dev['progress'].append(format(item[0]))
				else:
					dev['progress'].append(format(item[1]))

			# Remove # prefix if present
			# dev['color'].replace('#', '')

			# Increase score
			new = False
			returning = False
			game = dev['game']
			for name, data in score_dict.items():
				if name.upper() == dev['game'].upper():
					game = name
			if not game in score_dict:
				new = True
				score_dict[game] = {"score": 5, "mult": 1.0, "streak": 1, "reset": 0, "inactive": 0}
			if not (dev['title_change'] == ''):
				score_dict[dev['title_change']] = score_dict[game]
				del score_dict[game]
				dev['game'] = dev['title_change']
				game = dev['title_change']
			dict = score_dict[game]
			score, mult, streak, reset, active = int(dict.get("score")), float(dict.get("mult")), int(dict.get("streak")), int(dict.get("reset")), int(dict.get("inactive"))
			if reset < 0:
				returning = True
				reset, mult, streak = 0, 1.0, 0
			reset = reset + 1
			inactive = 0
			if not new:
				score = score + int(SCORE_INTERVAL * SCALE * mult)
				if not returning:
					mult = mult + (MULT_INTERVAL * SCALE)
				if mult > MAX_MULT:
					mult = MAX_MULT
				streak = streak + (STREAK_INTERVAL * SCALE)
			dict['score'] = str(score)
			dict['mult'] = str(mult)
			dict['streak'] = str(streak)
			dict['reset'] = str(reset)
			dict['inactive'] = str(inactive)
			scoring = str(score) + ' [x' + str(mult) + ']'
			if streak > 1:
				scoring = scoring + ' - ' + str(streak) + ' streak'
			dev['scoring'] = scoring

			# Load progress image
			if FLAGS.get("export_scraped"):
				print('Fetching ' + img_url[IMG_URL_CLIP:] + '...')
				dev['image'] = get(img_url)
				if dev['image'].status_code != SUCCESS:
					raise Exception('Bad image URL')

			# Skip duplicate entries
			if not (game in ignore):
				ignore.append(game)
			else:
				continue

			devs.append(dev)

# Process dev data
if FLAGS.get("export_scraped"):
	for dev in devs:
		# Commit image
		with open(dev['img_path'], 'wb') as output:
			output.write(dev['image'].content)

		# Commit dev data
		open(dev['dat_path'], 'w').close()
		with open(dev['dat_path'], 'a') as output:
			# output.write(dev['color'] + '\n')
			# output.write(dev['halloween'] + '\n')
			# output.write(dev['holidays'] + '\n')
			output.write('\n')
			output.write(dev['scoring'] + '\n')
			output.write(dev['game'] + '\n')
			output.write(dev['name'] + '\n')
			output.write(dev['tools'] + '\n')
			output.write(dev['web'] + '\n')
			for item in dev['progress']:
				output.write(item + '\n')

# Scores
if FLAGS.get("export_scores"):
	open('score_data.txt', 'w').close()
	with open('score_data.txt', 'w') as output:
		for game, dev_dict in score_dict.items():
			# print('parsing item...')
			output.write(game + '#' +
				str(dev_dict.get("score"))+ '#' +
				str(dev_dict.get("mult")) + '#' +
				str(dev_dict.get("streak")) + '#' +
				str(dev_dict.get("reset")) + '#' +
				str(dev_dict.get("inactive")) +
				'\n')

	# Scores backup
	shutil.copy2('score_data.txt', '_archives/scores/score_data_' + date + '.txt')

def tier_iter(range_token, set, last_tier):
	output.write(range_token + '\n')
	sort = {}
	for game in set:
		sort[game] = int(score_dict[game].get("score"))
	sort = sorted(sort, key = sort.get, reverse = True)
	for game in sort:
		output.write(score_dict[game].get("score") + '  --  ' + game)
		if (int(score_dict[game].get("reset")) > 0) and (float(score_dict[game].get("mult")) > 1): #(float(score_dict[game].get("mult")) > 1) or (int(score_dict[game].get("streak")) > 1):
			output.write(' (x' + score_dict[game].get("mult") + ', ' + score_dict[game].get("streak") + ' streak)\n')
		else:
			output.write('\n')
	if not last_tier:
		output.write('\n')

def load_tiers(check_inactive):
	tier_1 = [] # 1 to 199
	tier_2 = [] # 200 - 499
	tier_3 = [] # 500 - 999
	tier_4 = [] # 1000+
	for game, dev_dict in score_dict.items():
		inactive, score = int(dev_dict.get("inactive")), int(dev_dict.get("score"))
		def append_check(game):
			if score < 200:
				tier_1.append(game)
			elif score >= 200 and score < 499:
				tier_2.append(game)
			elif score >= 500 and score < 999:
				tier_3.append(game)
			elif score > 1000:
				tier_4.append(game)
		if check_inactive:
			if inactive <= 3:
				append_check(game)
		else:
			append_check(game)
	return {'one': tier_1, 'two': tier_2, 'three': tier_3, 'four': tier_4}

# Scores archive export
if FLAGS.get("export_archive"):
	open('score_archive.txt','w').close()
	with open('score_archive.txt', 'w') as output:
		tiers = load_tiers(False)
		tier_iter('[ 1000+ ]', tiers.get("four"), False)
		tier_iter('[ 500 - 999 ]', tiers.get("three"), False)
		tier_iter('[ 200 - 499 ]', tiers.get("two"), False)
		tier_iter('[ 1 - 199 ]', tiers.get("one"), True)
	# Scores archive backup
	shutil.copy2('score_archive.txt', '_archives/scores/score_archive_' + date + '.txt')

# Recap post export
if FLAGS.get("export_recap"):
	open('recap.txt','w').close()
	with open('recap.txt', 'w') as output:
		# Recap info
		output.write('-------- AGDG WEEKLY RECAP --------\n' +
		'Fill out the form to be a part of the weekly progress recap. Be sure to check out the "read me" link for important information on scoring and formatting.\n'
		'Submissions will be accepted for at least the next 36 hours.\n\n' +
		'-------- FORMAT\n' +
		'----[ Recap ]----\n' +
		'Game:\nDev:\nTools:\nWeb:\nProgress:\n+ ...\n- ...\n\n' +
		# 'Formatting tips\n(link)\n\n' +
		'-------- LINKS\n' +
		'Read me: pastebin.com/QA047M2e\n' +
		'Recap archive: dropbox.com/sh/icm5ng2zs8p24uh/AACC61OsXzCgl6-9Vdwb4sRAa\n' +
		'Scores archive: pastebin.com/AmFmLeAy\n\n' +
		'-------- SCORES\n')
		# Scores
		tiers = load_tiers(True)
		tier_iter('[ 1000+ ]', tiers.get("four"), False)
		tier_iter('[ 500 - 999 ]', tiers.get("three"), False)
		tier_iter('[ 200 - 499 ]', tiers.get("two"), False)
		tier_iter('[ 1 - 199 ]', tiers.get("one"), True)
		# Recap info (cont.)
		output.write('\n-------- FEEDBACK\n' +
		'Notice something wrong with your entry, score, or anything else? Let me know and I\'ll look into it.')