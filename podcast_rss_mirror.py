import os
import sys
import time
import datetime
import argparse

# import wget
import urllib.request

from xml.etree import ElementTree as ET

parser = argparse.ArgumentParser( description="This script creates a rss-podcast mirror on your local server") 
parser.add_argument( "-i", "--input_href", help="Input podcast rss address", required=True) 
parser.add_argument( "-p", "--podcast_name", help="Local pocast name", required=True, default=None ) 
parser.add_argument( "-n", "--new_href", help="New base-href", required=True, default=None) 
parser.add_argument( "--TEST", help="If this is used, only 10 files will be downloaded", required=False, action='store_true' ) 

args = vars( parser.parse_args( ) ) 

newhref = args["new_href"]
pod_name = args["podcast_name"]
pod_real_href = args["input_href"]
test_mode = args["TEST"]

time_threshold = 60*60*24-100

def logmess( message, log_file_obj, lastlog = False ) :
	current_timestamp = datetime.datetime.now().replace(microsecond=0).isoformat(" ")
	
	if( lastlog ) :
		eol = "\n\n"
	else :
		eol = "\n"
	
	log_file_obj.write( current_timestamp + " " + message + eol )
	
	if( lastlog ) : 
		log_file_obj.close()

def download_file( input, output ) :
	urllib.request.urlretrieve( input, output )
		
def create_pod_mirror( rss_href, podname, new_base_href ) :

	now_time = time.time()
	script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
	log_path = os.path.join( script_dir, "podcast_mirror.log" )
	
	log_file = open( log_path, "a" )

	logmess( "Start mirroring of " + rss_href, log_file )
	
	local_pod_dir = os.path.join( script_dir, pod_name )
	local_pod_rss = os.path.join( local_pod_dir, pod_name + ".rss" )

	if( not os.path.exists( local_pod_dir ) ) :
		os.mkdir( local_pod_dir )

	if( os.path.exists( local_pod_rss ) ):
		local_date_node = ET.parse( local_pod_rss ).getroot().findall( "last_download" )
		
		if( len( local_date_node ) > 0 ) :
			last_download = int( local_date_node[0].text )
		
		if( ( now_time - last_download < time_threshold ) and not test_mode ) :
			logmess( "Download timeout has not been reached! Exiting", log_file, True  )
			return 0
	
	tmp_podcast_rss = os.path.join( script_dir, pod_name + "_rss.tmp" )
	
	download_file( pod_real_href, tmp_podcast_rss )
	rss_tree = ET.parse( tmp_podcast_rss )
	os.remove( tmp_podcast_rss )
	
	root_elem = rss_tree.getroot()
	data_node = root_elem.findall( 'channel' )

	i=0
	
	for child in data_node[0]:
		if( child.tag != "item" ) :
			continue
		
		i+=1
		
		if( i > 10 and test_mode ) :
			logmess( "Test mode, exiting.", log_file, True  )
			return 0
		
		mp3link = child.findall( "guid" )[0]
		oldlink = mp3link.text
		
		link_basename = os.path.basename( oldlink )
		
		newlink = os.path.join( newhref, pod_name, link_basename )
		local_path = os.path.join( local_pod_dir, link_basename )
		
		mp3link.text = newlink
		
		if( not os.path.isfile( local_path ) ) :
			download_file( oldlink, local_path )  
			logmess( "downloading " + link_basename, log_file )
			time.sleep( 1 )
		else :
			logmess( "skipping " + link_basename + ", already exists", log_file )

	date_node = ET.SubElement( root_elem, "last_download" )
	date_node.text = str( int( now_time ) )
	rss_tree.write( local_pod_rss )
	logmess( "Finished mirroring " + rss_href, log_file, True )

create_pod_mirror( pod_real_href, pod_name, newhref )


	
	
	