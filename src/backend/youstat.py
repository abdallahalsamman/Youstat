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
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# CHANNEL_NAME = "nigahiga" # CHANNEL WITHOUT AUTO SUBTITLES BUT WITH MANUAL SUBTITLES
# CHANNEL_NAME = "KSIOlajidebt" # CHANNEL WITHOUT MANUAL SUBTITLES BUT WITH AUTO SUBTITLES

PAGE_SIZE = 50
if DEBUG:
	PAGE_SIZE = 2

TOP_WORDS_SIZE = 30 # the top 30 frequent words
STOPWORDS_FOLDER = os.path.dirname(os.path.abspath(__file__)) + "/" + "stopwords"

def channel_url(name):
	return "https://www.googleapis.com/youtube/v3/channels?part=contentDetails&forUsername="+name+"&key="+API_KEY

def get_channel(name):
	return get_json(channel_url(name))

def playlist_url(id, token):
	url = "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet%2CcontentDetails&maxResults="+ str(PAGE_SIZE) +"&playlistId="+id+"&key="+API_KEY
	return url + (("&pageToken=" + token) if token else "")

def uploads_id(channel):
	return channel['items'][0]['contentDetails']['relatedPlaylists']['uploads']

def video_id(vid):
	return vid['contentDetails']['videoId']

def is_video(vid):
	return ('videoId' in vid['contentDetails'])

def extract_original_subs(manual_subs, manual_subs_non_en, auto_subs, auto_subs_non_en):
	return map(lambda x: x[1], manual_subs + auto_subs + manual_subs_non_en + auto_subs_non_en)

def extract_english_subs(manual_subs, manual_subs_non_en, auto_subs, auto_subs_non_en):
	return map(lambda x: x[1], manual_subs + auto_subs) + \
		map(lambda x: x[2], manual_subs_non_en + auto_subs_non_en)

def format_subtitles(subtitles):
	subtitles = htmlParser.unescape(htmlParser.unescape(subtitles))
	subtitles = subtitles.replace('</text>', '\n')
	subtitles = re.sub('<.*?>', '', subtitles)
	return subtitles

def get_text(url):
	return requests.get(url).text

def get_json(url):
	return json.loads( get_text(url) )

def translated_sub(url):
	return url + "&tlang=en"

def create_subtitle(lang, url):
	return { 'lang': lang, 'url': url }

def make_subtitle(subtitle, translate=False):
	url = translated_sub(subtitle['url']) if translate else subtitle['url']
	return  (  subtitle['lang']
			 , format_subtitles(get_text(url)) or None )

def url_manual_sub(video_id, lang):
	return 'http://video.google.com/timedtext?lang='+lang+'&v='+video_id

def get_manual_sub(video_id):
	list_manual_subs = get_text('http://video.google.com/timedtext?type=list&v='+video_id)
	if 'lang_default="true"' in list_manual_subs:
		langs = re.findall('lang_code="(.*?)"', list_manual_subs)
		default_lang = re.findall('<track.*lang_code="(.*?)".*lang_default="true".*\/>', list_manual_subs)[0]
		subtitle = create_subtitle(default_lang, url_manual_sub(video_id, default_lang))
		if default_lang == 'en':
			return (video_id, make_subtitle(subtitle), None)
		else:
			url_translated_sub = url_manual_sub(video_id, 'en') if 'en' in list_manual_subs \
				else translated_sub(url_manual_sub(video_id, default_lang))
			translated_subtitle = create_subtitle('en', 'url')
			return (video_id, make_subtitle(subtitle), make_subtitle(translated_subtitle))
	else:
		return (video_id, None, None)

def sub_url(response):
	matches = re.findall("\"caption_tracks\".*?(https.*?lang\%3D(..))", response)
	if matches:
		url, lang = matches[0]
		url_decoded = urllib.unquote(url).decode('utf8')
		return (  create_subtitle(lang, url_decoded)
				, create_subtitle('en', translated_sub(url_decoded)) if lang != 'en' else None )
	return (None, None)

def get_auto_sub(video_id):
	video_page = get_text('http://youtube.com/watch?v='+video_id)
	default_sub, translated_sub = sub_url(video_page)
	if default_sub and not translated_sub:
		return (video_id, make_subtitle(default_sub), None)
	if default_sub and translated_sub:
		return (video_id, make_subtitle(default_sub), make_subtitle(translated_sub))
	return (video_id, None, None)

