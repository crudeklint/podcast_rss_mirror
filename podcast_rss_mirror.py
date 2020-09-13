# ==================
# PODCAST RSS MIRROR
# ==================
#
# The purpose of this program is to create a mirror podcast RSS feed 
# in the case of a horrible work proxy or something like that.
#
# Usage:
# Run the program with the desired settings using CLI parameters:
#
# * -i or --input_href: the real rss-feed address for the podcast 
#   you want to mirror.
# * -p or --podcast_name: the local name of the podcast. Files and
#   .rss will be saved in a folder with this name.
# * -n or --new_href: the web-address to the place where this file
#   resides. The link address to the mp3-files will be changed to this
#   address.
# * --oldest_pod: how old may the oldest podcast be. Default is 365 days.
# * --TEST: Use this option to make a test with 10 files.
#
# How it works:
# The program will parse the input RSS-feed, download all mp3-files within
# the time threshold and create a new RSS with new link addresses. Only
# the downloaded files will appear in this feed.
#
# It will store the unix time-stamp of latest download in the podcast-
# folder and will not download more often than once per day.
#
# Schedule this with cron or something to make it run daily (or whenever you want)
#
# By a cold-infected Christoffer Rudeklint 2018-01-10

import os
import sys
import time
import argparse
import requests

from datetime import datetime
from subprocess import call
from xml.etree import ElementTree as ET

# Simple loggin function
def logmess( message, log_file_obj, lastlog = False ) :
	current_timestamp = datetime.now().replace(microsecond=0).isoformat(" ")
	
	if( lastlog ) :
		eol = "\n\n"
	else :
		eol = "\n"
	
	log_file_obj.write( current_timestamp + " " + message + eol )
	
	if( lastlog ) : 
		log_file_obj.close()

# Function to download files. This may not be the best choice
# but it works with my web host.
def download_file( input, output, username=None, password=None ) :
	# urllib.request.urlretrieve( input, output )
	# call( ["wget", input, "-O", output] )
	
	if( not( username and password ) ):
		call( ["wget", input, "-O", output] )
	else:
		r = requests.get( input, auth=(username, password) )
	
		if r.status_code == 200:
			with open( output, 'wb' ) as out:
				for bits in r.iter_content():
					out.write( bits )

	return

