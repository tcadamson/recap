import os
import json
import time
import shutil
import datetime
from dataclasses import dataclass, asdict, field
orig = datetime.datetime.strptime("16:10:10", "%y:%m:%d")
orig = orig.replace(year = orig.year % 100)
step = datetime.timedelta(weeks = 1)
# recaps cover monday to sunday inclusive
# monday is the 4th -> only 3 days out of the most recent recap period were from this month
# thus most recent recap belongs to previous month
threshold = 4
orig_w = 2
span = 365
template = {
    "games": {},
    "stamps": {
        "all": [],
        "live": []
    },
    "threads": [],
}

@dataclass
class stamp:
    y: int
    m: int
    w: int

    def encode(self):
        self.y *= 1000
        self.m *= 10
        return self.y + self.m + self.w

def decode(s):
    y = s // 1000
    m = (s - y * 1000) // 10
    w = s % 10
    return stamp(y, m, w)

def key(file):
    return file.split(".")[0].replace("res/", "")

def read_json(file):
    loaded = template.get(key(file), {})
    if os.path.isfile(file):
        with open(file) as f:
            loaded = json.load(f)
    return loaded

def write_json(file, output):
    backup = "backup/{0}".format(key(file))
    with open(file, "w") as f:
        json.dump(output, f, separators = (",", ":"))
    if os.path.isdir(backup):
        shutil.copy2(file, "{0}/{1:.0f}.json".format(backup, time.time()))

# don't run when imported from the other scripts
if __name__ == "__main__":
    for folder in ["games", "stamps", "stats"]:
        os.makedirs("backup/{0}".format(folder), exist_ok = True)
    os.makedirs("res", exist_ok = True)

    # generate first recap code
    orig += step
    stamps = [stamp(orig.year, orig.month, orig_w).encode()]

    while len(stamps) < span:
        orig += step
        s = decode(stamps[-1])
        if orig.day > threshold:
            if s.m < orig.month:
                s.m += 1
                s.w = 0
            elif s.y < orig.year:
                s.y += 1
                s.m = 1
                s.w = 0
        s.w += 1
        stamps.append(s.encode())

    template["stamps"]["all"] = stamps
    for file in template:
        p = "res/{0}.json".format(file)
        write_json(p, read_json(p))