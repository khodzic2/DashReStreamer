#!/usr/bin/env python
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License
#    as published by the Free Software Foundation; either version 2
#    of the License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
#    02110-1301, USA.

import pandas as pd
import os
import re
from shutil import copyfile
import subprocess
import argparse
from mpegdash.parser import MPEGDASHParser
import configparser
import platform
from datetime import datetime

vmaf_list = []
vmaf_list1 = []
vmaf_list2 = []
vmaf_list3 = []

list_rep_mpd = []
list_seg_rep_csv = dict()
list_inter_names = dict()
list_stall_values = dict()
list_mpd_audio = dict()
list_mpd_video = dict()
list_resolutions = dict()

# get the current date
date = datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p")

#variable to store movie name
movie_name=""


def fill_resolution_dict():
    list_resolutions["720p"] = [1280, 720]
    list_resolutions["1080p"] = [1920, 1080]
    list_resolutions["1440p"] = [2560, 1440]
    list_resolutions["2160p"] = [3840, 2160]


def read_replevels_log(path, bitrate_column_name, index_column_name, delimiter):
    # read log and save bitrates and indexes

    if delimiter == 'tab':
        df = pd.read_csv(path, sep='\t')
    elif delimiter == 'csv':
        df = pd.read_csv(path)
        # removes whitespaces from column names
    df.columns = df.columns.str.replace(' ', '')
    for index, row in df.iterrows():
        # maps index to bitrate
        list_seg_rep_csv[row[index_column_name]] = row[bitrate_column_name]


def read_stalls_log(path, stall_column_name, index_column_name, delimiter):
    # read log and save stalls and indexes
    if delimiter == 'tab':
        df = pd.read_csv(path, sep='\t')
    elif delimiter == 'csv':
        df = pd.read_csv(path)
    # removes whitespaces from column names
    df.columns = df.columns.str.replace(' ', '')
    # maps chunk index to stall durations
    for index, row in (df.loc[df[stall_column_name] > 0]).iterrows():
        list_stall_values[row[index_column_name]] = row[stall_column_name]


def copy_init_file(path, newfolder_path):
    # copy init file from source to destination
    if not os.path.exists(newfolder_path):
        os.makedirs(newfolder_path)
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if filename.__contains__("init"):
            filepath = os.path.join(path, filename)
            filenewpath = os.path.join(newfolder_path, filename)
            copyfile(filepath, filenewpath)


def copy_video_segments(path, destination):
    # copy video segments from log to destination
    for key in list_seg_rep_csv:
        for subdir in os.walk(path):
            ime = list_seg_rep_csv.get(key)
            m = re.search(r'([0-9]+)\w+$', subdir[0])
            rep_level = -1
            if m:
                rep_level = int(m.group(1))
            # bitrate mapping +-5%
            if rep_level * 0.95 <= ime <= rep_level * 1.05:
                for file in os.listdir(subdir[0]):
                    filename = os.fsdecode(file)
                    s = "segment" + str(key) + ".m4s"
                    if filename.__contains__(s):
                        path_to_file = os.path.join(subdir[0], filename)
                        new_destination = os.path.join(destination, filename)
                        copyfile(path_to_file, new_destination)


def copy_audio_segments(path, destination):
    # copies audio log segments from source to destination
    for key in list_seg_rep_csv:
        for file in os.listdir(path):
            filename = os.fsdecode(file)
            if str(filename).endswith("_" + str(key) + '.m4s'):
                path_to_file = os.path.join(path, filename)
                new_destination = os.path.join(destination, filename)
                copyfile(path_to_file, new_destination)


def prepare_video_init(path, metrics):
    # combines video segments with init file
    init = ""
    osystem = platform.system()
    if osystem == 'Windows':
        suffix = "type "
    elif osystem == 'Linux':
        suffix = "cat "
    # add for mac :)
    else:
        suffix = "cat "
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).__contains__("dash_init"):
            init = filename
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).__contains__("kbps"):
            m4s = filename
            m4s2 = m4s.split(".m4s")[0]  # .removesuffix(".m4s")
            path_init = os.path.join(path, init)
            path_file = os.path.join(path, m4s)
            path_final = os.path.join(path, "inited" + m4s2 + ".mp4")
            komanda = suffix + path_init + " " + path_file + " > " + path_final
            os.system(komanda)
            #if metrics are to be calculated copy all needed segments to vmaf folder
            if metrics == "True":
                vmaf_path = os.path.join(path, "vmaf", "inited" + m4s2 + ".mp4" )
                copyfile(path_final, vmaf_path)


def prepare_audio_init(path):
    # combines audio segments with init file
    init = ""
    suffix = ""
    osystem = platform.system()
    if osystem == 'Windows':
        suffix = "type "
    elif osystem == 'Linux':
        suffix = "cat "
    else:
        suffix = "cat "
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).__contains__("segment_init"):
            init = filename
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if not (str(filename).__contains__("segment_init")) and str(filename).__contains__("segment") and not (
                str(filename).__contains__("kbps")):
            m4s = filename
            m4s2 = m4s.split(".m4s")[0]  # .removesuffix(".m4s")
            path_init = os.path.join(path, init)
            path_file = os.path.join(path, m4s)
            path_final = os.path.join(path, "inited" + m4s2 + ".avi")
            komanda = suffix + path_init + " " + path_file + " > " + path_final
            os.system(komanda)


