import os
import re
import json
import math
import time
import cfscrape
import datetime
from init import read_json, write_json
from dataclasses import dataclass, asdict, field
scraper = cfscrape.create_scraper()
orig = datetime.datetime.strptime("16:10:10", "%y:%m:%d")
urls = {
    "media": "https://i.4cdn.org/vg/{file}",
    "thread": "https://a.4cdn.org/vg/thread/{int}.json",
    "threads": "https://a.4cdn.org/vg/threads.json",
    "archive": "https://a.4cdn.org/vg/archive.json"
}
regs = {
    "title": re.compile("(?<=::).+?(?=::)"),
    "field": re.compile("(?<=>)[^>]*?(?=::)"),
    "content": re.compile("(?<=::).+?(?=[\w\s]{1,}::|$)"),
    "web": re.compile("[-\w]+\.\w{2,}.*?(?=[,<\s]|$)"),
    "stub": re.compile("(?<=\">)[^<]+"),
    "outer": re.compile("<[as][^:]+?[an]>")
}
logs = {
    "fetch": "Fetch: {file} [{count}]",
    "thread": "[Thread: {int}]"
}
replace = {
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": "\"",
    "&#039;": "\'",
    "&amp;": "&",
    "<wbr>": ""
}
fields = [
    "dev",
    "tools",
    "web",
    "progress"
]

@dataclass
class game:
    dev: str = ""
    tools: str = ""
    web: str = ""
    score: list = field(default_factory = list)
    alias: list = field(default_factory = list)

@dataclass
class score:
    stamp: int
    streak: int = 0
    count: int = 0

    def format(self):
        order = [getattr(self, i) for i in ["stamp", "streak", "count"]]
        return ":".join([str(i) for i in order if i >= 0])

def log(code, **args):
    print(logs[code].format(**args))

def parse_reg(reg, com):
    # transform quotelinks into expected form
    stubs = regs["stub"].findall(com)
    for q in regs["outer"].findall(com):
        com = com.replace(q, stubs.pop(0))
    # remove leading and trailing line breaks
    return [re.sub("^[<br>\s]{1,}br>\s*(?=\S)|\s*<br[<br>\s]{1,}$", "", i).strip() for i in regs[reg].findall(com)]

def resolve(title):
    for t, g in gs.items():
        if title in g.alias:
            return t
    return title

def gen_stamp(time):
    test = datetime.datetime.fromtimestamp(time)
    test = test.replace(hour = 0, minute = 0, second = 0)
    index = (test - orig).days // datetime.timedelta(weeks = 1).days
    return stamps["all"][index]

def gen_score(title, stamp):
    g = gs[title]
    recent = g.score.pop()
    start = stamps["all"].index(recent.stamp)
    end = start + recent.streak
    new = recent.streak == 0
    # after streak broken
    if end < stamps["all"].index(stamp):
        g.score.append(recent)
        recent = score(stamp, 1)
    # in new week, streak not broken
    elif new or stamp != recent.stamp and not rs[stamp][title]:
        recent.streak += 1
    recent.count += 1
    g.score.append(recent)

def gen_file(file, stamp):
    # file is the 4chan filename + ext, e.g. 1344402680740.png
    path = "res/{0}/".format(stamp)
    os.makedirs(path, exist_ok = True)
    log("fetch", file = file, count = len(rs[stamp]))
    if not "default" in file:
        with open(path + file, "wb") as f:
            f.write(scraper.get(urls["media"].format(file = file)).content)

def gen_title(title, stamp):
    split = [i.strip() for i in title.split("<")]
    if len(split) > 1:
        title, alias = resolve(split[0]), split[1]
        # don't retitle a game that is being registered
        # gs[title] = gs.pop(old, {}) breaks gs.setdefault(title, game(**zipped))
        if title in gs:
            if not alias in gs[title].alias:
                gs[title].alias.append(alias)
        else:
            title = alias
    rs.setdefault(stamp, read_json("res/{0}/data.json".format(stamp)))
    rs[stamp].setdefault(title, {})
    return title

def gen_pairs(fs, vs):
    out = {}
    for f, v in dict(zip(fs, vs)).items():
        f = f.lower()
        if f in fields and v:
            out[f] = v
    return out

