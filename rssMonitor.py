''' ~*~{O}~*~
	rssMonitor.py
	Author: Taylor Smith
	Comment: 
		A utility to check RSS feeds. Uses a json file (feeds.txt) to keep
		track of last check and feed URLs. You can edit the txt file to add new
		feeds or remove old ones.
	
	NAMING CONVENTIONS:
		feedJSON: the dictionary of data about feeds & some metadata stored in
			the feeds.txt file.
		feedList: the list of feed data in feedJSON, accessable at 
			feedJSON["feedList"]
		feedData: one of the dictionarys in feedList, accessable at
			feedJSON["feedList"][index]
		parsedFeeds: the list of parsed feeds returned fom feedparser.
		parsedFeed: data from a single parsed feed, accessable at 
			parsedFeeds[index]. index is the same between feedData and 
			parsedFeed.
		
	NOTE: In the code, keeping the parsed JSON and the parsed feeds in separate
		structures makes saving the JSON data MUCH easier.
		
	NOTE: DO NOT USE "lastCheck" FOR TIMESTAMP COMPARRISONS!!! You don't know
		what time zone the feed comes from. It is better to compare it with
		its own timestamps.
	
	NOTE: put [chcp 65001] into CMD (sans brackets) to enter Unicode Mode

	TODO: Add a timer when loading the feeds from the internet - 10s or so
	TODO: Add a date & time next to each entry when printing?
	TODO: Create custom errors
	TODO: use a function to protect from attribute errors when getting things
		from a parsed feed
'''

import feedparser, time, json, logging, sys
from datetime import datetime
from os import path

def main():
	decorative = "=-=-=-=-=-=-=-=-=-=-=-=-=\n"
	
	logging.basicConfig(filename='rssMonitor.log', level = logging.DEBUG)
	logging.info(decorative + "\nStarting up")
	
	#use this if you need to go back a bit. Note that it won't effect entry
	#titles if you have to use those for comparison.
	#revertFeedDates("2016-03-08 00:00:00")
	
	try:
		result = checkFeeds()
	except RuntimeError as error:
		print("\nFatal Error: %s" % error)
		logging.critical("Fatal Error: %s" % error)
	else:
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
	logging.warning("Starting up at %s" % str(datetime.now()))
	
	try:
		result = checkFeeds()
	except RuntimeError as error:
		return ("Fatal Error: %s" % error)
		logging.critical("Fatal Error: %s" % error)
	else:
		if(result[0] == 0):
			#no new feeds. Return nothing.
			return ""
		
		finalString = (result[1] + result[2])
		for string in result[3]:
			finalString = finalString + decorative + string
#*** END OF scheduledCheck() **************************************************


def checkFeeds(filePath="", entryCap=0, urgency=-1):
	#you are responsible for catching thrown errors.
	#checkFeeds should only throw RuntimeError's
	#--- SETUP ----------------------------------------------------------------
	#configure the format which time is loaded/saved in.
	#CAUTION! Changing this might (will) cause issues with parsing the time.
	datetimeFormat = "%Y-%m-%d %H:%M:%S"
	
	#make sure that you have a path. by default filePath = ""
	#if filePath is still "", set it to feeds.txt in the program's folder
	if filePath == "":
		filePath = path.dirname(path.realpath(__file__)) + "/feeds.txt"
	#ensure that the path is normalized.
	filePath = path.abspath(filePath)
		
	totalTally = 0
	heading = "" 		#contains totalTally, summary of all feeds
	fullSummary = ""	#contains individual feed summaries
	results = [] 		#contains all the new entry names

	#open the JSON file (it can take a few seconds to parse the feeds)
	feedJSON, parsedFeeds = loadFeeds(filePath)
			
	#with feedList, I can only modify objects in its array, not the array
	#itself. This makes code more readable.
	feedList = feedJSON["feedList"]
		
	#go ahead and set the start time and note it in the log
	startDatetime = trimNow_ms()
	logging.info("Last checked at [%s],\n\tnow checking at [%s]" % \
		(feedJSON["lastCheck"],str(startDatetime)))
	#--- MAIN CODE ------------------------------------------------------------
	#loop through each parsedFeed, building a list of new entries
	for index, parsedFeed in enumerate(parsedFeeds):
		print("checking feed %i/%i  "  % \
			(index + 1,len(feedJSON["feedList"])), end="\r")

		try:
			#get the feed's results in a tuple.
			#([0]counter, [1]feedSummary, [2]entryList)
			feedResult = getFeedEntries(parsedFeed, feedList[index], 5)
		except SyntaxError:
			logging.error("Feed [%i]:[%s] probably has an invalid URL." % \
			(index, feedList[index]["url"]))
		except ValueError:
			logging.error("Feed [%i] has no entries (code doesn't handle that \
			well" % index)
		else:
			#--- CLERICAL CODE - Can't run if try fails! ----------------------
			#update totalTally
			totalTally = totalTally + feedResult[0]

			#if there were new items detected, add to summary and results.
			if feedResult[0] > 0:
				fullSummary = fullSummary + feedResult[1]#string
				results.append(feedResult[2])#list
		#--- END OF TRY -------------------------------------------------------
	
		try:
			#get the feed's most recent timestamp
			newTimestamp = str(timeToDt(parsedFeed.entries[0].updated_parsed))
			#feedparser uses time_struct, I want a string.
			#store the timestamp for next time.
			feedList[index]["latestTimeStamp"] = newTimestamp
		except AttributeError:
			#if there's no attribute "updated_parsed", delete "latestTimeStamp"
			#if it exists (if it doesn't, None is returned by pop.)
			feedList[index].pop("latestTimeStamp",None)
		
		#also store the title of the newest entry
		feedList[index]["latestEntryTitle"] = \
		parsedFeed.entries[0].title
			
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
	saveFeedJSON(filePath, feedJSON)
		
	return (totalTally, heading, fullSummary, results)
