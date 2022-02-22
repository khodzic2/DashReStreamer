import pandas as pd
import os
import re
from shutil import copyfile
import subprocess
import argparse
from mpegdash.parser import MPEGDASHParser
import configparser

list_rep_mpd = []
list_seg_rep_csv = dict()
list_inter_names = dict()
list_stall_values = dict()
list_mpd_audio = dict()
list_mpd_video = dict()


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
                        path_to_file = os.path.join(os.sep, subdir[0] + os.sep, filename)
                        new_destination = os.path.join(os.sep, destination + os.sep, filename)
                        copyfile(path_to_file, new_destination)


def copy_audio_segments(path, destination):
    # copies audio log segments from source to destination
    for key in list_seg_rep_csv:
        for file in os.listdir(path):
            filename = os.fsdecode(file)
            if str(filename).endswith("_" + str(key) + '.m4s'):
                path_to_file = os.path.join(os.sep, path + os.sep, filename)
                new_destination = os.path.join(os.sep, destination + os.sep, filename)
                print(path_to_file)
                print(new_destination)
                copyfile(path_to_file, new_destination)


def prepare_video_init(path, osystem):
    # combines video segments with init file
    init = ""
    if osystem == 'win':
        suffix = "type "
    if osystem == 'linux':
        suffix = "cat"
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).__contains__("dash_init"):
            init = filename
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).__contains__("kbps"):
            m4s = filename
            m4s2 = m4s.removesuffix(".m4s")
            path_init = os.path.join(os.sep, path + os.sep, init)
            path_file = os.path.join(os.sep, path + os.sep, m4s)
            path_final = os.path.join(os.sep, path + os.sep, "inited" + m4s2 + ".mp4")
            komanda = suffix + path_init + " " + path_file + " > " + path_final
            os.system(komanda)


def prepare_audio_init(path, osystem):
    # combines audio segments with init file
    init = ""
    if osystem == 'win':
        suffix = "type "
    if osystem == 'linux':
        suffix = "cat"
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).__contains__("segment_init"):
            init = filename
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if not (str(filename).__contains__("segment_init")) and str(filename).__contains__("segment") and not (
                str(filename).__contains__("kbps")):
            m4s = filename
            m4s2 = m4s.removesuffix(".m4s")
            path_init = os.path.join(os.sep, path + os.sep, init)
            path_file = os.path.join(os.sep, path + os.sep, m4s)
            path_final = os.path.join(os.sep, path + os.sep, "inited" + m4s2 + ".avi")
            komanda = suffix + path_init + " " + path_file + " > " + path_final
            os.system(komanda)


def concat_audio_video_ffmpeg(path, auto_scale=False):
    # combines audio and video segments into one file, it rescales resolution to max if auto_scale option is on, default is False
    audio = ""
    m4s = ""
    segment = ""
    x = tuple
    if auto_scale:
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
                    path_video = os.path.join(os.sep, path + os.sep, video)
                    path_audio = os.path.join(os.sep, path + os.sep, audio)
                    path_i_video = os.path.join(os.sep, path + os.sep, "i" + video)
                    path_s = os.path.join(os.sep, path + os.sep, segment + "intermediate.ts")
                    path_final = os.path.join(os.sep, path + os.sep, "merged" + video)
                    komanda = "ffmpeg -i " + path_video + " -i " + path_audio + " -c copy " + path_i_video
                    os.system(komanda)
                    komanda2 = "ffmpeg -i " + path_i_video + " -c copy -f mpegts " + path_s
                    os.system(komanda2)
                    if not auto_scale:
                        komanda3 = 'ffmpeg -i "concat:' + path_s + '" -c copy ' + path_final
                        os.system(komanda3)
                    if auto_scale:
                        path_uns = os.path.join(os.sep, path + os.sep, "unscaled" + video)
                        komanda3 = 'ffmpeg -i "concat:' + path_s + '" -c copy ' + path_uns
                        os.system(komanda3)
                        komanda4 = 'ffmpeg -i ' + path_uns + ' -vf scale=' + x[1] + ':' + x[3] + " " + path_final
                        print(komanda4)
                        os.system(komanda4)


