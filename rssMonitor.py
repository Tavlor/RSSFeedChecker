''' ~*~{O}~*~
	rssMonitor.py
	Author: Taylor Smith
	Comment: 
		A utility to check RSS feeds. Uses a json file (feeds.txt) to keep
		track of last check and feed URLs. You can edit the json to add new
		feeds or remove old ones.

	NOTE: In the code, keeping the parsed JSON and the parsed feeds separate
		makes saving the JSON data MUCH easier.
		
	NOTE: DO NOT USE "lastCheck" FOR TIMESTAMP COMPARRISONS!!! You don't know
		what time zone the feed comes from. It is better to compare it with
		it's own timestamps (also, you cannot push back "lastCheck" because it
		gets reset to the current time at each run)

	TODO: logging to a file
	TODO: try returning a list of dictionarys for each feed with a title, sum,
		and results string as well as the total number.
	TODO: let program announce some feeds immediatly, daily, or weekly.
		Framework in JSON is set up already.
'''

import feedparser, time, json, logging
from datetime import datetime
from os import path

def main():
	print("Starting up\n")
	decorative =	"=-=-=-=-=-=-=-=-=-=\n"
	
	result = checkFeeds()
	
	#for testing
	#filePath = path.dirname(__file__) + "\\feeds.txt"
	#feedJSON, parsedFeeds = loadFeeds(filePath)
	#PUT TEST CODE HERE!
	#saveJSON(filePath, feedJSON)
	
	#print total and summaries
	print(result[1] + result[2])
	
	#print results
	for string in result[3]:
		print(decorative + string)
#*** END OF MAIN **************************************************************


def checkFeeds(filePath="", urgency=-1):
	#--- SETUP ----------------------------------------------------------------
	#configure the format which time is loaded/saved in.
	#CAUTION! Changing this might cause issues with parsing the time.
	datetimeFormat = "%Y-%m-%d %H:%M:%S"
	
	#make sure that you have a path. by default filePath = ""
	#if filePath is still "", set it to feeds.txt in the program's folder
	if filePath == "":
		#filePath = path.dirname(__file__) + "\\feeds.txt"
		filePath = path.abspath("feeds.txt")
	else: #to ensure that the path is normalized.
		filePath = path.abspath(filepath)
	
	startDatetime = datetime.now()
	totalTally = 0
	heading = "" 		#contains totalTally, summary of all feeds
	fullSummary = ""	#contains individual feed summaries
	results = [] 		#contains all the new entry names

	#open the JSON file (it can take a few seconds to parse the feeds)
	feedJSON, parsedFeeds= loadFeeds(filePath, datetimeFormat)
	print("data from feeds.txt loaded\n")

	#--- MAIN CODE ------------------------------------------------------------
	logging.info("Last checked at " + str(feedJSON["lastCheck"]) + \
	",\nnow checking at " + str(startDatetime))

	#loop through each feed, building a list of new entries
	for index, parsedFeed in enumerate(parsedFeeds):
		print("checking feed %i/%i  "  % \
			(index + 1,len(feedJSON["feeds"])), end="\r")
			
		#check that parsedFeeds is not None
		if parsedFeed is None:
			logging.warning("Feed skipped: %i" % index)
			continue
		
		#get the target timestamp for this feed
		feedTargetTimestamp = datetime.strptime(\
			feedJSON["feeds"][index]["latestTimeStamp"], datetimeFormat)
		
		#get the feed's results in a tuple.
		feedResult = getNewEntries(parsedFeed, feedTargetTimestamp)
		
		#--- CLERICAL CODE ----------------------------------------------------
		#update totalTally
		totalTally = totalTally + feedResult[0]

		#if there were new items detected, add to results.
		if feedResult[0] > 0:
			results.append(feedResult[1])

		#add the summary piece to fullSummary
		fullSummary = fullSummary + feedResult[2]

		#store the PublishDate of the newest entry so we have it for next time
		feedJSON["feeds"][index]["latestTimeStamp"] = \
		datetime.strftime(feedResult[3], datetimeFormat)

	print("\nfeeds checked!")
	#Contextual output! total number of entries effects the main summary
	if totalTally == 0:
		heading = "There are no new entries in any of your feeds.\n"
	elif totalTally == 1:
		heading = "There is 1 new entry in all your feeds.\n"
	else:
		heading = "There are " + str(totalTally) + \
			" new entries in all your feeds.\n"

	#save the time we started in the JSON structure
	feedJSON["lastCheck"] = datetime.strftime(startDatetime, datetimeFormat)
	#and then save the JSON structure
	saveJSON(filePath, feedJSON)
		
	return (totalTally, heading, fullSummary, results)
