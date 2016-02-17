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
		it's own timestamps.
	
	NOTE: put [chcp 65001] into CMD (sans brackets) to enter Unicode Mode

	TODO: try returning a list of dictionarys [feed : (sum, results string) as
		well as the total number.
	TODO: Add a timer when loading the feeds from the internet - 10s or so
	TODO: Add a date & time next to each entry when printing?
	TODO: Add exceptions
'''

import feedparser, time, json, logging, sys
from datetime import datetime
from os import path

def main():
	decorative = "=-=-=-=-=-=-=-=-=-=-=-=-=\n"
	
	logging.basicConfig(filename='rssMonitor.log', level = logging.DEBUG)
	logging.info(decorative + "\nStarting up")
	
	#use this if you need to go back a bit.
	revertFeedDates("2016-01-19 00:00:00")
	
	result = checkFeeds()
	
	#print total and summaries
	print(result[1] + result[2])
	
	#print results
	for string in result[3]:
		print(decorative + string)
	logging.info("all processes finished!")
#*** END OF MAIN **************************************************************


def scheduledCheck():
	#call this method when running a regular check.
	decorative = "=-=-^-=-=\n"
	
	logging.basicConfig(filename='rssMonitor.log', level = logging.WARNING)
	logging.warning("Starting up at " + str(datetime.now()))
	
	result = checkFeeds()
	if(result[0] == 0):
		#no new feeds. Return nothing.
		return ""
	
	finalString = (result[1] + result[2])
	for string in result[3]:
		finalString = finalString + decorative + string
#*** END OF scheduledCheck() **************************************************


def checkFeeds(filePath="", urgency=-1):
	#--- SETUP ----------------------------------------------------------------
	#configure the format which time is loaded/saved in.
	#CAUTION! Changing this might cause issues with parsing the time.
	datetimeFormat = "%Y-%m-%d %H:%M:%S"
	
	#make sure that you have a path. by default filePath = ""
	#if filePath is still "", set it to feeds.txt in the program's folder
	if filePath == "":
		filePath = path.dirname(path.realpath(__file__)) + "/feeds.txt"
	#ensure that the path is normalized.
	filePath = path.abspath(filePath)
	
	startDatetime = datetime.now()
	totalTally = 0
	heading = "" 		#contains totalTally, summary of all feeds
	fullSummary = ""	#contains individual feed summaries
	results = [] 		#contains all the new entry names

	try:
		#open the JSON file (it can take a few seconds to parse the feeds)
		feedJSON, parsedFeeds = loadFeeds(filePath, datetimeFormat)
	except: ValueError
		print("error in system - should print specific error")
		sys.exit()
	#--- MAIN CODE ------------------------------------------------------------
	logging.info("Last checked at " + str(feedJSON["lastCheck"]) + \
	",\nnow checking at " + str(startDatetime))

	#loop through each feed, building a list of new entries
	for index, parsedFeed in enumerate(parsedFeeds):
		print("checking feed %i/%i  "  % \
			(index + 1,len(feedJSON["feedsToCheck"])), end="\r")
			
		#check that parsedFeeds is not None
		if parsedFeed is None:
			logging.warning("Feed skipped: %i" % index)
			continue
		
		#get the target timestamp for this feed
		feedTargetTimestamp = datetime.strptime(\
			feedJSON["feedsToCheck"][index]["latestTimeStamp"], datetimeFormat)
		
		#get the feed's results in a tuple.
		#([0]counter, [1]feedSummary, [2]entryList, [3]feedLatestTimeStamp)
		feedResult = getNewEntries(parsedFeed, feedTargetTimestamp)
		
		#--- CLERICAL CODE ----------------------------------------------------
		#update totalTally
		totalTally = totalTally + feedResult[0]

		#if there were new items detected, add to summary and results.
		if feedResult[0] > 0:
			fullSummary = fullSummary + feedResult[1]#string
			results.append(feedResult[2])#list

		#store the PublishDate of the newest entry so we have it for next time
		feedJSON["feedsToCheck"][index]["latestTimeStamp"] = \
		datetime.strftime(feedResult[3], datetimeFormat)
	#--- END OF LOOP ----------------------------------------------------------
		
	#Contextual output! total number of entries effects the main summary
	if totalTally == 0:
		heading = "There are no new entries in any of your feeds.\n"
	elif totalTally == 1:
		heading = "There is 1 new entry in all your feeds.\n"
	else:
		heading = "There are %i new entries in all your feeds.\n" % totalTally

	#save the time we started in the JSON structure
	feedJSON["lastCheck"] = datetime.strftime(startDatetime, datetimeFormat)
	#and then save the JSON structure
	saveJSON(filePath, feedJSON)
		
	return (totalTally, heading, fullSummary, results)
#*** END OF checkFeeds() ******************************************************


def getNewEntries(parsedFeed, targetDatetime):
	#accepts a feed object and a datetime object to compare, returns a tuple
	#containing the number of new elements, a string of text representing those
	#elements and a summary string.
	
	#--- SETUP ----------------------------------------------------------------
	#keep track of the number of new entries
	counter = 0
	
	#holds the text output of this function.
	feedSummary = ""
	entryList = parsedFeed.feed.title + "\n"
	
	#check that entries exist really quick.
	if len(parsedFeed.entries) == 0:
		#No entries. I've run into this once. Not good for code.
		return (counter, feedSummary, entryList, targetDatetime)
		
	#get the feed's most recent timestamp, will be returned.
	tempUpdateTime = ""
	#sometimes feeds don't use 'updated_parsed'. This Try helps.
	try:
		tempUpdateTime = parsedFeed.entries[0].updated_parsed
	except AttributeError:
		logging.warning("'updated_parsed' doesn't exist for Feed: %s\n\t \
			Using 'published_parsed' instead" % parsedFeed.feed.title)
		tempUpdateTime = parsedFeed.entries[0].published_parsed
	
	feedLatestTimeStamp = \
	datetime.fromtimestamp(time.mktime(tempUpdateTime))
	#note that I convert 'time_struct' to 'datetime'

	#--- MAIN CODE ------------------------------------------------------------
	logging.debug("Checking " + parsedFeed.feed.title)
	
	#TODO:find a way for "ignore" to work
	
	#Go through entries until you hit an old one.
	for entry in parsedFeed.entries:
		#get the entry's timestamp
		entryTimeStamp = entry.updated_parsed
		#feedparser parses time as 'time_struct', convert to 'datetime'
		entryDatetime = datetime.fromtimestamp(time.mktime(entryTimeStamp))
		
		#Check to see if entry is new.
		if entryDatetime > targetDatetime:
			#if so, add the entry to the end of the main list.
			entryList = entryList + entry.title + "\n"
			counter = counter + 1
		else:
			break

	#Feed summary formatting. 
	if counter == 0:
		#don't return anything if nothing is new
		pass
	elif counter == 1:
		feedSummary = " > 1 new entry in %s.\n" % parsedFeed.feed.title
	else:
		feedSummary = " > %i new entries in %s.\n" %(counter, parsedFeed.feed.title)
	
	logging.debug("\tDone with " + parsedFeed.feed.title)
	#return count, the two strings, and the most recent timestamp in a tuple
	return (counter, feedSummary, entryList, feedLatestTimeStamp)
#*** END OF getNewEntries() ***************************************************


def revertFeedDates(newDate="1970-01-01 00:00:00",filePath=""):
#--- SETUP ----------------------------------------------------------------
	#configure the format which time is loaded/saved in.
	#CAUTION! Changing this might cause issues with parsing the time.
	datetimeFormat = "%Y-%m-%d %H:%M:%S"
	
	#make sure that you have a path. by default filePath = ""
	#if filePath is still "", set it to feeds.txt in the program's folder
	if filePath == "":
		filePath = path.dirname(path.realpath(__file__)) + "/feeds.txt"
	#ensure that the path is normalized.
	filePath = path.abspath(filePath)
	
	
	#open the JSON file (it can take a few seconds to parse the feeds)
	feedJSON = loadJSON(filePath)
	
	#reset timestamps in the JSON.
	rewriteTimestamps(feedJSON, newDate)
	logging.info("timestamps reverted to %s." % newDate)

	#save the JSON structure
	saveJSON(filePath, feedJSON)
#*** END OF checkFeeds() ******************************************************

#--- LOADING/SAVING DATA ---------------------------------------------------<<<
def loadJSON(filePath):
	#This function is used to load the feeds.TXT file as a JSON structure
	#the following line is a JSON structure which is loaded in the case of an error. Very basic.
	defaultJSON = '{"feedsToCheck":[], "lastCheck":"1970-01-01 00:00:00", "1ERROR":"!defaultJSON used!"}'
	
	#write another try/catch: FileNotFoundError
	with open(filePath, 'r') as store:
		try:
			loadedJSON = json.load(store)
		except ValueError:
			#throw another error. TODO: throw different errors if JSON is invalid or file is missing
			raise RuntimeError("Failed to load JSON from .txt file!")
			#logging.error("Invalid json file! Loading fake JSON; Check your JSON!")
			#loadedJSON = json.loads(defaultJSON)
	return loadedJSON
#*** END OF loadJSON() ********************************************************


def loadFeeds(filePath, datetimeFormat="%Y-%m-%d %H:%M:%S"):
	#load the .TXT file as a JSON structure. feeds are in a list called "feeds"
	
	#the unparsed JSON data - check it for missing info immediatly
	feedJSON = loadJSON(filePath)
	feedJSON = JSONDataFaultCheck(feedJSON)
	
	#a list of parsed feeds. Will NOT contain any data from the JSON
	parsedFeeds = []
	
	#parse the urls in the json structure as feeds
	for index, feedData in enumerate(feedJSON["feedsToCheck"]):
		print("parsing feed %i/%i  "  %\
			(index + 1,len(feedJSON["feedsToCheck"])), end="\r")
		
		#check feedData
		feedData = feedDataFaultCheck(feedData)
		
		#parse the feed - feedparser can accept bad urls
		#this step takes a little while.
		parsedFeed = feedparser.parse(feedData["url"])
		
		if parsedFeed.version == "": #implies invalid feed URL (not a feed)
			logging.warning("Target URL is not a feed! INDEX: %i\n\t%s" % (index,feedData["url"]))
			parsedFeed = None
		else: #update the data stored in the JSON file from the parsed feed
			feedData = updateFeedData(feedData, parsedFeed)

		parsedFeeds.append(parsedFeed)
	#--- end of for loop ---------------------------------------------------<<<
	logging.info("%i feeds parsed!" %len(feedJSON["feedsToCheck"]))

	#return a tuple of the json list and the parsed feed list
	return(feedJSON, parsedFeeds)
#*** END OF loadFeeds() *******************************************************


def saveJSON(filePath, JSON):
	#dumps list "JSON" into a .TXT as a json structure
	
	#sort the list of feed data by class (may comment out as needed)
	#JSON["feedsToCheck"] = sortJSONFeedListByClass(JSON["feedsToCheck"])
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
	return loadJSON(filePath)["feedsToCheck"]
#*** END OF getFeedList() *****************************************************


#--- ORGANIZING/CHECKING DATA ----------------------------------------------<<<
def JSONDataFaultCheck(JSON):
	#check for just the main JSON stuff (last time run, ect)
	#Feed-specific data is checked in feedDataFaultCheck
	
	#check that the feeds list exists and that it is indeed a list.
	if not "feedsToCheck" in JSON:
		logging.warning("'feedsToCheck' missing from feeds.txt!")
		raise ValueError("No list of feeds to check!")
		#JSON["feedsToCheck"] = []

	elif not type(JSON["feedsToCheck"]) == list:
		logging.warning("'feedsToCheck' not of type list!")
		raise ValueError("THe list of feeds to check is not a list!")
		#JSON["feedsToCheck"] = []
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
	for feedData in feedJSON["feedsToCheck"]:
		feedData["latestTimeStamp"] = newDate
		#overwriting is ok because the code will always store the feed's latest
		#timestamp even if it's older than the current "latestTimeStamp", i. e.
		#things will sort themselves out next time you run the script.
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
