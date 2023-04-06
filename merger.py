#place for functions for parsing, downloading and merging segments

import utils
from shutil import copyfile
import os
import re
import pandas as pd
import platform
from mpegdash.parser import MPEGDASHParser
import subprocess

def parse_mpd(mpd_url,list_mpd_video, list_mpd_audio):
    # parses mpd from given url, and saves all audio and video media links into list_mpd_audio and list_mpd_video dictionaries
    # mpd_url = 'http://cs1dev.ucc.ie/misl/4K_non_copyright_dataset/4_sec/x264/bbb/DASH_Files/full/dash_video_audio.mpd'

    mpd = MPEGDASHParser.parse(mpd_url)
    inited = False

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
    return movie_name


def parse_mpd_bytecode(mpd_url, destination, metrics,list_seg_rep_csv):
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

def read_replevels_log(path, bitrate_column_name, index_column_name, height_column_name, delimiter, chunk_duration_col, list_seg_rep_csv, list_seg_res_csv, youtube_segments_dict):
    # read log and save bitrates and indexes, and chunk duration
    if delimiter == 'tab':
        df = pd.read_csv(path, sep='\t')
    elif delimiter == 'csv':
        df = pd.read_csv(path)
        # removes whitespaces from column names
    df.columns = df.columns.str.replace(' ', '')
    for index, row in df.iterrows():
        # maps index to bitrate
        list_seg_rep_csv[row[index_column_name]] = row[bitrate_column_name]
        #add all resolutions
        list_seg_res_csv.add(row[height_column_name])
        youtube_segments_dict[row[index_column_name]] = row[height_column_name]
        chunk_duration=round(int(row[chunk_duration_col])/1000)
    return chunk_duration

def check_mpd_type(url):
#check if url is youtube link, regular or byterange mpd file
    if 'youtube' in url:
        return "youtube"
    try:
        mpd_test = MPEGDASHParser.parse(url)
        range = mpd_test.periods[0].adaptation_sets[0].representations[0].segment_lists[0].segment_urls[0].media_range
        print(range)
    except:
        return "regular"
    else:
        return "byterange"

def download_audio_segments(mpd_url, destination, list_mpd_audio, list_seg_rep_csv):
    # downloads audio log segments from source to destination, now supports only one audio quality, it can be easily modifed to support more

    # creates folder and opens new file to store all audio segment urls
    if not os.path.exists(destination):
        os.makedirs(destination)
    full_path = os.path.join(destination, "audioSegments.txt")
    open(full_path, 'w')

    # deletes last url part where mpd file name is
    mpd_url2 = mpd_url.rsplit("/", 2)[0]

    # puts audio init url to a file
    komanda = " echo " + mpd_url2 + str(list_mpd_audio[0]).replace(list_mpd_audio[0].rsplit("/", 4)[0],"") + " >> " + full_path
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


def download_video_segments(mpd_url, destination, list_mpd_video, list_seg_rep_csv):
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



def copy_init_file(path, newfolder_path):
    # copy init file from source to destination
    if not os.path.exists(newfolder_path):
        os.makedirs(newfolder_path)
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        #only init file has init substring in name
        if filename.__contains__("init"):
            filepath = os.path.join(path, filename)
            filenewpath = os.path.join(newfolder_path, filename)
            copyfile(filepath, filenewpath)

def copy_video_segments(path, destination, list_seg_rep_csv):
    # copy video segments from log to destination
    #for every segment parsed from log and stored in list
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

def copy_audio_segments(path, destination,list_seg_rep_csv):
    # copies audio log segments from source to destination
    #for every segment parsed from log and stored in list
    for key in list_seg_rep_csv:
        for file in os.listdir(path):
            filename = os.fsdecode(file)
            #audio segments extension
            if str(filename).endswith("_" + str(key) + '.m4s'):
                path_to_file = os.path.join(path, filename)
                new_destination = os.path.join(destination, filename)
                copyfile(path_to_file, new_destination)

