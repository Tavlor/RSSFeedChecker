''' ~*~{O}~*~
	RSSMonitor.py
	Author: Taylor Smith
	Description: A utility which monitors your rss feeds and notifies you when
	they are updated. Uses a json file to keep track of last check and feed 
	URLs. You can edit this to add new feeds or remove old ones.
	
	TODO: allow program to accept date range as an argument to check for 
	releases in that range.
	TODO: threading
	TODO: allow user to request just a summary or the entire thing.
	TODO: colored text output: use CURSES?
	TODO: does this take timezones into account?
	TODO: add error safety around the JSON file.
'''

import feedparser, time, json
from datetime import datetime

def main():
	'''#*** SETUP ****************************************************************
	print(" -- STARTING")
	#load the previous timestamps & hyperlinks.
	feedStorePath = r"G:/Python/Code/feeds.txt"
	with open(feedStorePath, 'r') as feedStore:
		feedJSON = json.load(feedStore)
	#configure the format which time is loaded/saved in.
	#CAUTION! Changing this might cause issues with parsing the time.
	datetimeFormat = "%Y-%m-%d %H:%M:%S"
	startCheckTime = datetime.now()
	#FIXME: this loads as string; convert it to time or datetime
	lastCheck = datetime.strptime(feedJSON["lastCheck"], datetimeFormat)
	#for absolute time, use datetime(2015,9,1,0,0)
	linkList = feedJSON["feeds"]
	feedList = []
	grandCounter = 0
	grandSummary =	"=-= SUMMARY =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n"
	grandText =		"=-= RESULTS =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n"
	decorative =	"=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n"
	#this will be sent out via text/email. Build up of all output.
	message = ""
	
	#*** MAIN CODE ************************************************************
	print("Last checked at " + str(lastCheck) + ",\nnow checking at " \
		+ str(startCheckTime))
	#parse all the links into feed objects.
	for link in linkList:
		feedList.append(feedparser.parse(link))

	#loop through each feed, building a list of new entries
	for feed in feedList:
		feedResult = checkFeed(feed, lastCheck)
		grandCounter = grandCounter + feedResult[0]
		#if there were new items detected, add to grandText.
		if feedResult[0] > 0:
			grandText = grandText + feedResult[1] + decorative 
		grandSummary = grandSummary + feedResult[2]

	#build the message.
	message = "There are " + str(grandCounter) + \
		" new entries in all your feeds.\n" + grandSummary + grandText
	print(" __ Printing results...")
	print(message)
	
	#save the new check time in the JSON structure, then save the JSON.
	feedJSON["lastCheck"] = datetime.strftime(startCheckTime, datetimeFormat)
	with open(feedStorePath, 'w') as feedStore:
		json.dump(feedJSON,feedStore)
	#wait for the user to press enter
	input()'''
	print(checkFeedsInList())
#*** END OF MAIN **************************************************************

def checkFeedsInList():
	#*** SETUP ****************************************************************
	#load the previous timestamps & hyperlinks.
	feedStorePath = r"G:/Python/Code/feeds.txt"
	with open(feedStorePath, 'r') as feedStore:
		feedJSON = json.load(feedStore)
	#configure the format which time is loaded/saved in.
	#CAUTION! Changing this might cause issues with parsing the time.
	datetimeFormat = "%Y-%m-%d %H:%M:%S"
	startCheckTime = datetime.now()
	#FIXME: this loads as string; convert it to time or datetime
	lastCheck = datetime.strptime(feedJSON["lastCheck"], datetimeFormat)
	#for absolute time, use datetime(2015,9,1,0,0)
	linkList = feedJSON["feeds"]
	feedList = []
	grandCounter = 0
	grandSummary =	"=-= SUMMARY =-=-=-=\n"
	grandText =		"=-= RESULTS =-=-=-=\n"
	decorative =	"=-=-=-=-=-=-=-=-=-=\n"
	#this will be sent out via text/email. Build up of all output.
	message = ""
	
	#*** MAIN CODE ************************************************************
	print("Last checked at " + str(lastCheck) + ",\nnow checking at " \
		+ str(startCheckTime))
	#parse all the links into feed objects.
	for link in linkList:
		feedList.append(feedparser.parse(link))

	#loop through each feed, building a list of new entries
	for feed in feedList:
		feedResult = checkFeed(feed, lastCheck)
		grandCounter = grandCounter + feedResult[0]
		#if there were new items detected, add to grandText.
		if feedResult[0] > 0:
			grandText = grandText + feedResult[1] + decorative 
		grandSummary = grandSummary + feedResult[2]

	#build the message.
	message = "There are " + str(grandCounter) + \
		" new entries in all your feeds.\n" + grandSummary + grandText
	
	#save the new check time in the JSON structure, then save the JSON.
	feedJSON["lastCheck"] = datetime.strftime(startCheckTime, datetimeFormat)
	with open(feedStorePath, 'w') as feedStore:
		json.dump(feedJSON,feedStore)
	return(message)
#*** END OF checkFeedsInList() *************************************************
	
def checkFeed(feed, checkTime):
	#requires a feed object and the date to compare, returns a tuple containing
	#the number of new elements, a string of text representing those elements
	#and a summary string.

	#keep track of the number of new entries
	counter = 0
	#holds the text output of this function.
	feedSummary = ""
	feedText = feed.feed.title + "\n"
	
	#print(decorative)
	print(" __ Checking " + feed.feed.title)
	#print(datetime.datetime.fromtimestamp(mktime(snarlFeed.entries[0].updated_parsed)))
	
	#Go through entries until you hit an old one.
	for entry in feed.entries:
		feedTime = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
		#Check to see if entry is new.
		if checkTime <= feedTime:
			feedText = feedText + " + " + entry.title + "\n"
			counter = counter + 1
		else:
			break

	#somewhat intelligent output. Stupid, but clever enough.
	if counter == 0:
		feedSummary = "There are no new entries in " + feed.feed.title + ".\n"
	elif counter == 1:
		feedSummary = "There is 1 new entry in " + feed.feed.title + ".\n" 
	else:
		feedSummary = "There are " + str(counter) + " new entries in " + \
		feed.feed.title + ".\n"
	feedText = feedText
	return (counter, feedText, feedSummary)
#*** END OF checkFeed() *********************************************************
	
#this allows the program to run on it's own. If the file is imported, then 
#__name__ will equal the module's name.
if __name__ == "__main__":
	main()