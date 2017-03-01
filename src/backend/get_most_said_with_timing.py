
import django
django.setup()

import sys, os
from youstat.models import Channels, Videos
from youstat import apps
from bs4 import BeautifulSoup

SEARCH_WORD = sys.argv[2]
URL = sys.argv[1]

user_input_kind, user_input_id = apps.user_input_info(URL)
if user_input_kind and user_input_id:
        if user_input_kind in ['channel', 'user']:
            channel = apps.get_channel(user_input_kind, user_input_id)
channel_username = "".join(x for x in apps.extract_channel_name(channel) if x.isalnum())
CHANNEL_ID = apps.extract_channel_id(channel)
apps.start({'url': URL, 'accurate': 'false'})


CHANNEL = Channels.objects.get(channel_id=CHANNEL_ID)
FOLDER =  "video_bot/"+ channel_username + '/' + SEARCH_WORD.strip() +  "/"
videos_with_subtitles = []
timings = []


for video_id in CHANNEL.video_ids:
	video = Videos.objects.filter(video_id=video_id)
	if video.exists():
		videos_with_subtitles.append((video_id, video[0].subtitle_original))

for video_with_subtitles in videos_with_subtitles:
	if SEARCH_WORD in video_with_subtitles[1]:
		soup = BeautifulSoup(video_with_subtitles[1], 'html.parser')
		timing = map(lambda x: (x.get('dur'), x.get('start'), x.string), filter(lambda x: SEARCH_WORD in x.string, soup.find_all('text')))
		if timing:
			timings.append((video_with_subtitles[0], timing))

print "mkdir -p " + FOLDER + ';'
files = []
for timing in timings:
	occurence = 0
	for time in timing[1]:
		print "ffmpeg -n -ss "+str(float(time[1]))+" -i $(youtube-dl -f mp4 --get-url "+"https://www.youtube.com/watch?v=" + timing[0]+") -t "+str(float(time[0]))+" " + FOLDER + timing[0]+"_"+str(occurence)+".mp4;"
		files.append(FOLDER + timing[0]+"_"+str(occurence)+".mp4")
		occurence += 1
print ';'.join(['ffmpeg -i '+file+' -map 0 -c copy -f mpegts '+file+'.ts' for file in files])
print 'ffmpeg -i "concat:'+'|'.join([file+'.ts' for file in files])+'" -c copy -absf aac_adtstoasc '+FOLDER+'output.mp4'
print "python video_bot/get_youtuber_img.py "+channel_username
print "python video_bot/add_text_to_thumbnail.py Pictures/"+channel_username+"/ "+SEARCH_WORD+"!"
print "echo "+FOLDER