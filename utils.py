#place for helper and other small functions

import os
import subprocess
import re

def fill_resolution_dict():
    # fill list_resolutions dictionary used for scaling in concat_audio_video_ffmpeg function
    list_resolutions = dict()
    list_resolutions["720p"] = [1280, 720]
    list_resolutions["1080p"] = [1920, 1080]
    list_resolutions["1440p"] = [2560, 1440]
    list_resolutions["2160p"] = [3840, 2160]
    return list_resolutions

def helper_get_max_resolution_fps_duration(path, prefix, list_seg_rep_csv , suffix=""):
    # function to get resolution, fps and duration of a highest resolution segment using ffprobe
    if suffix=='.mkv':
        checkyoutube = True
    if prefix == "inited":
        suffix = ".mp4"
    if prefix == "merged":
        suffix = ".mkv"
    if prefix == "inited_max" and not checkyoutube:
        suffix = ".mp4"

    list_inter_names2 = dict()
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).endswith(suffix) and str(filename).startswith(prefix):
            segment = re.search("(\d+)(?!.*\d)", filename.split(suffix)[0]).group(1)  # .removesuffix(suffix)).group(1)
            list_inter_names2[int(segment)] = str(filename)

    sorted_dict = dict(sorted(list_inter_names2.items()))
    if checkyoutube:
        segment = (sorted_dict[list(list_seg_rep_csv.keys())[list(list_seg_rep_csv.values()).index(max(list_seg_rep_csv.values()))]-1])
    else:
        segment = (sorted_dict[list(list_seg_rep_csv.keys())[list(list_seg_rep_csv.values()).index(max(list_seg_rep_csv.values()))]])

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

def helper_segment_list(path, list_inter_names):
    # puts all merged mp4 segments in a dictionary -- segment number -- filename that is used in concat_video_segments_final and create_stalled_video
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).endswith(".mkv") and str(filename).startswith("merged"):
            segment = re.search("(\d+)(?!.*\d)", filename.split(".mkv")[0]).group(1)  # .removesuffix(".mkv")
            list_inter_names[int(segment)] = str(filename)
    sorted_dict = dict(sorted(list_inter_names.items()))
    return sorted_dict

def clean_folder(path):
    #deletes all files in a folder given in path parameter
    for f in os.listdir(path):
        if os.path.isfile(os.path.join(path, f)):
            os.remove(os.path.join(path, f))

def check_abs_url(url):
    #create absolute path of an url
    if not os.path.isabs(url):
        url = os.path.abspath(url)
    return url