#*** END OF checkFeeds() ******************************************************

def getFeedEntries(parsedFeed, feedData, entryCap):
	#accepts a feed object and a datetime object to compare, returns a tuple
	#containing the number of new elements, a string of text representing those
	#elements and a summary string.
	
	#--- ERROR CHECK ----------------------------------------------------------
	#quick, check that the feed is valid first!
	if parsedFeed.version == "": #implies invalid feed URL (not a feed)
		raise SyntaxError("parsedFeed is not a feed!")
	
	#check that entries exist really quick.
	if len(parsedFeed.entries) == 0:
		#No entries. I've run into this once. Not good for code.
		raise ValueError("no entries in the feed!")
	
	#--- MAIN CODE ------------------------------------------------------------
	logging.debug("Checking " + parsedFeed.feed.title)
	entryResult = ""
	
	#If I haven't got a timestamp for the feed, I can just use the entry title.
	# If I haven't got that either, I can just return all the entries. Easy.
	if "latestTimeStamp" in feedData:
		entryResult = getNewEntries(parsedFeed, feedData["latestTimeStamp"], \
			True, entryCap)
	elif "latestEntryTitle" in feedData:
		logging.error("Issue with timestamp!\tusing entry title instead.")
		entryResult = getNewEntries(parsedFeed, feedData["latestEntryTitle"], \
			False, entryCap)
	else:
		logging.error("Issue with timestamp and entry title! \
		\tCalling getAllEntries().")
		entryResult = getAllEntries(parsedFeed, entryCap)

	#--- FINISHING UP ---------------------------------------------------------
	#entryResult = ([0] count, [1] entryList)
	#produce the feed summary.
	feedSummary = getFeedSummary(entryResult[0], parsedFeed.feed.title)

	#add title to list
	entryList = parsedFeed.feed.title + "\n" + entryResult[1]
	#add a note if the total number of entries is over the cap.
	if(entryResult[0] > entryCap):
		entryList = "%s -> And %i more!\n" % (entryList, entryResult[0] - entryCap)
	
	#return count, the two strings, and the most recent timestamp in a tuple
	return (entryResult[0], feedSummary, entryList)
#*** END OF getFeedEntries() **************************************************


def getNewEntries(parsedFeed, compareString, isTimestamp, entryCap):
	#takes a feed object and a string to compare. isTimestamp tells the loop if
	#it should treat compareString as a timestamp or an entry title. Returns a
	#tuple with the total number of new entires and a string with their titles.
	# (number of titles) = max(number of entries, entryCap)
	#--- SETUP ----------------------------------------------------------------
	#keep track of the number of new entries
	counter = 0
	#holds the text output of this function.
	entryList = ""
	#temporary boolean value to hold the comparison result.
	isNew = False
	#--- MAIN CODE ------------------------------------------------------------
	#Go through entries until you hit an old one.
	for entry in parsedFeed.entries:
		#test the entry based on isTimestamp
		if isTimestamp:
			isNew = (timeToStr(entry.updated_parsed) > compareString)
		else:
			isNew = (entry.title != compareString)
		
		#Check to see if the entry is new.
		if isNew:
			counter = counter + 1
			if counter <= entryCap:
				#add the entry's title to the end of the main list.
				entryList = entryList + entry.title + "\n"
		else:
			break
	return (counter, entryList)
#*** END OF getNewEntries() ***************************************************


