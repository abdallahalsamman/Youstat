import json
import re
import urllib
import requests
import os
import sys

from HTMLParser import HTMLParser
htmlParser = HTMLParser()

# import ipdb; ipdb.set_trace()

API_KEY = os.environ['YOUTUBE_API_KEY']

# CHANNEL_NAME = "nigahiga" # CHANNEL WITHOUT AUTO SUBTITLES BUT WITH MANUAL SUBTITLES
# CHANNEL_NAME = "KSIOlajidebt" # CHANNEL WITHOUT MANUAL SUBTITLES BUT WITH AUTO SUBTITLES

PAGE_SIZE = 5 # get one vid only 50 max

def channel_url(name):
	return "https://www.googleapis.com/youtube/v3/channels?part=contentDetails&forUsername="+name+"&key="+API_KEY

def get_channel(name):
	return get_json(channel_url(name))

def playlist_url(id, token):
	url = "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet%2CcontentDetails&maxResults="+ str(PAGE_SIZE) +"&playlistId="+id+"&key="+API_KEY
	return url + (("&pageToken=" + token) if token else "")

def uploads_id(channel):
	return channel['items'][0]['contentDetails']['relatedPlaylists']['uploads']

def latest_sub(videos_manual_subs, videos_auto_subs):
	if videos_manual_subs:
		return videos_manual_subs[0][1]
	if videos_auto_subs:
		return videos_auto_subs[0][1]

def video_id(vid):
	return vid['contentDetails']['videoId']

def is_video(vid):
	return ('videoId' in vid['contentDetails'])

def format_subtitles(subtitles):
	subtitles = htmlParser.unescape(htmlParser.unescape(subtitles))
	subtitles = subtitles.replace('</text>', '\n')
	subtitles = re.sub('<.*?>', '', subtitles)
	return subtitles

def get_json(url):
	page = requests.get(url) # gets the content of the url that fetches the videos
	return json.loads(page.text) # parses the content

def get_manual_sub(video_id):
	subtitle = requests.get('http://video.google.com/timedtext?lang=en&v='+video_id).text
	return ((video_id, format_subtitles(subtitle)) if subtitle else (video_id, None))

def sub_url(response):
	matches = re.findall("\"caption_tracks\".*?(https.*lang\%3D(.*?))\\\u0026", response)
	if matches:
		url, lang = matches[0]
		if lang == 'en':
			return urllib.unquote(url).decode('utf8')
	return None

def get_auto_sub(video_id):
	video_page = requests.get('http://youtube.com/watch?v='+video_id).text
	url = sub_url(video_page)
	if url:
		subtitle = requests.get(url).text
		return (video_id, format_subtitles(subtitle))
	return (video_id, None)

def split_results(results):
	oks = []
	errs = []
	for (id, result) in results:
		if result:
			oks += [(id, result)]
		else:
			errs += [id]
	return (oks, errs)


def get_subtitle_statistics(sub):
	r = requests.post(url = 'https://tone-analyzer-demo.mybluemix.net/api/tone',
		data = {'text': sub},
		headers={'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'})
	return json.loads(r.text)

def get_playlist(channel, token=None):
	playlist = get_json(playlist_url(uploads_id(channel), token))
	if 'nextPageToken' in playlist['items']:
		return playlist['items'] + get_playlist(playlist['nextPageToken'])
	else:
		return playlist['items']

def get_stats(channel_name):
	channel_name = channel_name
	channel = get_channel(channel_name)
	items = get_playlist(channel)
	video_ids = [video_id(item) for item in items if is_video(item)]

	manual_subs, video_ids_no_manual_subs = (
		split_results(get_manual_sub(i) for i in video_ids) )

	auto_subs, video_ids_no_auto_subs = (
		split_results(get_auto_sub(i) for i in video_ids_no_manual_subs) )

	sub = latest_sub(manual_subs, auto_subs)
	stats = get_subtitle_statistics(sub)
	return stats

def main():
	channel_name = sys.argv[1]
	print get_stats(channel_name)

if __name__ == '__main__':
	main()
