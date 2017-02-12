from __future__ import unicode_literals

# coding=utf-8

from django.apps import AppConfig
from django.http import HttpResponse

import json
import re
import urllib
import requests
import grequests
import os
import sys

from HTMLParser import HTMLParser
htmlParser = HTMLParser()
class YoustatConfig(AppConfig):
    name = 'youstat'



API_KEY = os.environ['YOUTUBE_API_KEY']

connection_limit = 500
s = requests.Session()
a = requests.adapters.HTTPAdapter(max_retries=3, pool_connections=connection_limit, pool_maxsize=connection_limit)
b = requests.adapters.HTTPAdapter(max_retries=3, pool_connections=connection_limit, pool_maxsize=connection_limit)
s.mount('http://', a)
s.mount('https://', b)

# CHANNEL_NAME = "nigahiga" # CHANNEL WITHOUT AUTO SUBTITLES BUT WITH MANUAL SUBTITLES
# CHANNEL_NAME = "KSIOlajidebt" # CHANNEL WITHOUT MANUAL SUBTITLES BUT WITH AUTO SUBTITLES

PAGE_SIZE = 50

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

def extract_video_id(video):
    return video['contentDetails']['videoId']

def is_video(video):
    return ('videoId' in video['contentDetails'])

def extract_original_subs(subtitles):
    manual_subs, manual_subs_non_en, auto_subs, auto_subs_non_en = subtitles
    return map(lambda x: x[1], manual_subs + auto_subs + manual_subs_non_en + auto_subs_non_en)

def extract_english_subs(subtitles):
    manual_subs, manual_subs_non_en, auto_subs, auto_subs_non_en = subtitles
    return map(lambda x: x[1], manual_subs + auto_subs) + \
        map(lambda x: x[2], manual_subs_non_en + auto_subs_non_en)

def extract_langs(subtitles):
    return list(set(map(lambda x: x[0], subtitles)))

def format_subtitles(subtitles):
    subtitles = htmlParser.unescape(htmlParser.unescape(subtitles))
    subtitles = subtitles.replace('</text>', '\n')
    subtitles = re.sub('<.*?>', '', subtitles)
    return subtitles

def greq_get_text(url, index, total):
    return grequests.get(url, timeout=1, session=s)

def get_text(url):
    return s.get(url).text

def get_json(url):
    return json.loads( get_text(url) )

def translated_sub(url):
    return url + "&tlang=en"

def create_subtitle(lang, url):
    return { 'lang': lang, 'url': url }

def url_manual_sub(video_id, lang):
    return 'http://video.google.com/timedtext?lang='+lang+'&v='+video_id

def sub_url(src):
    matches = re.findall("\"caption_tracks\".*?(https.*?lang\%3D(..))", src)
    if matches:
        url, lang = matches[0]
        url_decoded = urllib.unquote(url).decode('utf8')
        return (  create_subtitle(lang, url_decoded)
                , create_subtitle('en', translated_sub(url_decoded)) if lang not in ['en', 'en-GB'] else None )
    return (None, None)

def get_manual_sub_langs(video_id, index, total):
    return greq_get_text('http://video.google.com/timedtext?type=list&v='+video_id, index, total)

def get_video_page(video_id, index, total):
    return greq_get_text('https://www.youtube.com/watch?v='+video_id, index, total)

def available_manual_subs(src):
    langs = re.findall('lang_code="(.*?)"', src)
    if 'lang_default="true"' in src:
        default_lang = re.findall('<track.*lang_code="(.*?)".*lang_default="true".*\/>', src)[0]
        return (default_lang, langs)
    return (None, langs)

def make_manual_sub(video_id, manual_subs_page):
    if manual_subs_page:
        default_lang, langs = available_manual_subs( manual_subs_page )
        if default_lang:
            subtitle = create_subtitle(default_lang, url_manual_sub(video_id, default_lang))
            if default_lang in ['en', 'en-GB']:
                return (video_id
                    , ( subtitle['lang'], subtitle['url'] )
                    , None)
            else:
                url_translated_sub = url_manual_sub(video_id, 'en') if 'en' in langs \
                    else translated_sub(url_manual_sub(video_id, default_lang))
                translated_subtitle = create_subtitle('en', url_translated_sub)
                return (video_id
                    , ( subtitle['lang'], subtitle['url'] )
                    , ( translated_subtitle['lang'], translated_subtitle['url'] ))
    return (video_id, None, None)

def make_auto_sub(video_id, video_page):
    if video_page:
        default_sub, translated_sub = sub_url(video_page)
        if default_sub and not translated_sub:
            return (video_id
                    , ( default_sub['lang'], default_sub['url'] )
                    , None)
        if default_sub and translated_sub:
            return (video_id
                    , ( default_sub['lang'], default_sub['url'] )
                    , ( translated_sub['lang'], translated_sub['url'] ) )
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
    r = s.post(url = 'https://tone-analyzer-demo.mybluemix.net/api/tone',
        data = {'text': sub},
        headers={'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'})
    return json.loads(r.text)

def get_playlist(channel, token=None):
    playlist = get_json(playlist_url(uploads_id(channel), token))
    if 'nextPageToken' in playlist:
        return playlist['items'] + get_playlist(channel, playlist['nextPageToken'])
    else:
        return playlist['items']

def words_frequency(subtitles, stopwords):
    def sort_words_by_freq(words):
        return sorted(words.items(), key=lambda v: v[1], reverse=True)

    def rm_stop_words(subtitle):
        regex = r'\b('+b'|'.join( stopwords[subtitle[0]] ).decode('utf-8')+r')\b'
        sub_clean_1 = re.sub('[\,\.\(\)\[\]\*-]', ' ', subtitle[1])
        sub_clean_2 = re.sub('["]', '', sub_clean_1)
        clean_subtitle = re.sub(regex, '', sub_clean_2, flags=re.IGNORECASE)
        return clean_subtitle

    def count_words(subtitle, words=None):
        words = words if words else {}
        for word in subtitle.split():
            if word in words:
                words[word] += 1
            elif len(word) > 1:
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