def read_stalls_log(path, stall_column_name, index_column_name, delimiter):
    # read log and save stalls and indexes into list_stall_values
    list_stall_values = dict()
    #use pandas to read file
    if delimiter == 'tab':
        df = pd.read_csv(path, sep='\t')
    elif delimiter == 'csv':
        df = pd.read_csv(path)
    # removes whitespaces from column names
    df.columns = df.columns.str.replace(' ', '')
    # maps chunk index to stall durations
    for index, row in (df.loc[df[stall_column_name] > 0]).iterrows():
        list_stall_values[row[index_column_name]] = row[stall_column_name]
    return list_stall_values

def prepare_video_init(path, metrics):
    # combines video segments with init file
    init = ""
    osystem = platform.system()
    #different keyword for different system commands
    if osystem == 'Windows':
        suffix = "type "
    elif osystem == 'Linux':
        suffix = "cat "
    # add for mac :)
    else:
        suffix = "cat "
    #first find dash_init file used for video segments
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).__contains__("dash_init"):
            init = filename
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        #for every video segment
        if str(filename).__contains__("kbps"):
            m4s = filename
            m4s2 = m4s.split(".m4s")[0]  # .removesuffix(".m4s")
            path_init = os.path.join(path, init)
            path_file = os.path.join(path, m4s)
            path_final = os.path.join(path, "inited" + m4s2 + ".mp4")
            #combine init file and video into new file with .mp4 extension and "inited" prefix
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
        #this is init file for audio segments
        if str(filename).__contains__("segment_init"):
            init = filename
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        #for every audio segment
        if not (str(filename).__contains__("segment_init")) and str(filename).__contains__("segment") and not (
                str(filename).__contains__("kbps")):
            m4s = filename
            m4s2 = m4s.split(".m4s")[0]  # .removesuffix(".m4s")
            path_init = os.path.join(path, init)
            path_file = os.path.join(path, m4s)
            path_final = os.path.join(path, "inited" + m4s2 + ".avi")
            #combine init file and audio segment into new file with .avi extension and "inited" prefix
            komanda = suffix + path_init + " " + path_file + " > " + path_final
            os.system(komanda)


def concat_audio_video_ffmpeg(path, auto_scale, resolution, list_seg_rep_csv, list_resolutions):
    # combines audio and video segments into one file, it rescales resolution to max if auto_scale option is 1, if 2 then resolution is read
    audio = ""
    m4s = ""
    segment = ""
    x = tuple
    if auto_scale == 1:
        # get maximum resolution segment for scaling
        x = utils.helper_get_max_resolution_fps_duration(path, "inited", list_seg_rep_csv)
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        #for every audio segment
        if str(filename).endswith("avi") and str(filename).startswith("inited"):
            segment = re.search("\w+_([0-9]+)", filename).group(1)
            audio = str(filename)
            for file2 in os.listdir(path):
                filename2 = os.fsdecode(file2)
                #find its video segment pair
                if str(filename2).endswith("segment" + segment + ".mp4") and str(filename2).startswith("inited"):
                    video = str(filename2)
                    path_video = os.path.join(path, video)
                    path_audio = os.path.join(path, audio)
                    path_i_video = os.path.join(path, "i" + video.split(".mp4")[0] + ".mkv")
                    path_final = os.path.join(path, "merged" + video.split(".mp4")[0] + ".mkv")
                    #merge inited audio and video segment into one segment with .mkv extension and "merged" prefix
                    komanda = "ffmpeg -fflags +genpts -i " + path_video + " -i " + path_audio + " -c copy " + path_i_video
                    os.system(komanda)
                    if auto_scale == 0:
                        #if scaling is off, then do nothing
                        copyfile(path_i_video, path_final)
                    if auto_scale == 1:
                        #scale segment to a resolution of a maximum resolution segment
                        komanda4 = 'ffmpeg -i ' + path_i_video + ' -vf scale=' + str(x[1]) + ':' + str(
                            x[3]) + " -c:a copy " + path_final
                        os.system(komanda4)
                    if auto_scale == 2:
                        #scale segment to a 4k resolution
                        komanda4 = 'ffmpeg -i ' + path_i_video + ' -vf scale=' + str(
                            list_resolutions[resolution][0]) + ':' + str(
                            list_resolutions[resolution][1]) + " -c:a copy " + path_final
                        os.system(komanda4)


