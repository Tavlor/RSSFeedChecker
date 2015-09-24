''' ~*~{O}~*~
	RSSMonitor.py
	Author: Taylor Smith
	Description: A utility to check RSS feeds. Uses a json file to keep track
	of last check and feed URLs. You can edit this to add new feeds or remove old ones.
	
	TODO: allow program to accept date range as an argument to check for 
	releases in that range.
	TODO: add error safety around the JSON file in loadFeeds().
	TODO: logging to a file
	try returning a list of dictionarys for each feed with a title, sum, and results string as well as the total number.
'''

import feedparser, time, json, logging
from datetime import datetime
from os import path

def main():
	decorative =	"=-=-=-=-=-=-=-=-=-=\n"
	
	result = checkFeeds()
	
	#print total and summaries
	print(result[1] + result[2])
	
	#print results
	for string in result[3]:
		print(decorative + string)
#*** END OF MAIN **************************************************************

def getFeedListString(filePath, title=True, url=True, checktime=False):
	result = ""
	for item in getFeedList(filePath):
		if title:
			result = result + "=== " + item["title"]
		if url:
			result = result + "\n	" + item["URL"]
		if checktime:
			result = result + "\n	" + item["latestTimeStamp"]
		result =  result + "\n"
	return result.strip()
#*** END OF getFeedListString() ***********************************************

def getFeedList(filePath):
	#doesn't return actual feed dictionary - just the JSON stuff
	feedJSON = loadJSON(filePath)
	return feedJSON["feeds"]
	
#*** END OF getFeedList() *****************************************************

def loadFeeds(filePath, datetimeFormat):
	#TODO: add error safety;
	
	#load the text file as JOSN
	newjson = loadJSON(filePath)
	newfeeds = []
	
	#failure protections. make sure you have whay you need.
	if not "feeds" in newjson:
		logging.warning("feeds missing!")
		newjson["feeds"] = []
	elif not type(newjson["feeds"]) == list:
		logging.warning("feeds not of type list!")
		newjson["feeds"] = []
	
	if not "lastCheck" in newjson:
		newjson["lastCheck"] = "1970-01-01 00:00:00"
	#parse the urls in the json structure as feeds
	for index, data in enumerate(newjson["feeds"]):
		#--- check all needed components --------------------------------------
		if not "URL" in data:
			logging.warning("feed missing URL! INDEX: %i", index)
			continue #no point in loading it if we don't have a URL
		if not "latestTimeStamp" in data:
			data["latestTimeStamp"] = "1970-01-01 00:00:00"
		if not "title" in data:
			data["title"] = "" #this will be set later.
		#----------------------------------------------------------------------
		#construct array of parsed feeds
		newfeeds.append({"feed":feedparser.parse(data["URL"]), \
		"latestDatetime":datetime.strptime(data["latestTimeStamp"], datetimeFormat)})

	#return a tuple of the json structure and the feed list
	return(newjson, newfeeds)
#*** END OF loadFeeds() *******************************************************

def loadJSON(filePath):
	defaultJSON = '{"feeds":[], "lastCheck":"1970-01-01 00:00:00"}'
	with open(filePath, 'r') as store:
		try:
			newjson = json.load(store)
		except ValueError:
			logging.warning("Invalid json file!")
			newjson = json.loads(defaultJSON)
	return newjson
#*** END OF loadJSON() ********************************************************

def saveJSON(filePath, JSON):
	with open(filePath, 'w') as store:
		json.dump(JSON,store, sort_keys=True, indent=4, separators=(',', ': '))
#*** END OF saveJSON() ********************************************************

def checkFeeds(filePath=""):
	#--- SETUP ----------------------------------------------------------------
	#configure the format which time is loaded/saved in.
	#CAUTION! Changing this might cause issues with parsing the time.
	datetimeFormat = "%Y-%m-%d %H:%M:%S"
	
	#make sure that you have a path. by default filePath = ""
	if filePath == "":
		filePath = path.dirname(__file__) + "\\feeds.txt"
	
	startDatetime = datetime.now()
	#feedDataList = []
	totalTally = 0
	heading = "" #contains totalTally
	fullSummary = "" #contains individual summaries
	results = [] #results =#contains all the new entry names

	#open the JSON file
	feedJSON, feedDataList = loadFeeds(filePath, datetimeFormat)

	#--- MAIN CODE ------------------------------------------------------------
	logging.info("Last checked at " + str(feedJSON["lastCheck"]) + \
	",\nnow checking at " + str(startDatetime))

	#loop through each feed, building a list of new entries
	for index, pair in enumerate(feedDataList):
		#get the feed's results in a tuple.
		feedResult = getNewEntries(pair["feed"], pair["latestDatetime"])
		
		#update totalTally
		totalTally = totalTally + feedResult[0]

		#if there were new items detected, add to results.
		if feedResult[0] > 0:
			results.append(feedResult[1])

		#add the summary piece to fullSummary
		fullSummary = fullSummary + feedResult[2]

		#store the PublishDate of the latest entry so we have it next time
		feedJSON["feeds"][index]["latestTimeStamp"] = \
		datetime.strftime(feedResult[3], datetimeFormat)
		#store the feed name as well.
		feedJSON["feeds"][index]["title"] = pair["feed"].feed.title

	heading = "There are " + str(totalTally) + \
		" new entries in all your feeds.\n"

	#save the new check time in the JSON structure, then save the JSON.
	feedJSON["lastCheck"] = datetime.strftime(startDatetime, datetimeFormat)
	
	saveJSON(filePath, feedJSON)
		
	return (totalTally, heading, fullSummary, results)
#*** END OF checkFeeds() ******************************************************
	
def getNewEntries(feed, lastDatetime, firstDatetime = 0):
	#requires a feed object and a datetime to compare, returns a tuple containing
	#the number of new elements, a string of text representing those elements
	#and a summary string.

	#--- SETUP ----------------------------------------------------------------
	#get the most recent timestamp, will be returned.
	latestTimeStamp = \
	datetime.fromtimestamp(time.mktime(feed.entries[0].updated_parsed))
	
	#keep track of the number of new entries
	counter = 0
	
	#holds the text output of this function.
	feedSummary = ""
	feedText = feed.feed.title + "\n"
	
	#--- MAIN CODE ------------------------------------------------------------
	logging.info("Checking " + feed.feed.title)
	
	#Go through entries until you hit an old one.
	for entry in feed.entries:
		#feedparser parses time as 'time_struct', we need datetime
		feedDatetime = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
		#Check to see if entry is new.
		if feedDatetime > lastDatetime:
			feedText = feedText + entry.title + "\n"
			counter = counter + 1
		else:
			break

	#somewhat intelligent output. Stupid, but clever enough.
	if counter == 0:
		#don't return anything if nothing is new
		pass
	elif counter == 1:
		feedSummary = "There is 1 new entry in " + feed.feed.title + ".\n" 
	else:
		feedSummary = "There are " + str(counter) + " new entries in " + \
		feed.feed.title + ".\n"

	feedText = feedText
	
	#return count, the two strings, and the most recent timestamp in a tuple
	return (counter, feedText, feedSummary, latestTimeStamp)
#*** END OF getNewEntries() ***************************************************

def listFeeds():
#TODO: this should return a count of all feeds and list of feeds w/ last update
	pass
#this allows the program to run on it's own. If the file is imported, then 
#__name__ will equal the module's name.
if __name__ == "__main__":
	main()