def scrape(thread):
    # scraper will only process posts containing a title surrounded by ::
    # once confirmed, remove title (including ::) and all preceding text to simplify field regex
    for post in thread["posts"]:
        com = post.get("com", "")
        # convert character codes to their actual characters
        for char, to in replace.items():
            com = com.replace(char, to)
        test = parse_reg("title", com)
        if test:
            test = test.pop(0)
            com = re.sub(".*{0}.*?::".format(re.escape(test)), "", com)
            file = "{0}{1}".format(post["tim"], post["ext"]) if post.get("tim") else "default.png"
            stamp = gen_stamp(post["time"])
            title = gen_title(resolve(test), stamp)
            pairs = gen_pairs(parse_reg("field", com), parse_reg("content", com))
            progress = re.sub("[>\s]+([+/-]+)\s{0}(?=\w)", ">\g<1> ", ">{0}".format(pairs.pop("progress", "")))[1:]
            if title in blacklist:
                if title in gs:
                    del rs[stamp][title]
                    del gs[title]
                continue
            if pairs or progress:
                # users can freely overwrite dev, tools, web fields
                gs.setdefault(title, game(**pairs))
                g = gs[title]
                for field, content in pairs.items():
                    if hasattr(g, field):
                        setattr(g, field, re.sub(",(?=[^<\s])|[,\s]*<br>\s*", ", ", content))
                links = parse_reg("web", g.web.replace("@", "twitter.com/").replace("www", ""))
                g.web = "<br>".join([i[:-1] if i.endswith("/") else i for i in links])
                # collection of file:progress pairs under a registered title
                # truncated file is time:tim(ms part).ext
                if progress and not progress in rs[stamp][title].values():
                    # live stamps are those stamps for which a recap exists
                    # used to generate archive links on the site
                    if not stamp in stamps["live"]:
                        stamps["live"].append(stamp)
                    if not g.score:
                        g.score.append(score(stamp))
                    gen_file(file, stamp)
                    gen_score(title, stamp)
                    file = file[10:] if post.get("tim") else file
                    rs[stamp][title]["{0}:{1}".format(post["time"], file)] = progress

# convert games to dataclasses for easy manipulation
games = read_json("res/games.json")
stamps = read_json("res/stamps.json")
threads = read_json("res/threads.json")
blacklist = "res/blacklist.txt"
if os.path.isfile(blacklist):
    blacklist = open(blacklist, "r").readlines()
gs = {}
rs = {}
for title, d in games.items():
    g = game(*d.values())
    g.score = [score(*[int(j) for j in i.split(":")]) for i in g.score]
    gs[title] = g

# crawl archive and catalog for threads
# only threads in archive are marked as seen
# threads in catalog continually scraped until they are archived
catalog = []
for page in json.loads(scraper.get(urls["threads"]).text):
    for thread in page["threads"]:
        catalog.append(thread["no"])
set1 = set(threads)
set2 = set(json.loads(scraper.get(urls["archive"]).text) + catalog)
threads = list(set2 - (set1 & set2))
seen = list(set1 - (set1 - set2))
for int in sorted(threads):
    thread = json.loads(scraper.get(urls["thread"].format(int = int)).text)
    op = thread["posts"][0]
    if "agdg" in op.get("sub", "").lower():
        if not int in seen:
            if not int in catalog:
                seen.append(int)
            log("thread", int = int)
            scrape(thread)
    elif not int in seen:
        seen.append(int)

# convert dataclasses to JSON-legal format for file writing
for title, g in gs.items():
    g.score = [i.format() for i in g.score]
    gs[title] = asdict(g)
stamps["now"] = gen_stamp(time.time())
write_json("res/games.json", gs)
write_json("res/stamps.json", stamps)
write_json("res/threads.json", seen)

for stamp, r in rs.items():
    # posts with fields/contents but invalid title leave an empty {}, here we prune them
    r = {k:v for k, v in r.items() if v}
    if r:
        with open("res/{0}/data.json".format(stamp), "w") as f:
            json.dump(r, f, separators = (",", ":"))