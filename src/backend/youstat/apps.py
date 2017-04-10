from __future__ import unicode_literals

# coding=utf-8

from django.apps import AppConfig
from django.http import StreamingHttpResponse
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.views.decorators.http import condition

from models import Channels, Videos

import json
import re
import urllib
from urlparse import parse_qs, urlparse
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

TOP_WORDS_SIZE = 15 # the top 30 frequent words
STOPWORDS_FOLDER = os.path.dirname(os.path.abspath(__file__)) + "/" + "stopwords"

def channel_url(kind, id):
    return "https://www.googleapis.com/youtube/v3/channels?part=snippet,contentDetails&"+("forUsername" if kind == "user" else "id")+"="+id+"&key="+API_KEY

def get_channel(kind, id):
    return get_json(channel_url(kind, id))

def playlist_url(id, token):
    url = "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet%2CcontentDetails&maxResults="+ str(PAGE_SIZE) +"&playlistId="+id+"&key="+API_KEY
    return url + (("&pageToken=" + token) if token else "")

def search_url(query):
    return "https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=10&type=video,channel&q=%s&key=%s" % (query, API_KEY)

def uploads_id(channel):
    return channel['items'][0]['contentDetails']['relatedPlaylists']['uploads']

def extract_channel_id(channel):
    return channel['items'][0]['id'] if 'items' in channel and channel['items'] and 'id' in channel['items'][0] else None 

def extract_channel_name(channel):
    return channel['items'][0]['snippet']['title']

def extract_video_id(video):
    return video['contentDetails']['videoId']

def is_video(video):
    return ('videoId' in video['contentDetails'])

def extract_original_subs(subtitles):
    return map(lambda x: x[1], [i for sub in subtitles for i in sub])

def extract_english_subs(subtitles):
    return map(lambda x: x[2] if len(x) == 3 and x[2] else x[1], [i for sub in subtitles for i in sub])

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

def is_url(url):
    try:
        URLValidator()(url)
        return True
    except ValidationError:
        return False

def user_input_info(user_input):
    if is_url(user_input):
        parsed_url = urlparse(user_input)
        if parsed_url.netloc in ["www.youtube.com", "youtube.com"] and parsed_url.path:
            if parsed_url.path == "/watch":
                params = parse_qs(parsed_url.query)
                return ('video', params['v'][0])
            elif parsed_url.path.startswith("/user/") or parsed_url.path.startswith("/channel/"):
                split_path = parsed_url.path.split('/')
                if len(split_path) > 2:
                    return (split_path[1], split_path[2])
    else:
        return ('user', user_input)

def db_sub_to_runtime(record):
    return (
        record.video_id
        , (record.subtitle_original_lang, record.subtitle_original_formatted, record.subtitle_original)
        , ('en', record.subtitle_translated_formatted, record.subtitle_translated) if record.subtitle_translated_formatted else None
    )

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

def split_array(arr, elems_per_array):
    return [arr[i:i+elems_per_array] for i in range(0, len(arr), elems_per_array)]

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

def words_frequency(subtitles, stopwords, acc):
    def sort_words_by_freq(words):
        return sorted(words.items(), key=lambda v: v[1], reverse=True)

    def rm_stop_words(subtitle):
        regex = r'\b('+b'|'.join( stopwords[subtitle[0]] ).decode('utf-8')+r')\b'
        sub_clean_1 = re.sub('[\,\.\(\)\[\]\*-\:]', ' ', subtitle[1])
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

    def process_subs(subtitles, acc):
        words = acc
        for subtitle in subtitles:
            clean_subtitle = rm_stop_words(subtitle)
            words = count_words(clean_subtitle, words)
        return words
    words = process_subs(subtitles, acc)
    return sort_words_by_freq(words)[0:100]

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