def getAllEntries(parsedFeed, entryCap):
	#like getNewEntries(), but doesn't bother checking entries' timestamps
	#--- SETUP ----------------------------------------------------------------
	#keep track of the total number of entries
	counter = 0
	#variable to hold the text output of this function.
	entryList = "-< All Entries >-\n"

	#--- MAIN CODE ------------------------------------------------------------
	#Go through all entries.
	for entry in parsedFeed.entries:
		counter = counter + 1
		#we need to know how many new entries there are, but stop adding on
		#their titles if we're past entryCap.
		if counter <= entryCap:
			#add the entry's title to the end of the main list.
			entryList = entryList + entry.title + "\n"
	return (counter, entryList)
#*** END OF getAllEntries() ***************************************************


def getFeedSummary(count, title):
#Feed summary formatting.
	if count == 0:
		#don't return anything if there wasn't anything to begin with.
		return ""
	elif count == 1:
		return (" > 1 new entry in %s.\n" % title)
	else:
		return (" > %i new entries in %s.\n" % (count, title))
#*** END OF getFeedSummary() **************************************************


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
	saveFeedJSON(filePath, feedJSON)
#*** END OF checkFeeds() ******************************************************

#>>> LOADING/SAVING DATA <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
def loadFeeds(filePath):
	#load the .TXT file as a JSON structure into feedJSON, then parses the 
	#feeds via feedparser into parsedFeeds. Returns a tuple.
	
	#the unparsed JSON data - check it for missing info immediatly
	feedJSON = loadJSON(filePath)
	feedJSON = JSONDataFaultCheck(feedJSON)
	
	#a list of parsed feeds. Will NOT contain any data from the JSON
	parsedFeeds = []
	
	#parse the urls in the json structure as feeds
	for index, feedData in enumerate(feedJSON["feedList"]):
		#print a progress counter. It overwrites itself as the count goes up.
		#I'm kinda proud of this one. :)
		print("parsing feed %i/%i  "  %\
			(index + 1,len(feedJSON["feedList"])), end="\r")
		
		#check feedData for missing info (ie. the URL) before parseing the feed
		feedData = feedDataFaultCheck(feedData)
		
		#parse the feed - feedparser can handle bad urls, it 
		#this step takes a little while.
		parsedFeed = feedparser.parse(feedData["url"])
		
		#parsedFeed should ALWAYS have version as an attribute
		if parsedFeed.version == "": #implies invalid feed URL (not a feed)
			#the following includes index and the url.
			logging.warning("Target URL is not a feed! INDEX: %i\n\t%s" % (index,feedData["url"]))
			#not the time for an error. This is checked again in "getNewEntries()"
			#raise RuntimeError("[%s] is not an actual feed." % feedData["url"])
		else: #update the data stored in the JSON file from the parsed feed
			feedData = updateFeedData(feedData, parsedFeed)

		parsedFeeds.append(parsedFeed)
	#--- END OF FOR LOOP ------------------------------------------------------
	logging.info("%i feeds parsed!" %len(feedJSON["feedList"]))

	#return a tuple of the json list and the parsed feed list
	return(feedJSON, parsedFeeds)
#*** END OF loadFeeds() *******************************************************


def loadJSON(filePath):
	#This function is used to load the feeds.TXT file as a JSON structure.
	#It will throw an error if it cannot load the file.
	
	#write another try/catch: FileNotFoundError
	try:
		with open(filePath, 'r') as store:
			feedJSON = json.load(store)
	except FileNotFoundError:
		raise RuntimeError("Couldn't find feeds.txt!")
	except ValueError as error:
		raise RuntimeError("Bad JSON: %s" % str(error))
	else:
		return feedJSON
#*** END OF loadJSON() ********************************************************


def saveFeedJSON(filePath, feedJSON):
	#dumps feedJSON into a .TXT as a json structure
	
	#sort the list of feed data by class (may comment out as needed)
	#feedJSON["feedList"] = sortJSONFeedListByClass(feedJSON["feedList"])
	with open(filePath, 'w') as store:
		json.dump(feedJSON,store, sort_keys=True, indent=4, separators=(',', ': '))
#*** END OF saveFeedJSON() ********************************************************


#>>> FUDGING WITH TIME & DATETIME <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
def trimNow_ms():
	#easily get now() without microseconds
	return trimDatetime_ms(datetime.now())
#*** END OF truncatedNow() ****************************************************

def trimDatetime_ms(dt):
	#easily remove microseconds from any datetime
	return datetime(dt.year,dt.month,dt.day,dt.hour, dt.minute, dt.second)
	#dt.replace(microsecond = 0)
#*** END OF trimDatetime_ms() *************************************************

def strToDt(str):
	#easily convert string  with standard format to datetime.
	#May throw ValueError.
	return datetime.strptime(str, "%Y-%m-%d %H:%M:%S")
#*** END OF strToDt() *********************************************************

def timeToDt(t):
	#easily convert time to datetime
	return datetime.fromtimestamp(time.mktime(t))
#*** END OF timeToDt() ********************************************************

