#all functions needed for youtube videos manipulation

import os
import re
from shutil import copyfile
import subprocess
from datetime import timedelta

def youtube_vmaf_split (path,segment_duration):
    #split best resolution video in given path to a segments of a given duration required for vmaf calculation
    youtube_path=os.path.join(path,"vmaf")
    if not os.path.exists(youtube_path):
        os.makedirs(youtube_path)
    #convert integer seconds to a timestamp
    timestamp=str(timedelta(seconds=segment_duration))
    #find best resolution video in youtube_path
    for file in os.listdir(youtube_path):
        filename = os.fsdecode(file)
        if filename.startswith("bestres"):
            title_path = os.path.join(youtube_path,filename)
            if filename.endswith("mp4"):
                newname="inited_max"+filename.removesuffix('.mp4')+'segment%03d.mkv'
            else:
                newname = "inited_max"+filename.removesuffix('.mkv') + 'segment%03d.mkv'
            newpath=os.path.join(youtube_path,newname)
            #use ffmpeg to split video in segments of a given duration
            try:
                result = subprocess.run(['ffmpeg', '-i', title_path, '-c', 'copy', '-map', '0', '-segment_time', timestamp, '-f', 'segment', '-reset_timestamps', '1' , newpath
                                 ],
                                stdout=subprocess.PIPE).stdout.decode('utf-8')
            except:
                print("ERROR happened")
                pass
            break


def download_maxres_youtube_movie(path, url, yt_movie_title):
    #downloads best available resolutions of a youtube video from a given url to a specified folder
    #best res is needed as reference for metrics calculation
    paths = os.path.join(path, "vmaf")
    if not os.path.exists(paths):
        os.makedirs(paths)
    name="bestres"+yt_movie_title
    name=name.replace("\n", "")
    youtube_path=os.path.join(paths,name)
    #use youtube-dl to download a movie, if you do not specify resolution, best is downloaded by default
    try:
        result = subprocess.run(['youtube-dl', url,'-o', youtube_path
                                 ],
                                stdout=subprocess.PIPE).stdout.decode('utf-8')
    except:
        print(" not found!")
        pass

def youtube_split(path,segment_duration,youtube_videos):
    #split every video in given path to a segments of a given duration
    youtube_path=os.path.join(path,"youtube")
    timestamp=str(timedelta(seconds=segment_duration))
    #for every youtube video downloaded in download_youtube_movies do split
    for youtube_title in youtube_videos:
        title_path = os.path.join(youtube_path, youtube_title)
        #check the extension
        if youtube_title.endswith("mp4"):
            newname="merged"+youtube_title.removesuffix('.mp4')+'segment%03d.mkv'
        else:
            newname = "merged"+youtube_title.removesuffix('.mkv') + 'segment%03d.mkv'
        newpath = os.path.join(youtube_path,newname)
        #use ffmpeg to split videos into segment of segment_duration
        try:
            result = subprocess.run(['ffmpeg', '-i', title_path, '-c', 'copy', '-map', '0', '-segment_time', timestamp, '-f', 'segment', '-reset_timestamps', '1' , newpath
                                 ],
                                stdout=subprocess.PIPE).stdout.decode('utf-8')
        except:
            print("ERROR happened")
            pass

def download_youtube_movies(path, url, list_seg_res_csv, youtube_videos, yt_movie_title):
    #downloads all available resolutions (if not available, then next lower) of a youtube videos to a specified folder
    paths = os.path.join(path, "youtube")
    if not os.path.exists(paths):
        os.makedirs(paths)
    #for every needed resolution stored in list_seg_res_csv - which is parsed from log
    for height in list_seg_res_csv:
        #if there is no available resolution, download next lower res
        subrl = "bestvideo[height<="+str(height) + "]+bestaudio/best[height<=" + str(height) +"]"
        name = yt_movie_title+str(height)
        name = name.replace("\n", "")
        youtube_path=os.path.join(paths,name)
        #use youtube-dl to download segments to a specified path
        try:
            result = subprocess.run(['youtube-dl', '-f', subrl, '-R', '2', url,'-o', youtube_path
                                 ],
                                stdout=subprocess.PIPE).stdout.decode('utf-8')
        except:
            print(height + " not found!")
            pass
    #save downloaded file names in youtube_videos list to use in splitting functions
    for file in os.listdir(paths):
        filename = os.fsdecode(file)
        youtube_videos.append(filename)
    return youtube_videos

def get_youtube_title(url):
    # gets youtube movie title and store it to variable
    result = subprocess.run(['youtube-dl', '-e',  url
                         ],
                        stdout=subprocess.PIPE).stdout.decode('utf-8')
    #delete blank spaces
    youtube_movie_title=result.replace(" ", "")
    return youtube_movie_title

def copy_youtube_segments(path, destination, youtube_segments_dict):
    # copy youtube segments from given path to destination path
    if not os.path.exists(destination):
        os.makedirs(destination)
    if not os.path.exists(path):
        os.makedirs(path)
    for key in youtube_segments_dict:
        #all needed segments are saved in youtube_segments_dict in  read_replevels_log function
        height = youtube_segments_dict.get(key)
        for file in os.listdir(path):
            filename = os.fsdecode(file)
            #resolution height is saved in name string
            string_height= re.search(r'[^\d]*(\d+)',  filename).group(1)
            #.mkv extension is needed
            if filename.endswith(".mp4"):
                continue
            string_segment = re.search(r'(?:\d+)(?!.*\d)', filename)
            string_segment=string_segment.group(0)
            #string_segment+1 because splitted youtube segments names start from 0, and log segments start from 1
            if (int(string_height) ==height) and (int(string_segment)+1==key):
                path_to_file = os.path.join(path, filename)
                new_destination = os.path.join(destination, filename)
                copyfile(path_to_file, new_destination)
