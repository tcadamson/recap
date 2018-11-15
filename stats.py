import os
import re
import json
from init import read_json, write_json
places = 3
regs = {
    "words": re.compile("\\b\S+\\b"),
    "tools": re.compile("\\b[^\\/\s]+[^,\\/\s]"),
    "studio": re.compile("\w+\sstudio")
}
tool_regs = {
    "unity": re.compile("unity[\w]*"),
    "ue4": re.compile("\\bue[\w]*|unreal"),
    "gamemaker": re.compile("\\bgm[:\w]*|game\s*maker[:\w\s]*?"),
    "photoshop": re.compile("\\bps|photoshop"),
    "aseprite": re.compile("a[se]+prite")
}
stats = {}
counts = {}
data = {}

for root, dirs, files in os.walk("res"):
    for dir in dirs:
        parent = os.path.join(root, dir)
        for f in os.listdir(parent):
            if f.endswith(".json"):
                data[dir] = json.load(open(os.path.join(parent, f)))

entries = 0
progress = 0
for stamp, recap in data.items():
    net_words = 0
    for title, r in recap.items():
        g_words = 0
        for pair, p in r.items():
            g_words += len(regs["words"].findall(p))
        stats.setdefault(title, {})
        stats[title]["1"] = stats[title].get("1", 0) + 1
        stats[title]["words"] = stats[title].get("words", 0) + g_words
        net_words += g_words
    progress += net_words / len(recap)
    entries += len(recap)

def check_predefined(str):
    for id, reg in tool_regs.items():
        result = reg.findall(str)
        if result:
            for r in result:
                str = str.replace(r, "")
            counts[id] = counts.get(id, 0) + 1
    return str

games = read_json("res/games.json")
for title, g in games.items():
    stats[title]["2"] = max([int(i.split(":")[1]) for i in g["score"]])
    stats[title]["3"] = "{0} words".format(round(stats[title].pop("words") / stats[title]["1"]))
    # tally the commonly used/misspelled tools all at once (especially those involving multiple words)
    # many tools have a studio suffix, so a special case is used to account for those
    tools = check_predefined(" ".join(regs["tools"].findall(g["tools"].lower())))
    for str in regs["studio"].findall(tools):
        tools = tools.replace(str, "")
        counts[str] = counts.get(str, 0) + 1
    for t in regs["tools"].findall(tools.replace("studio", "")):
        counts[t] = counts.get(t, 0) + 1

recaps = len(data)
tools = sorted(counts, key = counts.get, reverse = True)[:places]
write_json("res/stats.json", {
    "1": recaps,
    "2": len(games),
    "3": round(entries / recaps),
    "4": "{0} words".format(round(progress / recaps)),
    "5": " ".join(tools),
    **stats
});