def concat_audio_video_ffmpeg(path, auto_scale, resolution):
    # combines audio and video segments into one file, it rescales resolution to max if auto_scale option is 1, if 2 then resolution is read
    audio = ""
    m4s = ""
    segment = ""
    x = tuple
    if auto_scale == 1:
        x = helper_get_max_resolution_fps_duration(path, "inited")
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).endswith("avi") and str(filename).startswith("inited"):
            segment = re.search("\w+_([0-9]+)", filename).group(1)
            audio = str(filename)
            for file2 in os.listdir(path):
                filename2 = os.fsdecode(file2)
                if str(filename2).endswith("segment" + segment + ".mp4") and str(filename2).startswith("inited"):
                    video = str(filename2)
                    path_video = os.path.join(path, video)
                    path_audio = os.path.join(path, audio)
                    path_i_video = os.path.join(path, "i" + video.split(".mp4")[0] + ".mkv")
                    path_final = os.path.join(path, "merged" + video.split(".mp4")[0] + ".mkv")
                    komanda = "ffmpeg -fflags +genpts -i " + path_video + " -i " + path_audio + " -c copy " + path_i_video
                    os.system(komanda)
                    if auto_scale == 0:
                        copyfile(path_i_video, path_final)
                    if auto_scale == 1:
                        komanda4 = 'ffmpeg -i ' + path_i_video + ' -vf scale=' + str(x[1]) + ':' + str(
                            x[3]) + " -c:a copy " + path_final
                        os.system(komanda4)
                    if auto_scale == 2:
                        komanda4 = 'ffmpeg -i ' + path_i_video + ' -vf scale=' + str(
                            list_resolutions[resolution][0]) + ':' + str(
                            list_resolutions[resolution][1]) + " -c:a copy " + path_final
                        os.system(komanda4)


def helper_get_max_resolution_fps_duration(path, prefix):
    # function to get resolution, fps and duration of a highest resolution segment using ffprobe
    suffix = ""
    if prefix == "inited":
        suffix = ".mp4"
    if prefix == "merged":
        suffix = ".mkv"
    if prefix == "inited_max":
        suffix = ".mp4"

    list_inter_names2 = dict()
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).endswith(suffix) and str(filename).startswith(prefix):
            segment = re.search("(\d+)(?!.*\d)", filename.split(suffix)[0]).group(1)  # .removesuffix(suffix)).group(1)
            list_inter_names2[int(segment)] = str(filename)
    sorted_dict = dict(sorted(list_inter_names2.items()))
    segment = (
        sorted_dict[
            list(list_seg_rep_csv.keys())[list(list_seg_rep_csv.values()).index(max(list_seg_rep_csv.values()))]])

    komanda = "ffmpeg -i " + os.path.join(path, segment) + " -codec copy " + os.path.join(path, segment.split(".mkv")[
        0] + ".mp4")  # .removesuffix(".mkv")
    segment_path = os.path.join(path, segment)
    if suffix == ".mkv":
        os.system(komanda)
        segment_path = os.path.join(path, segment.split(".mkv")[0] + ".mp4")  # .removesuffix(".mkv")

    result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                             'stream=width,height,avg_frame_rate,duration', '-of',
                             'default=noprint_wrappers=1', segment_path
                             ],
                            stdout=subprocess.PIPE).stdout.decode('utf-8')
    # result = result.split("/1")[0]
    return helper_format_result_string(result)


def helper_format_result_string(result):
    # formats output from ffprobe command
    result = result.replace('\n', '=')
    result = result.replace('\r', '')
    x = result.split('=')
    return x


def helper_segment_list(path):
    # puts all merged mp4 segments in a dictionary -- segment number -- filename
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).endswith(".mkv") and str(filename).startswith("merged"):
            segment = re.search("(\d+)(?!.*\d)", filename.split(".mkv")[0]).group(1)  # .removesuffix(".mkv")
            list_inter_names[int(segment)] = str(filename)
    sorted_dict = dict(sorted(list_inter_names.items()))
    return sorted_dict