def helper_get_max_resolution_fps_duration(path, sufix):
    # function to get resolution, fps and duration of a highest resolution segment using ffprobe
    list_inter_names2 = dict()
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).endswith(".mp4") and str(filename).startswith(sufix):
            segment = re.search("(\d+)(?!.*\d)", filename.removesuffix(".mp4")).group(1)
            list_inter_names2[int(segment)] = str(filename)
    sorted_dict = dict(sorted(list_inter_names2.items()))
    segment = (
    sorted_dict[list(list_seg_rep_csv.keys())[list(list_seg_rep_csv.values()).index(max(list_seg_rep_csv.values()))]])
    result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                             'stream=width,height,avg_frame_rate,duration', '-of',
                             'default=noprint_wrappers=1', os.path.join(path, segment)
                             ],
                            stdout=subprocess.PIPE).stdout.decode('utf-8')
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
        if str(filename).endswith(".mp4") and str(filename).startswith("merged"):
            segment = re.search("(\d+)(?!.*\d)", filename.removesuffix(".mp4")).group(1)
            list_inter_names[int(segment)] = str(filename)
    sorted_dict = dict(sorted(list_inter_names.items()))
    return sorted_dict


def create_stalled_video(path, sorted_dict, key):
    # creates stalled segments in given path
    stall_duration = 0
    if list_stall_values[key + 1] != 0:
        stall_duration = list_stall_values[key + 1] / 1000
        stall_duration = round(stall_duration, 1)
    newname = str(sorted_dict[key]).removesuffix('.mp4') + '.jpg'
    jpg_path = os.path.join(os.sep, path + os.sep, newname)
    file_path = os.path.join(os.sep, path + os.sep, sorted_dict[key])
    komanda = 'ffmpeg -sseof -3 -i ' + file_path + ' -update 1 -q:v 1 ' + jpg_path
    os.system(komanda)
    path_mp4 = os.path.join(os.sep, path + os.sep, sorted_dict[key])
    result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                             'stream=width,height,avg_frame_rate,duration', '-of', 'default=noprint_wrappers=1',
                             path_mp4], stdout=subprocess.PIPE).stdout.decode('utf-8')
    x = helper_format_result_string(result)
    result2 = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                              'stream=sample_rate,channel_layout,codec_name', '-of', 'default=noprint_wrappers=1',
                              path_mp4], stdout=subprocess.PIPE).stdout.decode('utf-8')
    y = helper_format_result_string(result2)
    path_mp4s = os.path.join(os.sep, path + os.sep, 's' + sorted_dict[key])
    command = 'ffmpeg -loop 1 -i ' + jpg_path + ' -f lavfi -i anullsrc=channel_layout=' + y[5].split('(')[
        0] + ':sample_rate=' + y[3] + ' -t ' + str(stall_duration) + ' -c:a ' + y[1] + ' -c:v libx264 -t ' + str(
        stall_duration) + ' -pix_fmt yuv420p -vf scale=' + x[1] + ':' + x[3] + ' -r ' + (x[5].split('/'))[
                  0] + ' -y ' + path_mp4s
    os.system(command)
    temp_path = os.path.join(os.sep, path + os.sep, "temporaryList.txt")
    open(temp_path, 'w').close()
    komanda = ' echo file ' + "'" + path_mp4 + "'" + '  >>  ' + temp_path
    os.system(komanda)
    komanda = ' echo file ' + "'" + path_mp4s + "'" + '  >>  ' + temp_path
    os.system(komanda)
    path_mp4ss = os.path.join(os.sep, path + os.sep, 'ss' + sorted_dict[key])
    komanda = 'ffmpeg -f concat -safe 0 -i ' + temp_path + ' -c copy ' + path_mp4ss
    os.system(komanda)
    ss_path = os.path.join(os.sep, path + os.sep, 'ss' + sorted_dict[key])
    seg_path = os.path.join(os.sep, path + os.sep, "segmentList.txt")
    komanda = ' echo file ' + "'" + ss_path + "'" + '  >>  ' + seg_path
    os.system(komanda)
    return x