#*** END OF checkFeeds() ******************************************************


def getNewEntries(feed, targetDatetime):
	#accepts a feed object and a datetime object to compare, returns a tuple
	#containing the number of new elements, a string of text representing those
	#elements and a summary string.

	#--- SETUP ----------------------------------------------------------------
	#get the feed's most recent timestamp, will be returned.
	feedLatestTimeStamp = \
	datetime.fromtimestamp(time.mktime(feed.entries[0].updated_parsed))
	#note that I convert 'time_struct' to 'datetime'
	
	#keep track of the number of new entries
	counter = 0
	
	#holds the text output of this function.
	feedSummary = ""
	feedText = feed.feed.title + "\n"

	#--- MAIN CODE ------------------------------------------------------------
	logging.info("Checking " + feed.feed.title)
	
	#Go through entries until you hit an old one.
	for entry in feed.entries:
		#get the entry's timestamp
		entryTimeStamp = entry.updated_parsed
		#feedparser parses time as 'time_struct', convert to 'datetime'
		entryDatetime = datetime.fromtimestamp(time.mktime(entryTimeStamp))
		
		#Check to see if entry is new.
		if entryDatetime > targetDatetime:
			feedText = feedText + entry.title + "\n"
			counter = counter + 1
		else:
			break

	#Feed summary formatting. 
	if counter == 0:
		#don't return anything if nothing is new
		pass
	elif counter == 1:
		feedSummary = " } " + str(counter) + " new entry in " + \
		feed.feed.title + ".\n"
	else:
		feedSummary = " } " + str(counter) + " new entries in " + \
		feed.feed.title + ".\n"

	feedText = feedText
	
	#return count, the two strings, and the most recent timestamp in a tuple
	return (counter, feedText, feedSummary, feedLatestTimeStamp)
#*** END OF getNewEntries() ***************************************************


#--- LOADING/SAVING DATA ---------------------------------------------------<<<
def loadJSON(filePath):
	#This function is used to load the .TXT file as a JSON structure
	defaultJSON = '{"feeds":[], "lastCheck":"1970-01-01 00:00:00"}'
	with open(filePath, 'r') as store:
		try:
			newjson = json.load(store)
		except ValueError:
			logging.warning("Invalid json file!")
			newjson = json.loads(defaultJSON)
	return newjson
#*** END OF loadJSON() ********************************************************


def loadFeeds(filePath, datetimeFormat="%Y-%m-%d %H:%M:%S"):
	#load the .TXT file as a JSON structure. feeds are in a list called "feeds"
	
	#the unparsed JSON data - check it for missing info immediatly
	feedJSON = loadJSON(filePath)
	feedJSON = JSONDataFaultCheck(feedJSON)
	
	#a list of parsed feeds. Will NOT contain any data from the JSON
	parsedFeeds = []
	
	#parse the urls in the json structure as feeds
	for index, feedData in enumerate(feedJSON["feeds"]):
		print("parsing feed %i/%i  "  % \
			(index + 1,len(feedJSON["feeds"])), end="\r")
		
		#check feedData
		feedData = feedDataFaultCheck(feedData)
		
		#parse the feed - feedparser can accept bad urls
		#this step takes a little while.
		parsedFeed = feedparser.parse(feedData["url"])
		
		if parsedFeed.version == "": #implies invalid feed URL (not a feed)
			logging.warning("Provided URL is not a feed! INDEX: %i", index)
			parsedFeed = None
		else: #update the data stored in the JSON file from the parsed feed
			feedData = updateFeedData(feedData, parsedFeed)

		parsedFeeds.append(parsedFeed)
	#--- end of for loop ---------------------------------------------------<<<
	print("\nfeeds parsed!")

	#return a tuple of the json list and the parsed feed list
	return(feedJSON, parsedFeeds)