def create_stalled_video(path, sorted_dict, key, path_to_gif, duration):
    # creates stalled segments in given path
    stall_duration = 0
    if list_stall_values[key + 1] != 0:
        stall_duration = list_stall_values[key + 1] / 1000
        stall_duration = round(stall_duration, 1)
    newname = str(sorted_dict[key]).split('.mkv')[0] + '.jpg'  # .removesuffix('.mkv')
    jpg_path = os.path.join(path, newname)
    file_path = os.path.join(path, sorted_dict[key])
    komanda = 'ffmpeg -sseof -3 -i ' + file_path + ' -update 1 -q:v 1 ' + jpg_path
    os.system(komanda)
    path_mp4 = os.path.join(path, sorted_dict[key])
    result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                             'stream=width,height,avg_frame_rate,duration', '-of', 'default=noprint_wrappers=1',
                             path_mp4], stdout=subprocess.PIPE).stdout.decode('utf-8')
    x = helper_format_result_string(result)
    result2 = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                              'stream=sample_rate,channel_layout,codec_name', '-of', 'default=noprint_wrappers=1',
                              path_mp4], stdout=subprocess.PIPE).stdout.decode('utf-8')
    y = helper_format_result_string(result2)
    path_mp4s = os.path.join(path, 's' + sorted_dict[key])
    command = 'ffmpeg -loop 1 -i ' + jpg_path + ' -f lavfi -i anullsrc=channel_layout=' + y[5].split('(')[
        0] + ':sample_rate=' + y[3] + ' -t ' + str(stall_duration) + ' -c:a ' + y[1] + ' -c:v libx264 -t ' + str(
        stall_duration) + ' -pix_fmt yuv420p -vf scale=' + x[1] + ':' + x[3] + ' -r ' + (x[5].split('/'))[
                  0] + ' -y ' + path_mp4s
    os.system(command)
    temp_path = os.path.join(path, "temporaryList.txt")
    open(temp_path, 'w').close()
    komanda = ' echo file ' + "'" + path_mp4 + "'" + '  >>  ' + temp_path
    os.system(komanda)
    komanda = ' echo file ' + "'" + path_mp4s + "'" + '  >>  ' + temp_path
    os.system(komanda)
    path_mp4ss = os.path.join(path, 'ss' + sorted_dict[key])
    komanda = 'ffmpeg -f concat -safe 0 -i ' + temp_path + ' -c copy ' + path_mp4ss
    os.system(komanda)
    ss_path = os.path.join(path, 'sss' + sorted_dict[key])
    subkomanda = "'gte(t," + str(duration) + ")'"""
    scale_gif = int(x[1]) // 13
    komanda = 'ffmpeg -i ' + path_mp4ss + ' -ignore_loop 0 -i ' + path_to_gif + ' -filter_complex "[1:v]format=yuva444p,scale=%d:%d,setsar=1,rotate=PI/6:c=black@0:ow=rotw(PI/6):oh=roth(PI/6) [rotate];[0:v][rotate] overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:format=auto:shortest=1:enable=' % (
        scale_gif, scale_gif) + subkomanda + '" -codec:a copy -y ' + ss_path
    os.system(komanda)
    seg_path = os.path.join(path, "segmentList.txt")
    komanda = ' echo file ' + "'" + ss_path + "'" + '  >>  ' + seg_path
    os.system(komanda)
    return x


def concat_video_segments_final(path, path_to_gif, path_to_file):
    # create stalls and merge final video
    sorted_dict = helper_segment_list(path)
    x = helper_get_max_resolution_fps_duration(path, "merged")
    full_path = os.path.join(path, "segmentList.txt")
    for key in sorted_dict:
        if ((key + 1) in list_stall_values.keys()):
            create_stalled_video(path, sorted_dict, key, path_to_gif, float(x[7]))
            continue
        seg_path = os.path.join(path, sorted_dict[key])
        komanda = 'echo file ' + "'" + seg_path + "'" + ' >> ' + full_path
        os.system(komanda)
    if not os.path.exists(path_to_file):
        os.makedirs(path_to_file)
    final_path = os.path.join(path_to_file, path_to_log.split(".")[-2].split(os.sep)[-1] + "_" + "video.mkv")
    komanda = "ffmpeg -f concat -safe 0 -i " + full_path + " -c copy " + final_path
    os.system(komanda)


def clean_folder(path):
    for f in os.listdir(path):
        if os.path.isfile(os.path.join(path, f)):
            os.remove(os.path.join(path, f))


def parse_mpd(mpd_url):
    # parses mpd from given url, and saves all audio and video media links into list_mpd_audio and list_mpd_video dictionaries
    # mpd_url = 'http://cs1dev.ucc.ie/misl/4K_non_copyright_dataset/4_sec/x264/bbb/DASH_Files/full/dash_video_audio.mpd'

    print(mpd_url)

    mpd = MPEGDASHParser.parse(mpd_url)
    inited = False
    global movie_name

    for program_information in mpd.program_informations:
        for title in program_information.titles:
            movie_name = title.text

    for period in mpd.periods:
        for adapt_set in period.adaptation_sets:
            if adapt_set.segment_templates is not None and inited is False:
                # gets audio init file suburl once
                list_mpd_video[0] = adapt_set.segment_templates[0].initialization
                inited = True
            for temp in adapt_set.segment_templates:
                if temp.media is not None:
                    list_mpd_audio[temp.duration] = temp.media

    inited = False
    for period in mpd.periods:
        for adapt_set in period.adaptation_sets:
            for temp in adapt_set.segment_templates:
                if temp.initialization is not None and temp.media is not None and inited is False:
                    # gets video init file suburl once
                    list_mpd_audio[0] = temp.initialization
                    inited = True
            for reps in adapt_set.representations:
                if reps.segment_templates is not None:
                    for temp in reps.segment_templates:
                        if temp.media is not None:
                            list_mpd_video[reps.bandwidth] = temp.media