def get_stopwords_lang(lang):
    def stopwords_file():
        return STOPWORDS_FOLDER+'/'+lang+'.txt'
    supported_langs = [name.split('.')[0] for name in os.listdir(STOPWORDS_FOLDER)]
    if lang in supported_langs:
        with open( stopwords_file() ) as f:
            content = f.read().splitlines()
        return content
    else:
        return []

def get_stopwords(langs):
    return { lang: get_stopwords_lang(lang) for lang in langs }

def beautify_stats(stats):
    def beautify_category(category):
        scores = map(lambda x: x['score'], category['tones'])
        scores_sum = reduce(lambda x,y: x+y, scores)
        tones = [ { tone['tone_name']: (tone['score'] / scores_sum) * 100
                    } for tone in category['tones'] ]
        return { 'category_name': category['category_name'], 'tones': tones }
    return map(beautify_category, stats['document_tone']['tone_categories'])

def main(request, args):
    channel_name = args
    channel = get_channel(channel_name)
    items = get_playlist(channel)
    video_ids = [extract_video_id(item) for item in items if is_video(item)]
    video_ids_len = len(video_ids)
    manual_sub_langs = grequests.map(
        [ get_manual_sub_langs(i, index, video_ids_len) for index, i in enumerate(video_ids) ])

    url_manual_subs, url_manual_subs_non_en, video_ids_no_manual_subs = (
        split_results([make_manual_sub(video_id, manual_sub_langs[index].text) for index, video_id in enumerate(video_ids) if manual_sub_langs[index]]) )

    video_ids_no_manual_subs_len = len(video_ids_no_manual_subs)
    videos_pages = grequests.map(
        [ get_video_page(i, index, video_ids_no_manual_subs_len) for index, i in enumerate(video_ids_no_manual_subs) ] )

    url_auto_subs, url_auto_subs_non_en, video_ids_no_auto_subs = (
        split_results([make_auto_sub(video_id, videos_pages[index].text) for index, video_id in enumerate(video_ids_no_manual_subs) if videos_pages[index] ]) )

    url_manual_subs_len = len(url_manual_subs)
    url_auto_subs_len = len(url_auto_subs)
    manual_subs_pages = grequests.map(
        [ greq_get_text(sub[1][1], index, url_manual_subs_len) for index, sub in enumerate(url_manual_subs) ] )
    auto_subs_pages = grequests.map(
        [ greq_get_text(sub[1][1], index, url_auto_subs_len) for index, sub in enumerate(url_auto_subs) ] )

    manual_subs, auto_subs = tuple(
        [ ( sub[0]
          , ( sub[1][0], format_subtitles( (manual_subs_pages if cat_ind is 0 else auto_subs_pages)[index].text ))
          ) for index, sub in enumerate(sub_cat)
          if (manual_subs_pages if cat_ind is 0 else auto_subs_pages)[index]
        ] for cat_ind, sub_cat in enumerate( (url_manual_subs, url_auto_subs) ) )

    url_manual_subs_non_en_len = len(url_manual_subs_non_en)
    url_auto_subs_non_en_len = len(url_auto_subs_non_en)

    manual_subs_non_en_pages = grequests.map(
        [ greq_get_text(sub[1][1], index, url_manual_subs_non_en_len) for index, sub in enumerate(url_manual_subs_non_en) ] )
    manual_subs_non_en_trans_pages = grequests.map(
        [ greq_get_text(sub[2][1], index, url_manual_subs_non_en_len) for index, sub in enumerate(url_manual_subs_non_en) ] )
    auto_subs_non_en_pages = grequests.map(
        [ greq_get_text(sub[1][1], index, url_auto_subs_non_en_len) for index, sub in enumerate(url_auto_subs_non_en) ] )
    auto_subs_non_en_trans_pages = grequests.map(
        [ greq_get_text(sub[2][1], index, url_auto_subs_non_en_len) for index, sub in enumerate(url_auto_subs_non_en) ] )

    manual_subs_non_en, auto_subs_non_en = tuple(
        [
            ( sub[0]
            , ( sub[1][0], format_subtitles( (manual_subs_non_en_pages if cat_ind is 0 else auto_subs_non_en_pages)[index].text ))
            , ( sub[2][0], format_subtitles( (manual_subs_non_en_trans_pages if cat_ind is 0 else auto_subs_non_en_trans_pages)[index].text ))
            )
            for index, sub in enumerate(sub_cat)
            if (manual_subs_non_en_pages if cat_ind is 0 else auto_subs_non_en_pages)[index]
                and (manual_subs_non_en_trans_pages if cat_ind is 0 else auto_subs_non_en_trans_pages)[index]
        ] for cat_ind, sub_cat in enumerate( (url_manual_subs_non_en, url_auto_subs_non_en) ) )

    subtitles = (manual_subs, manual_subs_non_en, auto_subs, auto_subs_non_en)
    if subtitles[0] or subtitles[1] or subtitles[2] or subtitles[3]:
        original_subs = extract_original_subs(subtitles)
        english_subs = extract_english_subs(subtitles)
        stopwords = get_stopwords( extract_langs ( original_subs ) )
        frequent_words = words_frequency( original_subs, stopwords )
        # beautiful_stats = beautify_stats ( get_subtitle_statistics( english_subs[0][1] ) )
        return HttpResponse(json.dumps(frequent_words))
    return HttpResponse(json.dumps([["No subtitles in this channel: " + channel_name, ""]]))
