
import django
django.setup()

import sys, re, os, subprocess
from youstat.models import Channels, Videos
from youstat import apps
from bs4 import BeautifulSoup
from progress.bar import Bar


PART_LENGTH = 3.5 # in min

def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)

def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]

def extract_search_occurence_duration(video_w_subs):
    return map(
        lambda x: (x.get('dur'), x.get('start'), x.string),
        filter(
            lambda x: re.findall(r'\b'+SEARCH_WORD+r'\b', x.string),
            BeautifulSoup(video_w_subs[1], 'html.parser').find_all('text')) )

def make_part_folder_path(output_folder, part):
    return os.path.abspath( os.path.join(output_folder, "part" + str(part)) )

def make_mp4_to_ts_conv_cmd(mp4file):
    return '/usr/local/bin/ffmpeg -i '+mp4file+' -map 0 -n -c copy -f mpegts '+mp4file+'.ts'

def make_mp4_to_ts_conv_cmds(part_dir_path):
    return [
        make_mp4_to_ts_conv_cmd(mp4file)
            for mp4file in listdir_fullpath( part_dir_path )
            if mp4file.split('.')[-1] == 'mp4' and os.path.isdir( part_dir_path )
    ]

def make_ffmpeg_download_part_cmd(part_video):
    return "/usr/local/bin/ffmpeg -n -ss " +part_video[1] + \
    " -i $(/usr/local/bin/youtube-dl -f mp4 --get-url https://www.youtube.com/watch?v=" + part_video[0]+")" + \
    " -t "+ str(float(part_video[2])) + " " + part_video[5] if not os.path.exists(part_video[5]) else ''

def make_ffmpeg_download_part_cmds(part_videos):
    return [
        cmd for video in part_videos for cmd in [make_ffmpeg_download_part_cmd(video)] if cmd
    ]

def make_concat_videos_cmd(part_dir_path):
    return "ffmpeg -y -i 'concat:" + \
        '|'.join([tsfile for tsfile in os.listdir( part_dir_path ) if tsfile.split('.')[-1] == 'ts']) + \
        "' -c copy -absf aac_adtstoasc output.mp4"

def make_upload_to_youtube_cmd(part, channel_username, part_dir_path):
    part_str = ' - Part '+str(part) if part > 1 else ''
    return 'PYTHONPATH=./video_bot/youtube-upload-master ' + \
        'python ./video_bot/youtube-upload-master/bin/youtube-upload ' + \
        '--client-secrets=./video_bot/client_secret.json ' + \
        '--title="'+channel_username.upper()+' All "'+SEARCH_WORD.capitalize() + '\!" Moments"' +part_str+' ' + \
        '--description="Which youtuber would you like to see next, and saying which word?" ' + \
        '--category=Entertainment ' + \
        '--tags="'+channel_username.lower()+',evexo,youtubers saying,evex o,WORDS ON YOUTUBERS,'+channel_username.lower()+' saying '+SEARCH_WORD+', saying '+SEARCH_WORD+'" ' + \
        '--default-language="en" ' + \
        '--playlist "'+channel_username.lower()+'" ' + \
        '--privacy public ' + \
        os.path.join(part_dir_path, 'output.mp4')

def main(SEARCH_WORD, URL):
    user_input_kind, user_input_id = apps.user_input_info(URL)
    if user_input_kind and user_input_id:
        if user_input_kind in ['channel', 'user']:
            channel = apps.get_channel(user_input_kind, user_input_id)
            channel_username = "".join(x for x in apps.extract_channel_name(channel) if x.isalnum())
            CHANNEL_ID = apps.extract_channel_id(channel)
            apps.start({'url': URL, 'accurate': 'false'})
            CHANNEL_DB = Channels.objects.get(channel_id=CHANNEL_ID)

    output_folder =  os.path.abspath( os.path.join( "video_bot", channel_username, SEARCH_WORD.strip() ) )

    videos_w_subs = [
        ( video_id, video[0].subtitle_original )
        for video_id in CHANNEL_DB.video_ids for video in [Videos.objects.filter(video_id=video_id)] if video.exists() ]

    occurences = []
    for video_w_subs in videos_w_subs:
        if SEARCH_WORD in video_w_subs[1]:
            occurs = extract_search_occurence_duration(video_w_subs) 
            if occurs:
                occurences.append((video_w_subs[0], occurs))
       
    duration = 0
    parts_videos = []
    for vid_occurences in occurences:
        for occur_index, occur in enumerate(vid_occurences[1]):
            duration += float(occur[0])
            part = int(duration / (PART_LENGTH * 60)) + 1 # min part is 1
            parts_videos.append((
                vid_occurences[0]
                , occur[1]
                , occur[0]
                , occur_index
                , part
                , os.path.abspath( os.path.join(
                    output_folder
                    , "part" + str(part)
                    , vid_occurences[0]+"_"+str(occur_index)+".mp4" )
                )
            ))

    FNULL = open(os.devnull, 'w')
    parts = range(1, part+1)
    for part in parts:
        part_videos = [video for video in parts_videos if video[4] == part]

        part_dir_path = make_part_folder_path( output_folder, part )
        os.makedirs( part_dir_path ) if not os.path.exists( part_dir_path ) else ''

        dl_cmds = make_ffmpeg_download_part_cmds(part_videos)
        dl_part_videos_count = len(dl_cmds)
        bar = Bar('Part %d: Downloading videos' % (part), max=dl_part_videos_count)
        for i, cmd in enumerate(dl_cmds):
            subprocess.call( cmd, stdout=FNULL, stderr=subprocess.STDOUT, shell=True )
            bar.next()
        bar.finish()

        conv_cmds = make_mp4_to_ts_conv_cmds(part_dir_path)
        part_videos_count = len(conv_cmds)
        bar = Bar("Part %d: Converting video(mp4 -> ts)" % (part), max=part_videos_count)
        for i, cmd in enumerate(conv_cmds):
            subprocess.call( cmd, stdout=FNULL, stderr=subprocess.STDOUT, shell=True )
            bar.next()
        bar.finish()

        print "Part %d: Merging %d videos" % (part, part_videos_count)
        subprocess.call( make_concat_videos_cmd(part_dir_path), cwd=part_dir_path, stdout=FNULL, stderr=subprocess.STDOUT, shell=True )

        print "Part %d: Uploading to youtube" % (part)
        subprocess.call( make_upload_to_youtube_cmd(part, channel_username, part_dir_path), stdout=FNULL, stderr=subprocess.STDOUT, shell=True)

if __name__ == "__main__":
    SEARCH_WORD = sys.argv[2]
    URL = sys.argv[1]
    main(SEARCH_WORD, URL)