def download_audio_segments(mpd_url, destination):
    # downloads audio log segments from source to destination, now supports only one audio quality, it can be easily modifed to support more

    # creates folder and opens new file to store all audio segment urls
    if not os.path.exists(destination):
        os.makedirs(destination)
    full_path = os.path.join(destination, "audioSegments.txt")
    open(full_path, 'w')

    # deletes last url part where mpd file name is
    mpd_url2 = mpd_url.rsplit("/", 2)[0]

    # puts audio init url to a file
    komanda = " echo " + mpd_url2 + str(list_mpd_audio[0]).replace(list_mpd_audio[0].rsplit("/", 4)[0],
                                                                   "") + " >> " + full_path
    os.system(komanda)

    # maps segments from log to mpd url and saves it to a file
    for key in list_seg_rep_csv:
        for key2 in list_mpd_audio:
            if key2 != 0:
                substring = str(list_mpd_audio[key2]).replace('$Number$', str(key))
                substring2 = substring.replace(substring.rsplit("/", 4)[0], "")
                komanda = " echo " + mpd_url2 + substring2 + " >> " + full_path
                os.system(komanda)

    # download all audio segments from server to specified location
    osystem = platform.system()
    if osystem == 'Linux':
        komanda = 'wget -i ' + full_path + ' -P ' + destination
    elif osystem == 'Windows':
        os.chdir(destination)
        komanda = 'for /f "tokens=*" %a in (' + full_path + ') do curl -O %a'
    # add option for mac :)
    else:
        komanda = 'wget -i ' + full_path + ' -P ' + destination
    os.system(komanda)


def download_video_segments(mpd_url, destination):
    # downloads video log segments from source to destination
    if not os.path.exists(destination):
        os.makedirs(destination)
    full_path = os.path.join(destination, "videoSegments.txt")
    open(full_path, 'w')

    # deletes last url part where mpd file name is
    mpd_url2 = mpd_url.rsplit("/", 1)[0]

    # copy location to video init file
    # mpd_full_path_ = os.path.join(os.sep,mpd_url2+os.sep, str(list_mpd_video[0]))
    komanda = " echo " + mpd_url2 + "/" + str(list_mpd_video[0]) + " >> " + full_path
    os.system(komanda)

    # for every segment in log, map bandwidth with bandwidth from mpd and save server url of that segment to a file
    for key in list_seg_rep_csv:
        for key2 in list_mpd_video:
            if key2 != 0:
                if key2 / 1000 * 0.95 <= list_seg_rep_csv[key] <= key2 / 1000 * 1.05:
                    substring = str(list_mpd_video[key2]).replace('$Number$', str(key))
                    komanda = " echo " + mpd_url2 + "/" + substring + " >> " + full_path
                    os.system(komanda)

    # download all files to specified location
    osystem = platform.system()
    if osystem == 'Linux':
        komanda = 'wget -i ' + full_path + ' -P ' + destination
    elif osystem == 'Windows':
        os.chdir(destination)
        komanda = 'for /f "tokens=*" %a in (' + full_path + ') do curl -O %a'
    # add option for mac :)
    else:
        komanda = 'wget -i ' + full_path + ' -P ' + destination
    os.system(komanda)

def check_abs_url(url):
    if not os.path.isabs(url):
        url = os.path.abspath(url)
    return url


def check_mpd_type(url):
    mpd_test = MPEGDASHParser.parse(url)
    try:
        range = mpd_test.periods[0].adaptation_sets[0].representations[0].segment_lists[0].segment_urls[0].media_range
        print(range)
    except:
        return "regular"
    else:
        return "byterange"