def split_results(results):
	english_videos = []
	non_english_videos = []
	no_subtitle_videos = []
	for (id, default_subtitle, translated_subtitle) in results:
		if default_subtitle and translated_subtitle:
			non_english_videos += [(id, default_subtitle, translated_subtitle)]
		elif default_subtitle:
			english_videos += [(id, default_subtitle)]
		else:
			no_subtitle_videos += [id]
	return (english_videos, non_english_videos, no_subtitle_videos)


def get_subtitle_statistics(sub):
	r = requests.post(url = 'https://tone-analyzer-demo.mybluemix.net/api/tone',
		data = {'text': sub},
		headers={'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'})
	return json.loads(r.text)

def get_playlist(channel, token=None):
	playlist = get_json(playlist_url(uploads_id(channel), token))
	if DEBUG:
		return playlist['items']
	if 'nextPageToken' in playlist:
		return playlist['items'] + get_playlist(channel, playlist['nextPageToken'])
	else:
		return playlist['items']

def words_frequency(subtitles):
	def sort_words_by_freq(words):
		return sorted(words.items(), key=lambda v: v[1], reverse=True)

	def get_stopwords(lang):
		def stopwords_file():
			return STOPWORDS_FOLDER+'/'+lang+'.txt'
		supported_langs = [name.split('.')[0] for name in os.listdir(STOPWORDS_FOLDER)]
		if lang in supported_langs:
			with open( stopwords_file() ) as f:
			    content = f.read().splitlines()
			return content
		else:
			return []

	def rm_stop_words(subtitle):
		regex = r'\b('+'|'.join( get_stopwords(  subtitle[0] ) )+r')\b'
		sub_clean_1 = re.sub('[?!,.\(\)\[\]]', ' ', subtitle[1])
		sub_clean_2 = re.sub('["-]', '', sub_clean_1)
		clean_subtitle = re.sub(regex, '', sub_clean_2, flags=re.IGNORECASE)
		return clean_subtitle

	def count_words(subtitle, words=None):
		words = words if words else {}
		for word in subtitle.split():
			if word in words:
				words[word] += 1
			else:
				words[word] = 1
		return words

	def process_subs(subtitles):
		words = {}
		for subtitle in subtitles:
			clean_subtitle = rm_stop_words(subtitle)
			words = count_words(clean_subtitle, words)
		return words

	words = process_subs(subtitles)
	return sort_words_by_freq(words)[0:TOP_WORDS_SIZE]

def beautify_stats(stats):
	def beautify_category(category):
		scores = map(lambda x: x['score'], category['tones'])
		scores_sum = reduce(lambda x,y: x+y, scores)
		tones = [ { tone['tone_name']: (tone['score'] / scores_sum) * 100
					} for tone in category['tones'] ]
		return { 'category_name': category['category_name'], 'tones': tones }
	return map(beautify_category, stats['document_tone']['tone_categories'])

def get_stats(channel_name):
	channel_name = channel_name
	channel = get_channel(channel_name)
	items = get_playlist(channel)
	video_ids = [video_id(item) for item in items if is_video(item)]

	manual_subs, manual_subs_non_en, video_ids_no_manual_subs = (
		split_results([get_manual_sub(i) for i in video_ids]) )

	auto_subs, auto_subs_non_en, video_ids_no_auto_subs = (
		split_results([get_auto_sub(i) for i in video_ids_no_manual_subs]) )

	if manual_subs or auto_subs or manual_subs_non_en or auto_subs_non_en:
		original_subs = extract_original_subs(manual_subs, manual_subs_non_en, auto_subs, auto_subs_non_en)
		english_subs = extract_english_subs(manual_subs, manual_subs_non_en, auto_subs, auto_subs_non_en)
		frequent_words = words_frequency( original_subs )
		stats = get_subtitle_statistics( english_subs[0][1] )
		beautiful_stats = beautify_stats(stats)
		return beautiful_stats
	else:
		return "No subtitles in this channel: "+channel_name

def main():
	channel_name = sys.argv[1]
	print get_stats(channel_name)

if __name__ == '__main__':
	main()