def concat_video_segments_final(path, path_to_gif, path_to_file, concat_type=0, osystem='win'):
    # create stalls and merge final video
    sorted_dict = helper_segment_list(path)
    x = helper_get_max_resolution_fps_duration(path, "merged")
    full_path = os.path.join(os.sep, path + os.sep, "segmentList.txt")
    open(full_path, 'w')
    max_seg_path = os.path.join(os.sep, path + os.sep, sorted_dict[
        list(list_seg_rep_csv.keys())[list(list_seg_rep_csv.values()).index(max(list_seg_rep_csv.values()))]])
    if (concat_type == 0):
        komanda = ' echo file ' + "'" + max_seg_path + "'" + " >> " + full_path
        os.system(komanda)
    for key in sorted_dict:
        if ((key + 1) in list_stall_values.keys()):
            x = create_stalled_video(path, sorted_dict, key)
            continue
        seg_path = os.path.join(os.sep, path + os.sep, sorted_dict[key])
        komanda = ' echo file ' + "'" + seg_path + "'" + ' >> ' + full_path
        os.system(komanda)
    if not os.path.exists(path_to_file):
        os.makedirs(path_to_file)
    final_path = os.path.join(os.sep, path_to_file + os.sep, 'FinalVideo.mp4')
    if concat_type == 1:
        komanda = "ffmpeg -f concat -safe 0 -i " + full_path + " -c copy " + final_path
        os.system(komanda)
        add_stall_gifs(path, path_to_gif, path_to_file)
    if concat_type == 0:
        komanda = 'ffmpeg -safe 0 -f concat -segment_time_metadata 1 -i ' + full_path + ' -vf select=concatdec_select -af aselect=concatdec_select,aresample=async=1 ' + final_path
        os.system(komanda)
        add_stall_gifs(path_to_gif, path_to_file, int(float(x[7])))
        gifed_path = os.path.join(os.sep, path_to_file + os.sep, 'gifedVideo.mp4')
        gifed_final = os.path.join(os.sep, path_to_file + os.sep, 'gifedfinalVideo.mp4')
        seconds = float(x[7])
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        komanda = 'ffmpeg -i ' + gifed_path + ' -ss ' + "%02d:%02d:%02d" % (
        hours, minutes, seconds) + ' -c:v libx264 ' + gifed_final
        os.system(komanda)


def add_stall_gifs(path_to_gif, path_to_file, duration):
    stall_sum = 0
    subkomanda = ""
    provjera = True
    for key in list_stall_values:
        first = ((key - 1) * int(duration) + stall_sum) + int(duration) + 0.5
        second = (first + round(list_stall_values[key] / 1000, 1)) - 1
        if (provjera):
            provjera = False
            subkomanda += "between(t," + str(first) + "," + str(second) + ")"
        else:
            subkomanda += "+between(t," + str(first) + "," + str(second) + ")"
        stall_sum += round(list_stall_values[key] / 1000, 1)
    if not os.path.exists(path_to_file):
        os.makedirs(path_to_file)
    path_final = os.path.join(os.sep, path_to_file + os.sep, 'FinalVideo.mp4')
    gif_final = os.path.join(os.sep, path_to_file + os.sep, 'gifedVideo.mp4')
    komanda = 'ffmpeg -i ' + path_final + ' -ignore_loop 0 -i ' + path_to_gif + ' -filter_complex ' + '"' "[1:v]format=yuva444p,scale=80:80,setsar=1,rotate=PI/6:c=black@0:ow=rotw(PI/6):oh=roth(PI/6) [rotate];[0:v][rotate] overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:shortest=1:enable='" + subkomanda + "'" + '"' + ' -codec:a copy -y ' + gif_final
    os.system(komanda)