# Main function.
def create_pod_mirror( rss_href, pod_name, new_base_href, oldest_pod=365, username=None, password=None, test_mode=False ) :

	# This list contains the episodes which will be removed from
	# the main feed.
	delete_list = []

	now_time = time.time()
	script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
	log_path = os.path.join( script_dir, "podcast_mirror.log" )
	
	log_file = open( log_path, "a" )

	logmess( "Start mirroring of " + rss_href, log_file )
	
	local_pod_dir = os.path.join( script_dir, pod_name )
	local_pod_rss = os.path.join( local_pod_dir, pod_name + ".rss" )
	pod_last_download_path = os.path.join( local_pod_dir, "last_download.log" )
	
	# Check if the podcast-folder exists. If not, create it.
	if( not os.path.exists( local_pod_dir ) ) :
		os.mkdir( local_pod_dir )

	# If there is a file containing the unix timestamp of the 
	# latest download - check this and if the theshold is not yet 
	# reached, exit the program.
	if( os.path.exists( pod_last_download_path ) ):
		last_download_file = open( pod_last_download_path )
		last_download_string = last_download_file.read()
		
		if( last_download_string == "" ) :
			last_download = 0
		else :
			last_download = int( last_download_string )
		
		last_download_file.close()
		
		if( ( now_time - last_download < time_threshold ) and not test_mode ) :
			logmess( "Download timeout has not been reached! Exiting", log_file, True  )
			return 0
	
	# create the path to the downloaded temporary RSS-file.
	tmp_podcast_rss = os.path.join( script_dir, pod_name + "_rss.tmp" )
	
	# Register the namespaces so the resulting XML-file is correct ...
	ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd" )
	ET.register_namespace("atom", "http://www.w3.org/2005/Atom" )
	ET.register_namespace("sr", "http://www.sverigesradio.se/podrss" )
	
	# Download the real RSS to the temporary path. Parse it using
	# ElementTree and remove the temporary file.
	download_file( rss_href, tmp_podcast_rss, username, password )
	rss_tree = ET.parse( tmp_podcast_rss )
	os.remove( tmp_podcast_rss )

	root_elem = rss_tree.getroot()
	data_node = root_elem.findall( 'channel' )
	
	# This counter is used if the test-flag is set.
	i=0
	
	no_exists_skipped = 0
	
	# This is only used for not spamming the log with skipped files.
	do_log = True
	
	for child in data_node[0]:
		# Only "items" in the feed are interesting.
		if( child.tag != "item" ) :
			continue
		
		i+=1
		
		# If test mode is set and the number of files are reached, 
		# continue the loop.
		if( i > 3 and test_mode ) :
			delete_list.append( child )
			if( do_log ) : 
				logmess( "Test mode, exiting.", log_file )
				
			do_log = False
			continue

		# Get the publication date.
		pub_date = child.findall( "pubDate" )[0]
		datestring = pub_date.text
		
		# Parse the time string to a time-object and calculate the time delta.
		date_obj = datetime.strptime(datestring, "%a, %d %b %Y %H:%M:%S %z")

		# Remove timezone info if there is any. Might be stupid...
		date_obj = date_obj.replace( tzinfo=None )

		time_delta = datetime.now() - date_obj

		# Get the enclosure node which contains the mp3-link.
		mp3link = child.findall( "enclosure" )[0]
		oldlink = mp3link.get( "url" )
		
		# Get the filename for the mp3-file (used for rewriting the links in the feed).
		link_basename = os.path.basename( oldlink )
		
		# If the time delta is too large, add this episode to the remove-list.
		if( time_delta.days > oldest_pod ) :
			delete_list.append( child )
			continue

		# Create the new web address and the os path for the mp3-files.
		newlink = os.path.join( new_base_href, pod_name, link_basename )
		local_path = os.path.join( local_pod_dir, link_basename )
		
		# Update the mp3-parameter to the new web address.
		mp3link.set( "url", newlink )
	
		# Check if the file already exists. If it does, skip this episode.
		if( not os.path.isfile( local_path ) ) :
			download_file( oldlink, local_path, username, password )  
			logmess( "downloading " + link_basename, log_file )
			time.sleep( 1 )
		else :
			no_exists_skipped += 1
			

	# Remove the unwanted episodes from the feed.
	for deletechild in delete_list:
		data_node[0].remove( deletechild )
	
	# Write the last-download file.
	last_download_file = open( pod_last_download_path, "w" )
	last_download_file.write( str( int( now_time ) ) )
	last_download_file.close()
	
	# Write the new RSS-feed
	rss_tree.write( local_pod_rss, encoding="UTF-8", xml_declaration=True )

	if( len( delete_list ) > 0 ):
		logmess( "Skipped " + str( len( delete_list ) ) + " episodes that were older than " + str( oldest_pod ) + " days", log_file )

	if( no_exists_skipped > 0 ):
		logmess( "Skipped " + str( no_exists_skipped ) + " episodes that already exists on disk", log_file )
		
	logmess( "Finished mirroring " + rss_href, log_file, True )

def main():
	# Create the input parameters using argparse
	parser = argparse.ArgumentParser( description="This script creates a rss-podcast mirror on your local server") 
	parser.add_argument( "-i", "--input_href", help="Input podcast rss address", required=True) 
	parser.add_argument( "-p", "--podcast_name", help="Local pocast name", required=True, default=None ) 
	parser.add_argument( "-n", "--new_href", help="New base-href", required=True, default=None)
	parser.add_argument( "-unm", "--username", help="Username for auth", required=False, default=None)
	parser.add_argument( "-pwd", "--password", help="Password for auth", required=False, default=None)
	parser.add_argument( "--oldest_pod", help="How old files to download (in days). Default 365 days", type=int, required=False, default=None) 
	parser.add_argument( "--TEST", help="If this is used, only 10 files will be downloaded", required=False, action='store_true', default=False ) 

	args = vars( parser.parse_args( ) ) 

	new_base_href = args["new_href"]
	pod_name = args["podcast_name"]
	pod_real_href = args["input_href"]
	test_mode = args["TEST"]
	password = args["password"]
	username = args["username"]

	# Hardcoded time threshold for a little less than a day.
	time_threshold = 60*60*24-100

	if( args["oldest_pod"] is None ) :
		oldest_pod = 365 #days
	else :
		oldest_pod = args["oldest_pod"]
	create_pod_mirror( pod_real_href, pod_name, new_base_href, oldest_pod, username, password, test_mode )
	
if( __name__ == "__main__" ):
	main()

