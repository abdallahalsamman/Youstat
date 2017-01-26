import requests
import json
import re
import urllib
from HTMLParser import HTMLParser
# import ipdb; ipdb.set_trace()

API_KEY = "AIzaSyCXGLaX39LmHNWUzSW6ejE9ywvOafNNZfI"
CHANNEL_ID = "UCVtFOytbRpEvzLjvqGG5gxQ"
# CHANNEL_NAME = "KSIOlajidebt"
CHANNEL_NAME = "nigahiga"
results_per_page = 1
CHANNEL_VIDEOS = []
CHANNEL_VIDEOS_WITH_MANUAL_SUBTITLES = []
CHANNEL_VIDEOS_WITH_OUT_MANUAL_SUBTITLES = []
CHANNEL_VIDEOS_WITH_AUTO_SUBTITLES = []
CHANNEL_VIDEOS_WITH_OUT_AUTO_SUBTITLES = []

"""
	make_channel_video_list_url method takes in an API_KEY and a CHANNEL_ID and returns the
	youtube search api link to fetch all videos of channel.

	the API_KEY and CHANNEL_ID are both optional
"""
def make_channel_info_url():
	return "https://www.googleapis.com/youtube/v3/channels?part=contentDetails&forUsername="+CHANNEL_NAME+"&key="+API_KEY

def make_playlist_videos_list_url(PLAYLIST_ID=""):
	return "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet%2CcontentDetails&maxResults="+ str(results_per_page) +"&playlistId="+PLAYLIST_ID+"&key="+API_KEY

def get_json_parsed_content_from_url(URL):
	page = requests.get(URL) # gets the content of the url that fetches the videos
	return json.loads(page.text) # parses the content


def filter_videos_and_nonvideos_from_data(DATA):
	global CHANNEL_VIDEOS
	CHANNEL_VIDEOS += [i['contentDetails']['videoId'] for i in DATA['items'] if 'videoId' in i['contentDetails']] # appends all videos id

def get_all_videos():
	api_url = make_channel_info_url()
	parsed_json_data = get_json_parsed_content_from_url(api_url) # get next page content

	uploads_playlist_id = parsed_json_data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
	playlist_api_url = make_playlist_videos_list_url(uploads_playlist_id)
	
	while True:
			url = playlist_api_url + (("&pageToken=" + parsed_json_data['nextPageToken']) if 'parsed_json_data' in vars() and 'nextPageToken' in parsed_json_data else "")
			parsed_json_data = get_json_parsed_content_from_url(url) # get next page content
			filter_videos_and_nonvideos_from_data(parsed_json_data)
			break # remove if you want to make this tool go through all the videos
			if 'nextPageToken' not in parsed_json_data:
				break

def filter_videos_by_subtitle_type():
	global CHANNEL_VIDEOS_WITH_MANUAL_SUBTITLES, CHANNEL_VIDEOS_WITH_OUT_MANUAL_SUBTITLES
	for video_id in CHANNEL_VIDEOS:
		r = requests.get('http://video.google.com/timedtext?lang=en&v='+video_id)
		if r.text != '':
			CHANNEL_VIDEOS_WITH_MANUAL_SUBTITLES += [{'video_id': video_id, 'subtitles': format_subtitles(r.text)}]
		else:
			CHANNEL_VIDEOS_WITH_OUT_MANUAL_SUBTITLES += [video_id]

def format_subtitles(subtitles):
	htmlParser = HTMLParser()
	subtitles = htmlParser.unescape(htmlParser.unescape(subtitles))
	subtitles = subtitles.replace('</text>', '\n')
	subtitles = re.sub('<.*?>', '', subtitles)
	return subtitles

def get_latest_video_sub():
	if CHANNEL_VIDEOS_WITH_MANUAL_SUBTITLES:
		return CHANNEL_VIDEOS_WITH_MANUAL_SUBTITLES[0]['subtitles']
	if CHANNEL_VIDEOS_WITH_AUTO_SUBTITLES:
		import ipdb; ipdb.set_trace()
		return CHANNEL_VIDEOS_WITH_AUTO_SUBTITLES[0]['subtitles']

def get_subtitles_for_videos_with_no_manual_subtitles():
	global CHANNEL_VIDEOS_WITH_AUTO_SUBTITLES, CHANNEL_VIDEOS_WITH_OUT_AUTO_SUBTITLES
	for video_id in CHANNEL_VIDEOS_WITH_OUT_MANUAL_SUBTITLES:
		r = requests.get('http://youtube.com/watch?v='+video_id)
		# "caption_tracks".*?(https.*?")
		try:
			automatic_subtitle_link, lang = re.findall("\"caption_tracks\".*?(https.*lang\%3D(.*?))\\\u0026", r.text)[0]
			automatic_subtitle_link = urllib.unquote(automatic_subtitle_link).decode('utf8')
			if lang == 'en':
				subtitles_r = requests.get(automatic_subtitle_link)
				CHANNEL_VIDEOS_WITH_AUTO_SUBTITLES += [{'video_id': video_id, 'subtitles': format_subtitles(subtitles_r.text)}]
		except IndexError:
			CHANNEL_VIDEOS_WITH_OUT_AUTO_SUBTITLES += [video_id]

def get_subtitle_statistics():
	r = requests.post('https://tone-analyzer-demo.mybluemix.net/api/tone', data={'text': get_latest_video_sub()}, headers={'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'})
	return json.loads(r.text)

get_all_videos()
filter_videos_by_subtitle_type()
get_subtitles_for_videos_with_no_manual_subtitles()
get_subtitle_statistics()
