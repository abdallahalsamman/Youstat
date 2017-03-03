
import django
django.setup()

import sys, re, os
from youstat.models import Channels, Videos
from youstat import apps
from bs4 import BeautifulSoup

SEARCH_WORD = sys.argv[2]
URL = sys.argv[1]

def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)

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
        timing = map(lambda x: (x.get('dur'), x.get('start'), x.string), filter(lambda x: re.findall(r'\b'+SEARCH_WORD+r'\b', x.string), soup.find_all('text')))
        if timing:
            timings.append((video_with_subtitles[0], timing))

duration = 0
part = 1
print "mkdir -p " + FOLDER + '/part'+str(part)+';'
for timing in timings:
    occurence = 0
    if duration >= (60 * 4):
        duration = 0
        part += 1
        print "mkdir -p " + FOLDER + '/part'+str(part)+';'
    for time in timing[1]:
        duration += float(time[0])
        if find(timing[0]+"_"+str(occurence)+".mp4", FOLDER):
            continue
        print "ffmpeg -n -ss "+str(float(time[1]))+" -i $(youtube-dl -f mp4 --get-url "+"https://www.youtube.com/watch?v=" + timing[0]+") -t "+str(float(time[0]))+" " + FOLDER + "part" + str(part) + "/" + timing[0]+"_"+str(occurence)+".mp4;"
        occurence += 1

partsExist = ' - Part `echo $part | sed \'s/[^0-9]//g\'`' if part > 1 else ''
print "python -c \"import os; print ''.join([';'.join(['ffmpeg -i "+FOLDER+"'+folder+'/'+file+' -map 0 -n -c copy -f mpegts "+FOLDER+"'+folder+'/'+file+'.ts' for file in os.listdir('"+FOLDER+"'+folder) if file.split('.')[-1] == 'mp4']) for folder in os.listdir('"+FOLDER+"') if os.path.isdir('"+FOLDER+"'+folder)])\" | sh"
print 'for FOLDER in `ls -d1 '+FOLDER+'*/`; do ffmpeg -y -i "concat:$(perl -e \'print join("|", @ARGV);\' $FOLDER*.ts)" -c copy -absf aac_adtstoasc $FOLDER/output.mp4; done;'
print "python video_bot/get_youtuber_img.py "+channel_username
print "python video_bot/add_text_to_thumbnail.py Pictures/"+channel_username+"/ "+SEARCH_WORD+"!"
print '\
for part in `ls -d1 '+FOLDER+'/*/ | xargs -n 1 basename`; do \
PYTHONPATH=./video_bot/youtube-upload-master \
python video_bot/youtube-upload-master/bin/youtube-upload \
--client-secrets=video_bot/client_secret.json \
--title="'+channel_username.capitalize()+' saying '+SEARCH_WORD+partsExist+'" \
--description="This is ' + channel_username.lower() + ' saying '+SEARCH_WORD+' compilation\
\\n\\nWhich youtuber would you like to see next, and saying which word?" \
--category=Entertainment \
--tags="'+channel_username.lower()+',evexo,youtubers saying,evex o,WORDS ON YOUTUBERS,'+channel_username.lower()+' saying '+SEARCH_WORD+', saying '+SEARCH_WORD+'" \
--default-language="en" \
--playlist "'+channel_username.lower()+'" \
--privacy unlisted \
'+FOLDER+'/$part/output.mp4;\
done;'
print "echo "+FOLDER
