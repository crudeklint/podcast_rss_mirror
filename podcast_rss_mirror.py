import os
import io
import sys
import time
import argparse
import urllib.request

# import wget
from datetime import datetime


from subprocess import call
from xml.etree import ElementTree as ET

parser = argparse.ArgumentParser( description="This script creates a rss-podcast mirror on your local server") 
parser.add_argument( "-i", "--input_href", help="Input podcast rss address", required=True) 
parser.add_argument( "-p", "--podcast_name", help="Local pocast name", required=True, default=None ) 
parser.add_argument( "-n", "--new_href", help="New base-href", required=True, default=None) 
parser.add_argument( "--DOWNLOAD_ALL", help="Download all podcasts (default 1 year)", required=False, action='store_true' ) 
parser.add_argument( "--TEST", help="If this is used, only 10 files will be downloaded", required=False, action='store_true' ) 

args = vars( parser.parse_args( ) ) 

newhref = args["new_href"]
pod_name = args["podcast_name"]
pod_real_href = args["input_href"]
test_mode = args["TEST"]
download_all = args["DOWNLOAD_ALL"]

time_threshold = 60*60*24-100
oldest_pod = 365 #days

def uglyfix( input_path ) :	
	thefile = io.open( input_path, mode="r", encoding="utf-8")
	file_string = thefile.read()
	thefile.close()
	
	for tag in ["itunes:summary", "description", "title", "itunes:keywords", "itunes:subtitle"] :
		fixed_tag = "<" + tag + ">"
		fixed_endtag = "</" + tag + ">"
	
		file_string = file_string.replace( fixed_tag, fixed_tag+"<![CDATA[" ).replace( fixed_endtag, "]]>"+fixed_endtag )
	
	thefile = open( input_path, "w" )
	thefile.write( file_string )
	thefile.close()
	

def logmess( message, log_file_obj, lastlog = False ) :
	current_timestamp = datetime.now().replace(microsecond=0).isoformat(" ")
	
	if( lastlog ) :
		eol = "\n\n"
	else :
		eol = "\n"
	
	log_file_obj.write( current_timestamp + " " + message + eol )
	
	if( lastlog ) : 
		log_file_obj.close()

def download_file( input, output ) :
	# urllib.request.urlretrieve( input, output )
	call( ["wget", input, "-O", output] )
	
		
def create_pod_mirror( rss_href, podname, new_base_href ) :

	delete_list = []

	now_time = time.time()
	script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
	log_path = os.path.join( script_dir, "podcast_mirror.log" )
	
	log_file = open( log_path, "a" )

	logmess( "Start mirroring of " + rss_href, log_file )
	
	local_pod_dir = os.path.join( script_dir, pod_name )
	local_pod_rss = os.path.join( local_pod_dir, pod_name + ".rss" )
	pod_last_download_path = os.path.join( local_pod_dir, "last_download.log" )
	
	if( not os.path.exists( local_pod_dir ) ) :
		os.mkdir( local_pod_dir )

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
	
	tmp_podcast_rss = os.path.join( script_dir, pod_name + "_rss.tmp" )
	
	ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd" )
	ET.register_namespace("atom", "http://www.w3.org/2005/Atom" )
	ET.register_namespace("sr", "http://www.sverigesradio.se/podrss" )
	
	download_file( pod_real_href, tmp_podcast_rss )
	rss_tree = ET.parse( tmp_podcast_rss )
	os.remove( tmp_podcast_rss )

	root_elem = rss_tree.getroot()
	data_node = root_elem.findall( 'channel' )
	
	i=0
	
	do_log = True
	
	for child in data_node[0]:
		if( child.tag != "item" ) :
			continue
		
		i+=1
		
		if( i > 10 and test_mode ) :
			delete_list.append( child )
			if( do_log ) : 
				logmess( "Test mode, exiting.", log_file )
				
			do_log = False
			continue
		
		# mp3link = child.findall( "guid" )[0]
		# oldlink = mp3link.text
		
		pub_date = child.findall( "pubDate" )[0]
		datestring = pub_date.text
		
		date_obj = datetime.strptime(datestring, "%a, %d %b %Y %H:%M:%S %Z")
		time_delta = datetime.now() - date_obj

		mp3link = child.findall( "enclosure" )[0]
		oldlink = mp3link.get( "url" )
		link_basename = os.path.basename( oldlink )
		
		if( time_delta.days > oldest_pod and not download_all ) :
			delete_list.append( child )
			logmess( link_basename + " too old. deleting from rss" , log_file )
			continue
		
		# title = child.findall( "title" )[0]
		# title.text = "<![CDATA[" + title.text + "]]>"
		
		newlink = os.path.join( newhref, pod_name, link_basename )
		local_path = os.path.join( local_pod_dir, link_basename )
		
		# mp3link.text = newlink
		mp3link.set( "url", newlink )
	
		if( not os.path.isfile( local_path ) ) :
			# download_file( oldlink, local_path )  
			logmess( "downloading " + link_basename, log_file )
			time.sleep( 1 )
		else :
			logmess( "skipping " + link_basename + ", already exists", log_file )

	for deletechild in delete_list:
		data_node[0].remove( deletechild )
			
	last_download_file = open( pod_last_download_path, "w" )
	last_download_file.write( str( int( now_time ) ) )
	last_download_file.close()
	
	rss_tree.write( local_pod_rss, encoding="UTF-8", xml_declaration=True )
	
	uglyfix( local_pod_rss )
	logmess( "Finished mirroring " + rss_href, log_file, True )

create_pod_mirror( pod_real_href, pod_name, newhref )



	
	
	