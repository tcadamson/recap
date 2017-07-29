from datetime import datetime
from requests import get
from sys import argv
import json
import shutil
import json
import re
import os

success = 200
img_url_clip = 22
recap = "----[ Recap ]----"
exclude = "-------- AGDG Weekly Recap --------"
score_interval = 5
mult_interval = 0.5
max_mult = 10.0
streak_interval = 1
scale = 1
flags = {
	"export_scores": False, # Write raw score data
	"export_archive": False, # Write formatted scoring list with archive-related data
	"export_json": True
}
now = datetime.now()
date = str(now.month) + "." + str(now.day) + "." + str(now.year)
parent = "2017/" + date
fake_time = 1483976641887
devs = []
ignore = [] # Set of game names to ignore for this pass if people submit entries twice for some reason
score_dict = {}

def clamp(arg, value):
	if arg < value:
		return value
	else:
		return arg

def query(filter, string, progress):
	try:
		result = re.search(filter, string).group(1).strip()
		# Replace special characters
		result = result.replace("&gt;", ">")
		result = result.replace("&lt;", "<")
		result = result.replace("&quot;", "\"")
		result = result.replace("&#039;", "\'")
		result = result.replace("<wbr>", "")
		result = result.replace("&amp;", "&")
		result = result.replace("</span>", "")
		if progress:
			temp = result
			filter = "br>(.+?)<|br>(.+?)$"
			result = re.findall(filter, temp)
	except AttributeError:
		result = ""
	return result

def format(item):
	# Enforce at least one space between progress marker and text
	if item[1] != " ":
		item = item[0:1] + " " + item[1:]
	return item

def process(post):
	dev = {}
	# Get correct image
	url = "https://my.mixtape.moe/scaxyw.png"
	dev["tim"] = str(fake_time + 1)
	dev["ext"] = ".png"
	if ("tim" in post):
		url = "https://i.4cdn.org/vg/" + str(post["tim"])
		dev["tim"] = str(post["tim"])
		dev["ext"] = post["ext"]
		if post["ext"] == ".webm":
			dev["ext"] = "s.jpg"
		url = url + dev["ext"]
	dev["image"] = get(url)
	print("Fetch: " +  dev["tim"] + dev["ext"])
	if dev["image"].status_code != success:
		raise Exception("Bad image URL")
	# Get data from fields
	comment = post["com"]
	dev["game"] = query("Game:(.+?)<br>", comment, 0)
	dev["name"] = query("Dev:(.+?)<br>", comment, 0)
	dev["tools"] = query("Tools:(.+?)<br>", comment, 0)
	dev["web"] = query("Web:(.+?)<br>", comment, 0)
	dev["progress"] = []
	list = query("Progress:(.*)", comment, 1)
	for item in list:
		if len(item[0]) > 0:
			dev["progress"].append(format(item[0]))
		else:
			dev["progress"].append(format(item[1]))
	# Optional form args
	dev["*game"] = query("\*Game:(.+?)<br>", comment, 0)
	return dev

def scoring(dev):
	new = False
	returning = False
	# Check if game exists in database. If it does, use title case of entry
	for name, data in score_dict.items():
		if name.upper() == dev["game"].upper():
			dev["game"] = name
	if not dev["game"] in score_dict:
		new = True
		score_dict[dev["game"]] = {"score": 5, "mult": 1.0, "streak": 1, "reset": 0, "inactive": 0}
	# Check for game title change
	if (dev["*game"] != ""):
		score_dict[dev["*game"]] = score_dict[dev["game"]]
		del score_dict[dev["game"]]
		dev["game"] = dev["*game"]
	# Get score data for game and perform necessary calculations
	dict = score_dict[dev["game"]]
	score, mult, streak, reset, active = int(dict.get("score")), float(dict.get("mult")), int(dict.get("streak")), int(dict.get("reset")), int(dict.get("inactive"))
	if reset < 0:
		returning = True
		reset, mult, streak = 0, 1.0, 0
	reset = reset + 1
	inactive = 0
	if not new:
		score = score + int(score_interval * scale * mult)
		if not returning:
			mult = mult + (mult_interval * scale)
		if mult > max_mult:
			mult = max_mult
		streak = streak + (streak_interval * scale)
	# Store current score data
	dict["score"] = str(score)
	dict["mult"] = str(mult)
	dict["streak"] = str(streak)
	dict["reset"] = str(reset)
	dict["inactive"] = str(inactive)
	scoring = str(score) + " [x" + str(mult) + "]"
	if streak > 1:
		scoring = scoring + " - " + str(streak) + " streak"
	dev["scoring"] = scoring