#*** END OF loadFeeds() *******************************************************


def saveJSON(filePath, JSON):
	#dumps list "JSON" into a .TXT as a json structure
	
	#sort the list of feed data by class (may comment out as needed)
	#JSON["feeds"] = sortJSONFeedListByClass(JSON["feeds"])
	with open(filePath, 'w') as store:
		json.dump(JSON,store, sort_keys=True, indent=4, separators=(',', ': '))
#*** END OF saveJSON() ********************************************************


#--- GETTING DATA ----------------------------------------------------------<<<

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


def getClass(feedData):
	return feedData["class"]
#*** END OF getClass() ********************************************************


def getFeedList(filePath):
	#doesn't return actual feed dictionary - just the JSON stuff
	return loadJSON(filePath)["feeds"]
#*** END OF getFeedList() *****************************************************


#--- ORGANIZING/CHECKING DATA ----------------------------------------------<<<
def JSONDataFaultCheck(JSON):
	#check for just the main JSON stuff (last time run, ect)
	#Feed-specific data is checked in feedDataFaultCheck
	
	#check that the feeds list exists and that it is indeed a list.
	if not "feeds" in JSON:
		logging.warning("feeds missing!")
		JSON["feeds"] = []

	elif not type(JSON["feeds"]) == list:
		logging.warning("feeds not of type list!")
		JSON["feeds"] = []
	#--------------------------------------------------------------------------

	if not "lastCheck" in JSON: #last time a check was run
		JSON["lastCheck"] = "1970-01-01 00:00:00"

	if not "lastNotify" in JSON: #last time a notification was sent
		JSON["lastNotify"] = "1970-01-01 00:00:00"

	if not "lastDaily" in JSON: #last time a daily notification was sent
		JSON["lastDaily"] = "1970-01-01 00:00:00"

	if not "lastWeekly" in JSON: #last time a weekly notification was sent
		JSON["lastWeekly"] = "1970-01-01 00:00:00"
		
	return JSON
#*** END OF JSONDataFaultCheck() **********************************************


def feedDataFaultCheck(feedData):
	#checks each feed's data for missing elements
	#returns feedData(modified)
	
	if not "url" in feedData: #check for feed url
		feedData["url"] = ""

	if not "url-home" in feedData: #check for home url
		feedData["url-home"] = ""

	if not "latestTimeStamp" in feedData: #check for the timestamp
		feedData["latestTimeStamp"] = "1970-01-01 00:00:00"

	if not "title" in feedData: #check for the feed's title
		feedData["title"] = ""
		#"title" will be set later when the feed is parsed.

	if not "class" in feedData: #check for the feed's class
		feedData["class"] = "" 

	if not "urgency" in feedData: #check for the feed's urgency
		feedData["urgency"] = 1
		#possible urgencies: 0=immediate; 1=daily; 2=weekly
		
	return feedData
#*** END OF feedDataFaultCheck() **********************************************


def sortJSONFeedListByClass(feedJSON):
	return sorted(feedJSON, key=getClass)
#*** END OF sortJSONFeedListByClass() *****************************************


def rewriteTimestamps(feedJSON, newDate="1970-01-01 00:00:00"):
	#overwrites all the feed timestamps in the .TXT json structure
	#handy if you've been testing and missed an update
	for feedData in feedJSON["feeds"]:
		feedData["latestTimeStamp"] = newDate
	return feedJSON
#*** END OF rewriteTimestamps() ***********************************************


def updateFeedData(feedData, parsedFeed):
	#updates a few things by pulling from the parsed feed.
	
	#check that parsedFeed is not None
	if parsedFeed is None:
		return feedData
		
	#update the feed title every time
	if "title" in parsedFeed.feed:
		feedData["title"] = parsedFeed.feed.title
	
	#if a home URL isn't saved, get one from the feed.
	if feedData["url-home"] == "" and "link" in parsedFeed.feed:
		feedData["url-home"] = parsedFeed.feed.link
	return feedData
#*** END OF updateFeedData() **************************************************


#this allows the program to run on it's own. If the file is imported, then 
#__name__ will be the module's name.
if __name__ == "__main__":
	main()