def clean_folder(path):
    for f in os.listdir(path):
        if os.path.isfile(os.path.join(path, f)):
            os.remove(os.path.join(path, f))


def parse_mpd(mpd_url):
    # parses mpd from given url, and saves all audio and video media links into list_mpd_audio and list_mpd_video dictionaries
    # mpd_url = 'http://cs1dev.ucc.ie/misl/4K_non_copyright_dataset/4_sec/x264/bbb/DASH_Files/full/dash_video_audio.mpd'

    mpd = MPEGDASHParser.parse(mpd_url)
    inited = False

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


def download_audio_segments(mpd_url, destination, osystem):
    # downloads audio log segments from source to destination, now supports only one audio quality, it can be easily modifed to support more

    # creates and opens new file to store all audio segment urls
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
    if osystem == 'linux':
        komanda = 'wget -i ' + full_path + ' -P ' + destination
    if osystem == 'win':
        # to implement
        print("not implemented")
    os.system(komanda)


def download_video_segments(mpd_url, destination, osystem):
    # downloads audio log segments from source to destination, now supports only one audio quality, it can be easily modifed to support more
    full_path = os.path.join(destination, "videoSegments.txt")
    open(full_path, 'w')

    # deletes last url part where mpd file name is
    mpd_url2 = mpd_url.rsplit("/", 1)[0]

    # copy location to video init file
    komanda = " echo " + mpd_url2 + "/" + str(list_mpd_video[0]) + " >> " + full_path
    os.system(komanda)

    # for every segment in log, map bandwidth with bandwidth from mpd and save server url of that segment to a file
    for key in list_seg_rep_csv:
        for key2 in list_mpd_video:
            if key2 != 0:
                if list_seg_rep_csv[key] >= key2 / 1000 * 0.95 and list_seg_rep_csv[key] <= key2 / 1000 * 1.05:
                    substring = str(list_mpd_video[key2]).replace('$Number$', str(key))
                    komanda = " echo " + mpd_url2 + "/" + substring + " >> " + full_path
                    os.system(komanda)

    # download all files to specified location
    if osystem == 'linux':
        komanda = 'wget -i ' + full_path + ' -P ' + destination
    if osystem == 'win':
        # to implement
        print("not implemented")
    os.system(komanda)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='This is log merger.')
    parser.add_argument('--path_to_log', dest='path_to_log', type=str, default="",
                        help='Path where video log is stored')
    parser.add_argument('--rep_lvl_column', dest='rep_lvl_column', type=str, default="Rep_Level",
                        help='Column name where rep level is stored')
    parser.add_argument('--chunk_index_column', dest='chunk_index_column', type=str, default="Chunk_Index",
                        help='Column name where chunk index is stored')
    parser.add_argument('--stall_dur_column', dest='stall_dur_column', type=str,
                        help='Column name where stall duration is stored')
    parser.add_argument('--log_separator', dest='log_separator', type=str, default="csv",
                        help='Separator tyle, tab or csv')
    parser.add_argument('--path_audio', dest='path_audio', type=str, default="",
                        help='Full path to where audio files are stored')
    parser.add_argument('--path_video', dest='path_video', type=str, default="",
                        help='Full path to where video files are stored')
    parser.add_argument('--dest_video', dest='dest_video', type=str, default="",
                        help='Full path to working folder')
    parser.add_argument('--os', dest='os', type=str, default='linux',
                        help='Operating system where script is run')
    parser.add_argument('--gif_path', dest='gif_path', type=str, default="",
                        help='Full path to gif')
    parser.add_argument('--final_path', dest='final_path', type=str, default="",
                        help='Full path to place where to store final video')
    parser.add_argument("--concat_type", dest='concat_type', type=int, default=1,
                        help='Concat type, default is 1, 0 for reencoding and inserting temporary start segment')
    parser.add_argument("--mpd_path", dest='mpd_path', type=str, default="",
                        help='URL where mpd with audio and video is')
    parser.add_argument("--auto_scale", dest='auto_scale', type=bool, default=False,
                        help='If auto scale option is on then all video segments are rescaled to resolution of highest quality segment ')
    parser.add_argument("--log_location", dest='log_location', type=str, default='local',
                        help='local is for locally downloaded segments, mpd link is to download segments from server, where full link is sent as parameter ')
    parser.add_argument("--parameter_type", dest='par_type', type=str, default='config',
                        help='Specifies how parameters are sent to script - path for sending parameters in console while calling script, and config for seting parameters in .ini file ')
    parser.add_argument("--config_path", dest='config_path', type=str, default="",
                        help='Path to where .ini config file is stored ')

    args = parser.parse_args()

    if args.par_type == 'config':
        config_obj = configparser.ConfigParser()
        config_obj.read(args.config_path)
        param = config_obj["parameters"]
        path_to_log = param["path_to_log"]
        rep_lvl_column = param["rep_lvl_column"]
        chunk_index_column = param["chunk_index_column"]
        stall_dur_column = param["stall_dur_column"]
        log_separator = param["log_separator"]
        path_audio = param["path_audio"]
        path_video = param["path_video"]
        dest_video = param["dest_video"]
        os_type = param["os"]
        gif_path = param["gif_path"]
        final_path = param["final_path"]
        concat_type = int(param["concat_type"])
        mpd_path = param["mpd_path"]
        auto_scale = param["auto_scale"]
        log_location = param["log_location"]
        read_replevels_log(path_to_log, rep_lvl_column, chunk_index_column, log_separator)
        read_stalls_log(path_to_log, stall_dur_column, chunk_index_column, log_separator)
        if log_location != 'local':
            parse_mpd(log_location)
            download_audio_segments(log_location, dest_video, os_type)
            download_video_segments(log_location, dest_video, os_type)
        if log_location == 'local':
            copy_init_file(path_video, dest_video)
            copy_init_file(path_audio, dest_video)
            copy_video_segments(path_video, dest_video)
            copy_audio_segments(path_audio, dest_video)
        prepare_video_init(dest_video, os_type)
        prepare_audio_init(dest_video, os_type)
        if auto_scale=='True':
            concat_audio_video_ffmpeg(dest_video, True)
        if auto_scale=='False':
            concat_audio_video_ffmpeg(dest_video, False)
        concat_video_segments_final(dest_video, gif_path, final_path, concat_type, args.os)
        #clean_folder(dest_video)

    if args.par_type == 'path':
        read_replevels_log(args.path_to_log, args.rep_lvl_column, args.chunk_index_column, args.log_separator)
        read_stalls_log(args.path_to_log, args.stall_dur_column, args.chunk_index_column, args.log_separator)
        if args.log_location != 'local':
            parse_mpd(args.log_location)
            download_audio_segments(args.log_location, args.dest_video, args.os)
            download_video_segments(args.log_location, args.dest_video, args.os)
        if args.log_location == 'local':
            copy_init_file(args.path_video, args.dest_video)
            copy_init_file(args.path_audio, args.dest_video)
            copy_video_segments(args.path_video, args.dest_video)
            copy_audio_segments(args.path_audio, args.dest_video)
        prepare_video_init(args.dest_video, args.os)
        prepare_audio_init(args.dest_video, args.os)
        concat_audio_video_ffmpeg(args.dest_video, args.auto_scale)
        concat_video_segments_final(args.dest_video, args.gif_path, args.final_path, args.concat_type, args.os)
        #clean_folder(args.dest_video)