def dtToTime(t):
	#easily convert datetime to time if you don't care about sub-seconds
	return time.mktime(dt_obj.timetuple())
#*** END OF dtToTime() ********************************************************

def timeToStr(t):
	#easily convert time to string with standard format
	return time.strftime("%Y-%m-%d %H:%M:%S", t)
#*** END OF timeToStr() *******************************************************


#>>> GETTING DATA <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
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


def getFeedClass(feedData):
	return feedData["class"]
#*** END OF getFeedClass() ****************************************************

def getFeedTitle(feedData):
	return feedData["title"]
#*** END OF getFeedTitle() ****************************************************

def getFeedList(filePath):
	#doesn't return all of feedJSON - just feedList
	return loadJSON(filePath)["feedList"]
#*** END OF getFeedList() *****************************************************


#>>> ORGANIZING/CHECKING DATA <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
def JSONDataFaultCheck(feedJSON):
	#check for just the main JSON stuff (last time run, ect)
	#Feed-specific data is checked in feedDataFaultCheck
	
	#check that the feeds list exists and that it is indeed a list.
	if not "feedList" in feedJSON:
		logging.warning("'feedList' missing from feeds.txt!")
		raise RuntimeError("No list of feeds to check!")

	elif not type(feedJSON["feedList"]) == list:
		logging.warning("'feedList' is not of type list!")
		raise RuntimeError("Bad feedJSON: the list of feeds to check is not a list!")
	#--------------------------------------------------------------------------

	if not "lastCheck" in feedJSON: #last time a check was run
		feedJSON["lastCheck"] = "1970-01-01 00:00:00"

	if not "lastNotify" in feedJSON: #last time a notification was sent
		feedJSON["lastNotify"] = "1970-01-01 00:00:00"

	if not "lastDaily" in feedJSON: #last time a daily notification was sent
		feedJSON["lastDaily"] = "1970-01-01 00:00:00"

	if not "lastWeekly" in feedJSON: #last time a weekly notification was sent
		feedJSON["lastWeekly"] = "1970-01-01 00:00:00"
		
	return feedJSON
#*** END OF JSONDataFaultCheck() **********************************************


def feedDataFaultCheck(feedData):
	#checks each feed's data for missing elements and adds them if needed.
	#returns feedData(modified)
	
	if not "url" in feedData: #check for feed url
		feedData["url"] = ""

	if not "url-home" in feedData: #check for home url
		feedData["url-home"] = ""

	#if there is no timestamp to compare to, getNewEntries() will return all
	#available entries (to a point) and set this to the newest entry's time.
	#if not "latestTimeStamp" in feedData: #check for the last timestamp
	#	feedData["latestTimeStamp"] = "1970-01-01 00:00:00"
	
	#same as previous
	#if not "latestEntryTitle" in feedData: #check for the last entry title
	#	feedData["latestEntryTitle"] = ""

	if not "title" in feedData: #check for the feed's title
		feedData["title"] = ""
		#"title" will be set later when the feed is parsed.

	if not "class" in feedData: #check for the feed's class
		feedData["class"] = "" 

	if not "urgency" in feedData: #check for the feed's urgency
		feedData["urgency"] = 1
		#possible urgencies: 0=immediate; 1=daily; 2=weekly
		#not yet implemented...
		
	return feedData
#*** END OF feedDataFaultCheck() **********************************************


def updateFeedData(feedData, parsedFeed):
	#updates a few things by pulling from the parsed feed.
	#assumes that these items are present in parsedFeed.
	#might add a try-except to protect against needless crashes

	#update the feed title every time
	if "title" in parsedFeed.feed:
		feedData["title"] = parsedFeed.feed.title
	
	#if a home URL isn't saved, get one from the feed.
	if feedData["url-home"] == "" and "link" in parsedFeed.feed:
		feedData["url-home"] = parsedFeed.feed.link
	return feedData
#*** END OF updateFeedData() **************************************************


def sortJSONFeedListByClass(feedJSON):
	return sorted(feedJSON, key=getFeedClass)
#*** END OF sortJSONFeedListByClass() *****************************************


def rewriteTimestamps(feedJSON, newDate="1970-01-01 00:00:00"):
	#overwrites all the feed timestamps in the .TXT json structure
	#handy if you've been testing and missed an update
	for feedData in feedJSON["feedList"]:
		#if a feed doesn't have a timestamp, I don't want one.
		if "latestTimeStamp" in feedData:
			feedData["latestTimeStamp"] = newDate
		#overwriting is ok because the code will always store the feed's latest
		#timestamp even if it's older than the current "latestTimeStamp", i. e.
		#things will sort themselves out next time you run the script.
	return feedJSON
#*** END OF rewriteTimestamps() ***********************************************


#this allows the program to run on it's own. If the file is imported, then 
#__name__ will be the module's name.
if __name__ == "__main__":
	main()