def parse_mpd_bytecode(mpd_url, destination, metrics):
    # parses mpd from given url, and saves all audio and video media links into list_mpd_audio and list_mpd_video dictionaries
    # mpd_url = 'http://cs1dev.ucc.ie/misl/4K_non_copyright_dataset/4_sec/x264/bbb/DASH_Files/full/dash_video_audio.mpd'
    mpd = MPEGDASHParser.parse(mpd_url)
    max_bandwidth = 0
    init_video = True
    init_audio = True
    filenewpath = os.path.join(destination, "vmaf")
    if not os.path.exists(destination):
        os.makedirs(destination)
    if not os.path.exists(filenewpath):
        os.makedirs(filenewpath)

    # for every segment in log, map bandwidth with bandwidth from mpd and save server url of that segment to a file
    for key in list_seg_rep_csv:
        for period in mpd.periods:
            for adapt_set in period.adaptation_sets:
                # download video init file once
                if "video" in adapt_set.representations[0].mime_type:
                    if (init_video):
                        init_name = adapt_set.segment_lists[0].initializations[0].source_url
                        mpd_url2 = mpd_url.rsplit("/", 1)[0]
                        mpd_url_final = mpd_url2 + "/" + init_name
                        filepath = os.path.join(destination, init_name)
                        komanda = 'curl.exe ' + mpd_url_final + ' --output ' + filepath
                        os.system(komanda)
                        init_video = False
                        if metrics == "True":
                            copyfile(filepath, os.path.join(filenewpath,init_name))
                    if metrics=="True":
                        for representation in adapt_set.representations:
                            # find max bandwidth
                            if representation.bandwidth>max_bandwidth:
                                max_bandwidth=representation.bandwidth
                                max_base_url=representation.base_urls[0].base_url_value
                                max_ranges=representation.segment_lists[0]
                    for representation in adapt_set.representations:
                        # maps bandwidth from mpd with bandwidth from video log file
                        if (list_seg_rep_csv[key] >= representation.bandwidth / 1000 * 0.95 and list_seg_rep_csv[
                            key] <= representation.bandwidth / 1000 * 1.05):
                            # get base_url for that representation
                            base_url = representation.base_urls[0].base_url_value
                            # get full url of a segment to download
                            mpd_url2 = mpd_url.rsplit("/", 1)[0]
                            mpd_url_final = mpd_url2 + "/" + representation.base_urls[0].base_url_value
                            # get last part of base url for segment file name to save locally - bbb_1920x1080_60fps_4300kbps_dash.mp4 and change extension to m4s
                            segment_name = base_url.rsplit("/", 2)[2]
                            segment_name_final = segment_name.split(".mp4")[0] + "_segment" + str(key) + ".m4s"
                            # get media range of a specific segment
                            range = representation.segment_lists[0].segment_urls[key - 1].media_range
                            # create final path to save file locally
                            final_url = os.path.join(destination, segment_name_final)
                            komanda = 'curl.exe -v -X GET -H ' + '"Range: bytes=' + range + '" ' + mpd_url_final + ' >> ' + final_url
                            print("CURL OBICNA KOMANDA " + komanda)
                            os.system(komanda)
                            if metrics=="True":
                                mpd_url2 = mpd_url.rsplit("/", 1)[0]
                                mpd_url_final = mpd_url2 + "/" + max_base_url
                                segment_name = max_base_url.rsplit("/", 2)[2]
                                segment_name_final = segment_name.split(".mp4")[0] + "_segment" + str(key) + ".m4s"
                                max_final_url = os.path.join(filenewpath, segment_name_final)
                                range = max_ranges.segment_urls[key - 1].media_range
                                komanda = 'curl.exe -v -X GET -H ' + '"Range: bytes=' + range + '" ' + mpd_url_final + ' >> ' + max_final_url
                                print( "CURL METRIC KOMANDA " + komanda)
                                os.system(komanda)

                # download audio init file once
                if "audio" in adapt_set.representations[0].mime_type:
                    if (init_audio):
                        init_name = adapt_set.representations[0].base_urls[0].base_url_value
                        mpd_url2 = mpd_url.rsplit("/", 1)[0]
                        mpd_url_final = mpd_url2 + "/" + init_name
                        filepath = os.path.join(destination, "segment_init.mp4")
                        range = adapt_set.representations[0].segment_lists[0].initializations[0].range
                        komanda = 'curl.exe -v -X GET -H ' + '"Range: bytes=' + range + '" ' + mpd_url_final + ' >> ' + filepath
                        os.system(komanda)
                        init_audio = False
                    # get base url for audio segments
                    base_url = adapt_set.representations[0].base_urls[0].base_url_value
                    mpd_url2 = mpd_url.rsplit("/", 1)[0]
                    mpd_url_final = mpd_url2 + "/" + base_url
                    # get media range of specific segment
                    range = adapt_set.representations[0].segment_lists[0].segment_urls[key - 1].media_range
                    segment_name = "segment_" + str(key) + ".m4s"
                    # get final url to save segment locally
                    final_url = os.path.join(destination, segment_name)
                    komanda = 'curl.exe -v -X GET -H ' + '"Range: bytes=' + range + '" ' + mpd_url_final + ' >> ' + final_url
                    os.system(komanda)

def download_max_res_segments (mpd_url, dest):
    #download max bandwidth segments needed for vmaf metric
    destination=os.path.join(dest,"vmaf")
    if not os.path.exists(destination):
        os.makedirs(destination)
    full_path = os.path.join(destination, "videoSegments.txt")
    open(full_path, 'w')

    mpd_url2 = mpd_url.rsplit("/", 1)[0]
    for key in list_seg_rep_csv:
        substring = str(list_mpd_video[max(list_mpd_video)]).replace('$Number$', str(key))
        komanda = " echo " + mpd_url2 + "/" + substring + " >> " + full_path
        os.system(komanda)
    komanda = " echo " + mpd_url2 + "/" + str(list_mpd_video[0]) + " >> " + full_path
    os.system(komanda)
    # download all files to specified location
    osystem = platform.system()
    if osystem == 'Linux':
        komanda = 'wget -i ' + full_path + ' -P ' + destination
    elif osystem == 'Windows':
        os.chdir(destination)
        komanda = 'for /f "tokens=*" %a in (' + full_path + ') do curl -O %a'
    # add option for mac :)
    else:
        komanda = 'wget -i ' + full_path + ' -P ' + destination
    os.system(komanda)