def create_stalled_video(path, sorted_dict, key, path_to_gif, duration, list_stall_values):
    # creates stalled segments in given path
    stall_duration = 0
    #key + 1 because in log stall is recorded afted that segment
    if list_stall_values[key + 1] != 0:
        #conversion from ms to seconds
        stall_duration = list_stall_values[key + 1] / 1000
        stall_duration = round(stall_duration, 1)
    newname = str(sorted_dict[key]).split('.mkv')[0] + '.jpg'  # .removesuffix('.mkv')
    jpg_path = os.path.join(path, newname)
    file_path = os.path.join(path, sorted_dict[key])
    #create jpg picture from the stalled segment last frame
    komanda = 'ffmpeg -sseof -3 -i ' + file_path + ' -update 1 -q:v 1 ' + jpg_path
    os.system(komanda)
    path_mp4 = os.path.join(path, sorted_dict[key])
    #get width, height, fps, duration of a video part of a segment
    result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                             'stream=width,height,avg_frame_rate,duration', '-of', 'default=noprint_wrappers=1',
                             path_mp4], stdout=subprocess.PIPE).stdout.decode('utf-8')
    x = utils.helper_format_result_string(result)
    #get sample_rate, channel_layout, codec_name of an audio part of a segment
    result2 = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                              'stream=sample_rate,channel_layout,codec_name', '-of', 'default=noprint_wrappers=1',
                              path_mp4], stdout=subprocess.PIPE).stdout.decode('utf-8')
    y = utils.helper_format_result_string(result2)
    path_mp4s = os.path.join(path, 's' + sorted_dict[key])
    #create new segment of a stalled part - jpg for the stall duration
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
    #concat original segment and stalled part + add stalling gif animation
    komanda = 'ffmpeg -i ' + path_mp4ss + ' -ignore_loop 0 -i ' + path_to_gif + ' -filter_complex "[1:v]format=yuva444p,scale=%d:%d,setsar=1,rotate=PI/6:c=black@0:ow=rotw(PI/6):oh=roth(PI/6) [rotate];[0:v][rotate] overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:format=auto:shortest=1:enable=' % (
        scale_gif, scale_gif) + subkomanda + '" -codec:a copy -y ' + ss_path
    os.system(komanda)
    seg_path = os.path.join(path, "segmentList.txt")
    komanda = ' echo file ' + "'" + ss_path + "'" + '  >>  ' + seg_path
    os.system(komanda)
    return x


def concat_video_segments_final(path, path_to_gif, path_to_file, list_inter_names, list_seg_rep_csv, list_stall_values, path_to_log,  segment_duration=4, isyoutube=False):
    # create stalls and merge final video
    sorted_dict = utils.helper_segment_list(path, list_inter_names)
    #for youtube segment duration is known before so there is no need to use ffprobe
    if isyoutube is False:
        x = utils.helper_get_max_resolution_fps_duration(path, "merged", list_seg_rep_csv)
    full_path = os.path.join(path, "segmentList.txt")
    # youtube segments starts from 0, others from 1
    if isyoutube:
        sorted_dict2 = dict()
        for key in sorted_dict:
            sorted_dict2[key + 1] = sorted_dict[key]
        sorted_dict=sorted_dict2

    for key in sorted_dict:
        #for every stall that is stored in list_stall_values create stalled video
        if (key + 1) in list_stall_values.keys():
            if isyoutube:
                create_stalled_video(path, sorted_dict, key, path_to_gif, segment_duration, list_stall_values)
            else:
                create_stalled_video(path, sorted_dict, key, path_to_gif, float(x[7]), list_stall_values )
            continue
        #store path to every segment that is going to be merged in segmentList.txt file
        seg_path = os.path.join(path, sorted_dict[key])
        komanda = 'echo file ' + "'" + seg_path + "'" + ' >> ' + full_path
        os.system(komanda)

    if not os.path.exists(path_to_file):
        os.makedirs(path_to_file)
    #create path for the final merged video
    final_path = os.path.join(path_to_file, path_to_log.split(".")[-2].split(os.sep)[-1] + "_" + "video.mkv")
    #merge all segments including stalled ones into one movie
    komanda = "ffmpeg -f concat -safe 0 -i " + full_path + " -c copy " + final_path
    os.system(komanda)

