''' ~*~{O}~*~
	RSSMonitor.py
	Author: Taylor Smith
	Comment: 
		A utility to check RSS feeds. Uses a json file (feeds.txt) to keep
		track of last check and feed URLs. You can edit the json to add new
		feeds or remove old ones.
		
	NOTE: In the code, keeping the parsed JSON and the parsed feeds separate
		makes saving the JSON data MUCH easier.
	
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


def getFeedList(filePath):
	#doesn't return actual feed dictionary - just the JSON stuff
	feedJSON = loadJSON(filePath)
	return feedJSON["feeds"]
#*** END OF getFeedList() *****************************************************


def loadFeeds(filePath, datetimeFormat="%Y-%m-%d %H:%M:%S"):
	#load the .TXT file as a JSON structure. feeds are in a list called "feeds"
	
	#the unparsed JSON data - check it for missing info immediatly
	newjson = loadJSON(filePath)
	newjson = JSONDataFaultCheck(newjson)
	
	# a list of parsed feeds. Will NOT contain any data from the JSON
	#contains dictionaries of the parsed feeds and respective timestamps
	parsedFeeds = []
	
	#parse the urls in the json structure as feeds
	for index, data in enumerate(newjson["feeds"]):
		#check feed data
		data, urlPresent = feedDataFaultCheck(data, index)
		
		if not urlPresent: #parse ONLY if a url was detected
			parsedFeed = None
		else:
			parsedFeed = feedparser.parse(data["url"])
	
			#add to list of dictionaries {parsed feed, timestamp}
		parsedFeeds.append({"feed":parsedFeed, "latestDatetime":\
			datetime.strptime(data["latestTimeStamp"], datetimeFormat)})
			
		data = updateFeedData(data, parsedFeeds[index]["feed"])
	#--- end of for loop --------------------------------------------------

	#return a tuple of the json list and the parsed feed list
	return(newjson, parsedFeeds)
#*** END OF loadFeeds() *******************************************************


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


def feedDataFaultCheck(feedData, index=-1):
	#checks each feed's data for missing elements
	#returns feedData(modified) as well as a boolean which confirms the url
	urlPresent = True
	if not "url" in feedData or feedData["url"] == "": #check for feed url
		logging.warning("feed missing URL! INDEX: %i", index)
		feedData["url"] = ""
		urlPresent = False #no point in loading it if we don't have a URL

	if not "url-home" in feedData: #check for home url
		feedData["url-home"] = "$$$$$"

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
		
	return feedData, urlPresent
#*** END OF feedDataFaultCheck() **********************************************


def updateFeedData(feedData, parsedFeed):
	#updates a few things by pulling from the parsed feed.
	
	#check that parsedFeed is not None
	if parsedFeed is None:
		return feedData
		
	#update the feed title every time
	feedData["title"] = parsedFeed.feed.title
	
	#if a home URL isn't saved, get one from the feed.
	if feedData["url-home"] == "":
		feedData["url-home"] = parsedFeed.feed.link
	return feedData
#*** END OF updateFeedData() **************************************************


def saveJSON(filePath, JSON):
	#dumps list "JSON" into a .TXT as a json structure
	
	#sort the list of feed data by class (may comment out as needed)
	#JSON["feeds"] = sortJSONFeedListByClass(JSON["feeds"])
	with open(filePath, 'w') as store:
		json.dump(JSON,store, sort_keys=True, indent=4, separators=(',', ': '))
#*** END OF saveJSON() ********************************************************


def checkFeeds(filePath="", urgency=-1):
	#--- SETUP ----------------------------------------------------------------
	#configure the format which time is loaded/saved in.
	#CAUTION! Changing this might cause issues with parsing the time.
	datetimeFormat = "%Y-%m-%d %H:%M:%S"
	
	#make sure that you have a path. by default filePath = ""
	#if filePath is still "", set it to feeds.txt in the program's folder
	if filePath == "":
		filePath = path.dirname(__file__) + "\\feeds.txt"
	
	startDatetime = datetime.now()
	totalTally = 0
	heading = "" 		#contains totalTally, summary of all feeds
	fullSummary = ""	#contains individual feed summaries
	results = [] 		#contains all the new entry names

	#open the JSON file
	feedJSON, parsedFeeds = loadFeeds(filePath, datetimeFormat)

	#--- MAIN CODE ------------------------------------------------------------
	logging.info("Last checked at " + str(feedJSON["lastCheck"]) + \
	",\nnow checking at " + str(startDatetime))

	#loop through each feed, building a list of new entries
	for index, pair in enumerate(parsedFeeds):
		#check that parsedFeeds is not None
		if pair["feed"] is None:
			logging.warning("Feed skipped: %i" % index)
			continue
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

		#Contextual output! total number of entries effects the main summary
		if totalTally == 0:
			heading = "There are no new entries in any of your feeds.\n"
		elif totalTally == 1:
			heading = "There is 1 new entry in all your feeds.\n"
		else:
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

	#Feed summary formatting. 
	if counter == 0:
		#don't return anything if nothing is new
		pass
	else:
		feedSummary = " } " + str(counter) + " new entries in " + \
		feed.feed.title + ".\n"

	feedText = feedText
	
	#return count, the two strings, and the most recent timestamp in a tuple
	return (counter, feedText, feedSummary, latestTimeStamp)
#*** END OF getNewEntries() ***************************************************


#this allows the program to run on it's own. If the file is imported, then 
#__name__ will be the module's name.
if __name__ == "__main__":
	main()