def start(data):
    user_input_kind, user_input_id = user_input_info(urllib.unquote(data['url']))
    accurate = 'accurate' in data and data['accurate'].lower() == "true"
    if user_input_kind and user_input_id:
        if user_input_kind in ['channel', 'user']:
            channel = get_channel(user_input_kind, user_input_id)
            channel_id = extract_channel_id(channel)
            if channel_id is None:
              search_json = get_json( search_url( user_input_id ) )
              yield json.dumps(search_json)
	      yield " " * 1024
	      raise StopIteration
            channel_db = Channels.objects.filter(channel_id=channel_id)
            if channel_db.exists() and not accurate:
                yield json.dumps(channel_db[0].words_count[0:TOP_WORDS_SIZE])
                yield " " * 1024
                raise StopIteration 
            items = get_playlist(channel)
            channel_video_ids = [extract_video_id(item) for item in items if is_video(item)]
            video_ids = [video_id for video_id in channel_video_ids if not Videos.objects.filter(video_id=video_id).exists()]
            video_ids_in_db = list(set(channel_video_ids)^set(video_ids))
        elif user_input_kind == 'video':
            video_db = Videos.objects.filter(video_id=user_input_id)
            if video_db.exists() and not accurate:
                yield json.dumps(video_db[0].words_count[0:TOP_WORDS_SIZE])
                yield " " * 1024
                raise StopIteration 
            video_ids = [user_input_id]

        video_ids_chunks = split_array(video_ids, 20)
        video_ids_chunks_len = len(video_ids_chunks)
        video_ids_in_db_chunks = split_array(video_ids_in_db, 20) if video_ids_in_db else []
        video_ids_in_db_chunks_len = len(video_ids_in_db_chunks)
        frequent_words = {}
        for chunk_index, video_ids_chunk in enumerate(video_ids_chunks):
            subtitles_from_db = [
                db_sub_to_runtime(Videos.objects.get(video_id=video_id)) for video_id in video_ids_in_db_chunks[chunk_index]
            ] if video_ids_in_db_chunks and video_ids_in_db_chunks_len > chunk_index else []

            yield '%.0f%%' % (((chunk_index+1)*100)/float(video_ids_chunks_len))
            yield " " * 1024
            print'APP: Processing Chunk %d/%d' % (chunk_index+1, video_ids_chunks_len)
            video_ids_len = len(video_ids_chunk)
            manual_sub_langs = grequests.map(
                [ get_manual_sub_langs(i, index, video_ids_len) for index, i in enumerate(video_ids_chunk) ], size=50)

            url_manual_subs, url_manual_subs_non_en, video_ids_no_manual_subs = (
                split_results([make_manual_sub(video_id, manual_sub_langs[index].text) for index, video_id in enumerate(video_ids_chunk) if manual_sub_langs[index]]) )

            video_ids_no_manual_subs_len = len(video_ids_no_manual_subs)
            videos_pages = grequests.map(
                [ get_video_page(i, index, video_ids_no_manual_subs_len) for index, i in enumerate(video_ids_no_manual_subs) ], size=50)

            url_auto_subs, url_auto_subs_non_en, video_ids_no_auto_subs = (
                split_results([make_auto_sub(video_id, videos_pages[index].text) for index, video_id in enumerate(video_ids_no_manual_subs) if videos_pages[index] ]) )

            url_manual_subs_len = len(url_manual_subs)
            url_auto_subs_len = len(url_auto_subs)
            manual_subs_pages = grequests.map(
                [ greq_get_text(sub[1][1], index, url_manual_subs_len) for index, sub in enumerate(url_manual_subs) ], size=50)
            auto_subs_pages = grequests.map(
                [ greq_get_text(sub[1][1], index, url_auto_subs_len) for index, sub in enumerate(url_auto_subs) ], size=50)

            manual_subs, auto_subs = tuple(
                [ ( sub[0]
                  , ( sub[1][0]
                    , format_subtitles( (manual_subs_pages if cat_ind is 0 else auto_subs_pages)[index].text )
                    , (manual_subs_pages if cat_ind is 0 else auto_subs_pages)[index].text
                    )
                  ) for index, sub in enumerate(sub_cat)
                  if (manual_subs_pages if cat_ind is 0 else auto_subs_pages)[index]
                ] for cat_ind, sub_cat in enumerate( (url_manual_subs, url_auto_subs) ) )

            url_manual_subs_non_en_len = len(url_manual_subs_non_en)
            url_auto_subs_non_en_len = len(url_auto_subs_non_en)

            manual_subs_non_en_pages = grequests.map(
                [ greq_get_text(sub[1][1], index, url_manual_subs_non_en_len) for index, sub in enumerate(url_manual_subs_non_en) ], size=50)
            manual_subs_non_en_trans_pages = grequests.map(
                [ greq_get_text(sub[2][1], index, url_manual_subs_non_en_len) for index, sub in enumerate(url_manual_subs_non_en) ], size=50)
            auto_subs_non_en_pages = grequests.map(
                [ greq_get_text(sub[1][1], index, url_auto_subs_non_en_len) for index, sub in enumerate(url_auto_subs_non_en) ], size=50)
            auto_subs_non_en_trans_pages = grequests.map(
                [ greq_get_text(sub[2][1], index, url_auto_subs_non_en_len) for index, sub in enumerate(url_auto_subs_non_en) ], size=50)

            manual_subs_non_en, auto_subs_non_en = tuple(
                [
                    ( sub[0]
                    , ( sub[1][0]
                        , format_subtitles( (manual_subs_non_en_pages if cat_ind is 0 else auto_subs_non_en_pages)[index].text )
                        , (manual_subs_non_en_pages if cat_ind is 0 else auto_subs_non_en_pages)[index].text )
                    , ( sub[2][0]
                        , format_subtitles( (manual_subs_non_en_trans_pages if cat_ind is 0 else auto_subs_non_en_trans_pages)[index].text )
                        , (manual_subs_non_en_trans_pages if cat_ind is 0 else auto_subs_non_en_trans_pages)[index].text )
                    )
                    for index, sub in enumerate(sub_cat)
                    if (manual_subs_non_en_pages if cat_ind is 0 else auto_subs_non_en_pages)[index]
                        and (manual_subs_non_en_trans_pages if cat_ind is 0 else auto_subs_non_en_trans_pages)[index]
                ] for cat_ind, sub_cat in enumerate( (url_manual_subs_non_en, url_auto_subs_non_en) ) )

            subtitles = (manual_subs, manual_subs_non_en, auto_subs, auto_subs_non_en, subtitles_from_db)
            if subtitles[0] or subtitles[1] or subtitles[2] or subtitles[3] or subtitles[4]:
                original_subs = extract_original_subs(subtitles)
                english_subs = extract_english_subs(subtitles)
                subs_pages = manual_subs_pages + auto_subs_pages + manual_subs_non_en_pages + auto_subs_non_en_pages
                translated_subs_pages = manual_subs_non_en_trans_pages + auto_subs_non_en_trans_pages
                stopwords = get_stopwords( extract_langs ( original_subs ) )
                frequent_words = words_frequency( original_subs, stopwords, dict(frequent_words) )
                if user_input_kind in ['channel', 'user']:
                    for sub_category in subtitles:
                        for sub in sub_category:
                            Videos.objects.update_or_create(
                                video_id=sub[0]
                                , defaults={
                                    'subtitle_original': sub[1][2]
                                    , 'subtitle_original_formatted': sub[1][1]
                                    , 'subtitle_original_lang': sub[1][0]
                                    , 'subtitle_translated': sub[2][2] if len(sub) == 3 and sub[2] else ''
                                    , 'subtitle_translated_formatted': sub[2][1] if len(sub) == 3 and sub[2] else ''
                                    , 'words_count': words_frequency( [sub[1]], stopwords, {} )
                                }
                            )
                elif user_input_kind == 'video':
                    Videos.objects.update_or_create(
                        video_id=video_ids[0]
                        , defaults={
                            'subtitle_original': subs_pages[0].text if subs_pages else ''
                            , 'subtitle_original_formatted': original_subs[0][1]
                            , 'subtitle_original_lang': original_subs[0][0]
                            , 'subtitle_translated': translated_subs_pages[0].text if translated_subs_pages else ''
                            , 'subtitle_translated_formatted': format_subtitles(translated_subs_pages[0].text) if translated_subs_pages else ''
                            , 'words_count': frequent_words
                        }
                    )
                # beautiful_stats = beautify_stats ( get_subtitle_statistics( english_subs[0][1] ) )
        if frequent_words:
            if user_input_kind in ['channel', 'user']:
                Channels.objects.update_or_create(
                    channel_id=channel_id
                    , defaults={
                        'video_ids': video_ids_in_db + video_ids
                        , 'words_count': frequent_words
                    }
                )
            yield json.dumps(frequent_words[0:TOP_WORDS_SIZE])
            yield " " * 1024
            raise StopIteration
        yield json.dumps([["No subtitles in "+ user_input_kind +" to analyse: ", user_input_id]])

        yield " " * 1024
        raise StopIteration
    else:
        yield json.dumps([["Please input a youtube channel/video url", ""]])
        yield " " * 1024
        raise StopIteration

@condition(etag_func=None)
def main(request, args):
    res = StreamingHttpResponse(start(request.GET))
    res['Content-Encoding'] = 'identity'
    return res
