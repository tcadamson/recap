from sys import argv
from yattag import Doc
from yattag import indent
import os

doc, tag, text = Doc().tagtext()
root = os.path.dirname(os.path.abspath(argv[0]))
folder = root + "\\2017\\7.19.2017"
dict = {"score": 1, "title": 2, "dev": 3, "tools": 4, "web": 5, "progress": 6}

def fetch(path):
	data = open(path, 'r').readlines()
	list = []
	for line in data:
		list.append(line.rstrip())
	return list

doc.asis("<!DOCTYPE html>")
with tag("html", lang = "en"):
	with tag("head"):
		doc.stag("meta", charset = "utf-8")
		doc.stag("meta", ("http-equiv", "X-UA-Compatible"), content = "IE=edge")
		doc.stag("meta", name = "viewport", content = "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no")
		with tag("title"):
			text("AGDG Recap")
		doc.stag("link", rel = "stylesheet", href = "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css", integrity = "sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u", crossorigin = "anonymous")
		doc.stag("link", rel = "stylesheet", href = "recap.css")
		with tag("script", src = "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js", integrity = "sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa", crossorigin = "anonymous"):
			text("")
		with tag("script", src = "https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"):
			text("")
	with tag("body"):
		with tag("div", klass = "header"):
			doc.stag("img", src = "agdg.png", alt = "AGDG")
			with tag("h1"):
				text("JULY 2017")
				doc.stag("br")
				with tag("span", id = "week"):
					text("WEEK 3")
		with tag("div", klass = "grid"):
			dat = ""
			for subdir, dirs, files in os.walk(folder):
				for file in files:
					path = subdir + os.sep + dat
					if file.endswith(".txt"):
						dat = file
						continue
					info = fetch(path)
					num = file.replace("img", "")
					with tag("div", klass = "item"):
						doc.stag("img", src = "data/test/" + num, alt = num)
						with tag("div", klass = "frame"):
							with tag("div", klass = "heading"):
								with tag("h2"):
									text(info[dict["title"]])
							with tag("div", klass = "details"):
								with tag("p"):
									doc.asis("DEV&emsp;" + info[dict["dev"]])
									doc.stag("br")
									doc.asis("TOOLS&emsp;" + info[dict["tools"]])
									doc.stag("br")
									doc.asis("WEB&emsp;" + info[dict["web"]])
							with tag("div", klass = "progress"):
								with tag("p"):
									text("PROGRESS")
									for i in range(dict["progress"], len(info)):
										doc.stag("br")
										text(info[i])
							with tag("div", klass = "heading", id = "score"):
								with tag("h2"):
									text(info[dict["score"]])

result = indent(
    doc.getvalue(),
    indentation = '    ',
    indent_text = False
)
with open('test.htm', 'w') as output:
	output.write(result)