def init_vmaf_segments (paths):
    # combines video segments in vmaf folder with init file
    init = ""
    osystem = platform.system()
    if osystem == 'Windows':
        suffix = "type "
    elif osystem == 'Linux':
        suffix = "cat "
    # add for mac :)
    else:
        suffix = "cat "

    path=os.path.join(paths,"vmaf")
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).__contains__("dash_init"):
            init = filename
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).__contains__("kbps"):
            m4s = filename
            m4s2 = m4s.split(".m4s")[0]  # .removesuffix(".m4s")
            path_init = os.path.join(path, init)
            path_file = os.path.join(path, m4s)
            path_final = os.path.join(path, "inited_max" + m4s2 + ".mp4")
            komanda = suffix + path_init + " " + path_file + " > " + path_final
            os.system(komanda)

def scale_vmaf(paths):
    path=os.path.join(paths,"vmaf")
    #find maximum resolution segment and save that resolution to a variable
    x = helper_get_max_resolution_fps_duration(path, "inited_max")
    for file2 in os.listdir(path):
        filename2 = os.fsdecode(file2)
        if str(filename2).startswith("inited") and not(str(filename2).startswith("inited_max")):
            video = str(filename2)
            path_i_video = os.path.join(path, video)
            path_final = os.path.join(path, "scaled" + video)
            #scale every segment to a maximum mpd resolution
            komanda4 = 'ffmpeg -i ' + path_i_video + ' -vf scale=' + str(x[1]) + ':' + str(x[3]) + " " + path_final
            os.system(komanda4)