# Load scoring data
scores = open("score_data.txt", "r").readlines()
for line in scores:
	string = line.split("#")
	string[5] = string[5].replace("\n", "")
	reset = int(string[4]) - scale
	reset = clamp(reset, -1)
	inactive = int(string[5]) + scale
	score_dict[string[0]] = {"score": string[1], "mult": string[2], "streak": string[3], "reset": str(reset), "inactive": str(inactive)}

# Get threads to scrape, then scrape them
threads = open("threads.txt", "r").readlines()
for thread in threads:
	url = "https://a.4cdn.org/vg/thread/" + str.strip(thread, "\n") + ".json"
	# Fetch thread URL data
	thread = get(url)
	if thread.status_code != success:
		raise Exception("Bad thread URL")
	# Process thread data
	data = json.loads(thread.text)
	for post in data["posts"]:
		if ("com" in post) and (recap in post["com"]) and not (exclude in post["com"]):
			dev = process(post)
			scoring(dev)
			# Skip duplicate entries
			if not (dev["game"] in ignore):
				ignore.append(dev["game"])
			else:
				continue
			devs.append(dev)

if flags.get("export_json"):
	data = {}
	if (not os.path.isdir(parent)):
		os.makedirs(parent)
		os.makedirs(parent + "/images")
	for dev in devs:
		with open(parent + "/images/" + dev["tim"] + dev["ext"], "wb") as output:
			output.write(dev["image"].content)
		# Prepare data for JSON dump
		temp = {}
		temp["game"] = dev["game"]
		temp["name"] = dev["name"]
		temp["tools"] = dev["tools"]
		temp["web"] = dev["web"]
		temp["scoring"] = dev["scoring"]
		temp["ext"] = dev["ext"]
		list = []
		for item in dev["progress"]:
			list.append(item)
		temp["progress"] = list
		data[dev["tim"]] = temp\
	# Write JSON
	open(parent + "/data.json", "w").close()
	with open(parent + "/data.json", "w") as output:
		json.dump(data, output, indent = 4)

# Scores
if flags.get("export_scores"):
	open("score_data.txt", "w").close()
	with open("score_data.txt", "w") as output:
		for game, dev_dict in score_dict.items():
			output.write(game + "#" +
				str(dev_dict.get("score"))+ "#" +
				str(dev_dict.get("mult")) + "#" +
				str(dev_dict.get("streak")) + "#" +
				str(dev_dict.get("reset")) + "#" +
				str(dev_dict.get("inactive")) +
				"\n")
	# Scores backup
	shutil.copy2("score_data.txt", "archives/scores/score_data_" + date + ".txt")

def tier_iter(range_token, set, last_tier):
	output.write(range_token + "\n")
	sort = {}
	for game in set:
		sort[game] = int(score_dict[game].get("score"))
	sort = sorted(sort, key = sort.get, reverse = True)
	for game in sort:
		output.write(score_dict[game].get("score") + "  --  " + game)
		if (int(score_dict[game].get("reset")) > 0) and (float(score_dict[game].get("mult")) > 1):
			output.write(" (x" + score_dict[game].get("mult") + ", " + score_dict[game].get("streak") + " streak)\n")
		else:
			output.write("\n")
	if not last_tier:
		output.write("\n")

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
	return {"one": tier_1, "two": tier_2, "three": tier_3, "four": tier_4}

# Scores archive export
if flags.get("export_archive"):
	open("score_archive.txt","w").close()
	with open("score_archive.txt", "w") as output:
		tiers = load_tiers(False)
		tier_iter("[ 1000+ ]", tiers.get("four"), False)
		tier_iter("[ 500 - 999 ]", tiers.get("three"), False)
		tier_iter("[ 200 - 499 ]", tiers.get("two"), False)
		tier_iter("[ 1 - 199 ]", tiers.get("one"), True)
	# Scores archive backup
	shutil.copy2("score_archive.txt", "archives/scores/score_archive_" + date + ".txt")