def calculate_vmaf(paths):
    #movie name is parsed from mpd
    mv=movie_name.replace(" ", "")
    #temporary list to save every result row
    temp_list=[]
    #vmaf model locations
    model_path='resources/vmaf_v0.6.1.json'
    model_path4k='resources/vmaf_4k_v0.6.1.json'
    path=os.path.join(paths,"vmaf")
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).startswith("scaled"):
            segment = re.search("(\d+)(?!.*\d)", filename.split(".mp4")[0]).group(1)
            video1=str(filename)
            for file2 in os.listdir(path):
                filename2 = os.fsdecode(file2)
                if str(filename2).endswith("segment" + segment + ".mp4") and str(filename2).startswith("inited_max"):
                    video2 = str(filename2)
                    path_video_orig = os.path.join(path, video1)
                    path_video_ref = os.path.join(path, video2)
                    log= video1.split(".mp4")[0]+'.xml'
                    #to avoid vmaf modelpath bug in windows ...
                    os.chdir(os.path.dirname(os.path.realpath(__file__)))
                    # ffmpeg command to calculate all metrics with specific vmaf model and store them to xml log

                    komanda = "ffmpeg -i " + path_video_orig+ " -i " + path_video_ref +  ' -lavfi libvmaf=model_path="' + model_path + '":n_threads=4:psnr=1:ssim=1:ms_ssim=1:log_fmt=xml:log_path=' + log + ' -f null - '
                    print("VMAF KOMANDA " + komanda)
                    os.system(komanda)

                    # parsing metric values from log and adding them to temp_list
                    df = pd.read_xml(log,
                                     xpath="/VMAF/pooled_metrics/metric")
                    temp_list.append("segment" + segment)
                    temp_list.append(model_path)
                    for index, row in (df.loc[df['name'] == 'vmaf']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'psnr']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ms_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    #adding all metrics for 1 segment to vmaf_list which will be stored to a final csv
                    vmaf_list.append(temp_list.copy())
                    temp_list.clear()
                    if os.path.isfile(log):
                        os.remove(log)

                    komanda = "ffmpeg -i " + path_video_orig + " -i " + path_video_ref + ' -lavfi libvmaf=model_path="' + model_path4k + '":n_threads=4:psnr=1:ssim=1:ms_ssim=1:log_fmt=xml:log_path=' + log + ' -f null - '
                    print("KOMANDA " + komanda)
                    os.system(komanda)
                    df = pd.read_xml(log,
                                     xpath="/VMAF/pooled_metrics/metric")
                    temp_list.append("segment" + segment)
                    temp_list.append(model_path4k)
                    for index, row in (df.loc[df['name'] == 'vmaf']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'psnr']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ms_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    vmaf_list1.append(temp_list.copy())
                    temp_list.clear()
                    if os.path.isfile(log):
                        os.remove(log)

                    komanda = "ffmpeg -i " + path_video_orig + " -i " + path_video_ref + ' -lavfi libvmaf=model_path="' + model_path4k + '":n_threads=4:psnr=1:ssim=1:ms_ssim=1:phone_model:log_fmt=xml:log_path=' + log + ' -f null - '
                    print("KOMANDA " + komanda)
                    os.system(komanda)
                    df = pd.read_xml(log,
                                     xpath="/VMAF/pooled_metrics/metric")
                    temp_list.append("segment" + segment)
                    temp_list.append(model_path4k + "_phone")
                    for index, row in (df.loc[df['name'] == 'vmaf']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'psnr']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ms_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    vmaf_list2.append(temp_list.copy())
                    temp_list.clear()
                    if os.path.isfile(log):
                        os.remove(log)

                    komanda = "ffmpeg -i " + path_video_orig + " -i " + path_video_ref + ' -lavfi libvmaf=model_path="' + model_path + '":n_threads=4:psnr=1:ssim=1:ms_ssim=1:phone_model:log_fmt=xml:log_path=' + log + ' -f null - '
                    print("KOMANDA " + komanda)
                    os.system(komanda)
                    df = pd.read_xml(log,
                                     xpath="/VMAF/pooled_metrics/metric")
                    temp_list.append("segment" + segment)
                    temp_list.append(model_path + "_phone")
                    for index, row in (df.loc[df['name'] == 'vmaf']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'psnr']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ms_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    vmaf_list3.append(temp_list.copy())
                    temp_list.clear()
                    if os.path.isfile(log):
                        os.remove(log)
    #creating dataframes for every model to store them to csv
    final_dataframe = pd.DataFrame(vmaf_list, columns=['Segment', 'Model','VMAF', 'PSNR','SSIM', 'MS_SSIM'])
    final_dataframe1 = pd.DataFrame(vmaf_list1, columns=['Segment', 'Model','VMAF', 'PSNR','SSIM', 'MS_SSIM'])
    final_dataframe2 = pd.DataFrame(vmaf_list2, columns=['Segment', 'Model','VMAF', 'PSNR','SSIM', 'MS_SSIM'])
    final_dataframe3 = pd.DataFrame(vmaf_list3, columns=['Segment', 'Model','VMAF', 'PSNR','SSIM', 'MS_SSIM'])

    #saving 4 different files for 4 different vmaf models
    final_log_name= mv + "_vmaf_v0.6.1_" +  date +'.csv'
    metric_path=os.path.join(path,final_log_name)
    final_dataframe.to_csv(metric_path)

    final_log_name = mv + "_4k_vmaf_v0.6.1_" + date + '.csv'
    metric_path = os.path.join(path, final_log_name)
    final_dataframe1.to_csv(metric_path)

    final_log_name = mv + "_4k_vmaf_v0.6.1_phone_" + date + '.csv'
    metric_path = os.path.join(path, final_log_name)
    final_dataframe2.to_csv(metric_path)

    final_log_name = mv + "_vmaf_v0.6.1_phone_" + date + '.csv'
    metric_path = os.path.join(path, final_log_name)
    final_dataframe3.to_csv(metric_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='This is log merger.')
    parser.add_argument('--path_to_log', dest='path_to_log', type=str, default="",
                        help='Path where video log is stored')
    parser.add_argument('--rep_lvl_col', dest='rep_lvl_column', type=str, default="Rep_Level",
                        help='Column name where rep level is stored')
    parser.add_argument('--seg_index_col', dest='chunk_index_column', type=str, default="Chunk_Index",
                        help='Column name where chunk index is stored')
    parser.add_argument('--stall_dur_col', dest='stall_dur_column', type=str, default="Stall_Dur",
                        help='Column name where stall duration is stored')
    parser.add_argument('--log_separator', dest='log_separator', type=str, default="csv",
                        help='Separator tyle, tab or csv')
    parser.add_argument('--path_audio', dest='path_audio', type=str, default="",
                        help='Full path to where audio files are stored')
    parser.add_argument('--path_video', dest='path_video', type=str, default="",
                        help='Full path to where video files are stored')
    parser.add_argument('--dest_video', dest='dest_video', type=str, default="output_files/resources/segments",
                        help='Full path to working folder')
    parser.add_argument('--gif_path', dest='gif_path', type=str, default="resources/gif.gif",
                        help='Full path to gif')
    parser.add_argument('--final_path', dest='final_path', type=str, default="output_files/resources/segments/final",
                        help='Full path to place where to store final video')
    parser.add_argument("--mpd_path", dest='mpd_path', type=str, default="",
                        help='URL where mpd with audio and video is')
    parser.add_argument("--auto_scale", dest='auto_scale', type=int, default=0,
                        help='If auto scale option is 0 it is off, if 1 then all video segments are rescaled to resolution of highest quality segment, if 2 aditional parameter scale_resolution is read')
    parser.add_argument("--log_location", dest='log_location', type=str, default='local',
                        help="'local' is for locally downloaded segments, 'mpd' link is to download segments from server, where full link is sent as parameter ")
    parser.add_argument("--parameter_type", dest='par_type', type=str, default='config',
                        help='Specifies how parameters are sent to script - path for sending parameters in console while calling script, and config for seting parameters in .ini file ')
    parser.add_argument("--config_path", dest='config_path', type=str, default="",
                        help='Path to where .ini config file is stored ')
    parser.add_argument("--cleanup", dest='cleanup', type=str, default="False",
                        help='If True all files except final video in dest_video deleted')
    parser.add_argument("--scale_resolution", dest='scale_resolution', type=str,
                        help='720p, 1080p, 1440p or 2160p, auto_scale should be set to 2')
    parser.add_argument("--calculate_metrics", dest='calc_metrics', type=str, default="True",
                        help='If True VMAF, PSNR, SSIM and SSIM are calculated')
    parser.add_argument("--merge_video", dest='merge_video', type=str, default="True",
                        help='If True final video is merged')

    args = parser.parse_args()

    fill_resolution_dict()

    if args.par_type == 'config':
        config_obj = configparser.ConfigParser()
        config_path = args.config_path
        config_path = check_abs_url(config_path)
        config_obj.read(config_path)
        param = config_obj["parameters"]
        path_to_log = param["path_to_log"]
        path_to_log = check_abs_url(path_to_log)
        rep_lvl_column = param["rep_lvl_col"]
        chunk_index_column = param["seg_index_col"]
        stall_dur_column = param["stall_dur_col"]
        log_separator = param["log_separator"]
        path_audio = param["path_audio"]
        path_audio = check_abs_url(path_audio)
        path_video = param["path_video"]
        path_video = check_abs_url(path_video)
        # code to add date into the folder structure
        dest_video = param["dest_video"] + "/" + date
        dest_video = check_abs_url(dest_video)
        gif_path = param["gif_path"]
        gif_path = check_abs_url(gif_path)
        # code to add date into the final folder structure
        final_path_list = param["final_path"].split("/")
        final_path_list.insert(len(final_path_list) - 1, date)
        final_path_list = [val + "/" for val in final_path_list]
        final_path = "".join(final_path_list)
        final_path = check_abs_url(final_path)
        mpd_path = param["mpd_path"]
        auto_scale = int(param["auto_scale"])
        log_location = param["log_location"]
        cleanup = param["cleanup"]
        scale_resolution = param["scale_resolution"]
        calc_metrics = param["calculate_metrics"]
        merge_video = param["merge_video"]
        read_replevels_log(path_to_log, rep_lvl_column, chunk_index_column, log_separator)
        read_stalls_log(path_to_log, stall_dur_column, chunk_index_column, log_separator)
        if log_location != 'local':
            # check mpd type
            type = check_mpd_type(mpd_path)
            if type == "regular":
                parse_mpd(mpd_path)
                download_audio_segments(mpd_path, dest_video)
                download_video_segments(mpd_path, dest_video)
                if calc_metrics == "True":
                    download_max_res_segments(mpd_path, dest_video)
            if (type == "byterange"):
                parse_mpd_bytecode(mpd_path, dest_video,calc_metrics)
            if calc_metrics == "True":
                init_vmaf_segments(dest_video)
        if log_location == 'local':
            copy_init_file(path_video, dest_video)
            copy_init_file(path_audio, dest_video)
            copy_video_segments(path_video, dest_video)
            copy_audio_segments(path_audio, dest_video)
        prepare_video_init(dest_video, calc_metrics)
        if calc_metrics == "True":
            scale_vmaf(dest_video)
            calculate_vmaf(dest_video)
        if merge_video == "True":
            prepare_audio_init(dest_video)
            concat_audio_video_ffmpeg(dest_video, auto_scale, scale_resolution)
            concat_video_segments_final(dest_video, gif_path, final_path)
        if cleanup == "True":
            clean_folder(dest_video)

    if args.par_type == 'path':
        path_to_log = args.path_to_log
        path_to_log = check_abs_url(path_to_log)
        # code to add date into the folder structure
        dest_video = args.dest_video + "/" + date
        dest_video = check_abs_url(dest_video)
        path_video = args.path_video
        path_video = check_abs_url(path_video)
        path_audio = args.path_audio
        path_audio = check_abs_url(path_audio)
        log_location = args.log_location
        log_location = check_abs_url(log_location)
        gif_path = args.gif_path
        gif_path = check_abs_url(gif_path)
        # code to add date into the final folder structure
        final_path_list = args.final_path.split("/")
        final_path_list.insert(len(final_path_list) - 1, date)
        final_path_list = [val + "/" for val in final_path_list]
        final_path = "".join(final_path_list)
        final_path = check_abs_url(final_path)
        calc_metrics = args.calculate_metrics
        merge_video = args.merge_video
        mpd_path = args.mpd_path
        read_replevels_log(path_to_log, args.rep_lvl_column, args.chunk_index_column, args.log_separator)
        read_stalls_log(path_to_log, args.stall_dur_column, args.chunk_index_column, args.log_separator)
        if args.log_location != 'local':
            # check mpd type
            type = check_mpd_type(mpd_path)
            if (type == "regular"):
                parse_mpd(log_location)
                download_audio_segments(log_location, dest_video)
                download_video_segments(log_location, dest_video)
                if calc_metrics == "True":
                    download_max_res_segments(mpd_path, dest_video)
            if (type == "byterange"):
                parse_mpd_bytecode(mpd_path, dest_video,calc_metrics)
            if calc_metrics == "True":
                init_vmaf_segments(dest_video)

        if args.log_location == 'local':
            copy_init_file(path_video, dest_video)
            copy_init_file(path_audio, dest_video)
            copy_video_segments(path_video, dest_video)
            copy_audio_segments(path_audio, dest_video)
        prepare_video_init(dest_video, calc_metrics)
        if calc_metrics == "True":
            scale_vmaf(dest_video)
            calculate_vmaf(dest_video)
        if merge_video == "True":
            prepare_audio_init(dest_video)
            concat_audio_video_ffmpeg(dest_video, args.auto_scale, args.scale_resolution)
            concat_video_segments_final(dest_video, gif_path, final_path)
        if args.cleanup == "True":
            clean_folder(dest_video)
