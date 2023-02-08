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

import os
import argparse
import configparser
from datetime import datetime
import youtube
import metrics
import utils
import merger

list_rep_mpd = []
list_seg_rep_csv = dict()
list_seg_res_csv = set()
list_inter_names = dict()
list_stall_values = dict()
list_mpd_audio = dict()
list_mpd_video = dict()
list_resolutions = dict()
# all needed segments are saved in youtube_segments_dict in  read_replevels_log function
youtube_segments_dict = dict()
youtube_videos = list()

# get the current date
date = datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p")

#variable to store movie name
movie_name = ""
#variable to store youtube movie name
yt_movie_title = ""
#variable to store chunk duration, default is 4
chunk_duration = 4

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
    parser.add_argument('--chunk_dur_col', dest='chunk_duration_column', type=str, default="ChunkDur",
                        help='Column name where chunk duration in miliseconds is stored')
    parser.add_argument('--height_col', dest='height_column', type=str, default="Height",
                        help='Column name where segment height is stored')
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
    list_resolutions=utils.fill_resolution_dict()
    if args.par_type == 'config':
        config_obj = configparser.ConfigParser()
        config_path = args.config_path
        config_path = utils.check_abs_url(config_path)
        config_obj.read(config_path)
        param = config_obj["parameters"]
        path_to_log = param["path_to_log"]
        path_to_log = utils.check_abs_url(path_to_log)
        rep_lvl_column = param["rep_lvl_col"]
        chunk_index_column = param["seg_index_col"]
        stall_dur_column = param["stall_dur_col"]
        chunk_duration_column=param["chunk_dur_col"]
        height_column = param["height_col"]
        log_separator = param["log_separator"]
        path_audio = param["path_audio"]
        path_audio = utils.check_abs_url(path_audio)
        path_video = param["path_video"]
        path_video = utils.check_abs_url(path_video)
        # code to add date into the folder structure
        dest_video = param["dest_video"] + "/" + date
        dest_video = utils.check_abs_url(dest_video)
        gif_path = param["gif_path"]
        gif_path = utils.check_abs_url(gif_path)
        # code to add date into the final folder structure
        final_path_list = param["final_path"].split("/")
        final_path_list.insert(len(final_path_list) - 1, date)
        final_path_list = [val + "/" for val in final_path_list]
        final_path = "".join(final_path_list)
        final_path = utils.check_abs_url(final_path)
        mpd_path = param["mpd_path"]
        auto_scale = int(param["auto_scale"])
        log_location = param["log_location"]
        cleanup = param["cleanup"]
        scale_resolution = param["scale_resolution"]
        calc_metrics = param["calculate_metrics"]
        merge_video = param["merge_video"]
        chunk_duration=merger.read_replevels_log(path_to_log, rep_lvl_column, chunk_index_column, height_column, log_separator, chunk_duration_column, list_seg_rep_csv, list_seg_res_csv, youtube_segments_dict)
        list_stall_values=merger.read_stalls_log(path_to_log, stall_dur_column, chunk_index_column, log_separator)
    elif args.par_type == 'path':
        path_to_log = args.path_to_log
        path_to_log = utils.check_abs_url(path_to_log)
        # code to add date into the folder structure
        dest_video = args.dest_video + "/" + date
        dest_video = utils.check_abs_url(dest_video)
        path_video = args.path_video
        path_video = utils.check_abs_url(path_video)
        path_audio = args.path_audio
        path_audio = utils.check_abs_url(path_audio)
        log_location = args.log_location
        log_location = utils.check_abs_url(log_location)
        gif_path = args.gif_path
        gif_path = utils.check_abs_url(gif_path)
        # code to add date into the final folder structure
        final_path_list = args.final_path.split("/")
        final_path_list.insert(len(final_path_list) - 1, date)
        final_path_list = [val + "/" for val in final_path_list]
        final_path = "".join(final_path_list)
        final_path = utils.check_abs_url(final_path)
        calc_metrics = args.calculate_metrics
        merge_video = args.merge_video
        mpd_path = args.mpd_path
        chunk_duration=merger.read_replevels_log(path_to_log, args.rep_lvl_column, args.chunk_index_column, args.height_column,args.log_separator, args.chunk_duration_column, list_seg_rep_csv, list_seg_res_csv, youtube_segments_dict)
        list_stall_values=merger.read_stalls_log(path_to_log, args.stall_dur_column, args.chunk_index_column, args.log_separator)
        cleanup=args.cleanup
    if log_location != 'local':
        # check mpd type
        type = merger.check_mpd_type(mpd_path)
        if type == "youtube":
            yt_movie_title = youtube.get_youtube_title(mpd_path)
            youtube_videos = youtube.download_youtube_movies(dest_video, mpd_path, list_seg_res_csv, youtube_videos, yt_movie_title)
            youtube.youtube_split(dest_video,chunk_duration, youtube_videos)
        elif type == "regular":
            movie_name=merger.parse_mpd(mpd_path,list_mpd_video, list_mpd_audio)
            merger.download_audio_segments(mpd_path, dest_video, list_mpd_audio, list_seg_rep_csv)
            merger.download_video_segments(mpd_path, dest_video, list_mpd_video, list_seg_rep_csv)
            if calc_metrics == "True":
                metrics.download_max_res_segments(mpd_path, dest_video, list_mpd_video, list_seg_rep_csv)
        elif type == "byterange":
            merger.parse_mpd_bytecode(mpd_path, dest_video,calc_metrics, list_seg_rep_csv)
        if calc_metrics == "True" and type!="youtube":
            metrics.init_vmaf_segments(dest_video)
    if log_location == 'local':
        merger.copy_init_file(path_video, dest_video)
        merger.copy_init_file(path_audio, dest_video)
        merger.copy_video_segments(path_video, dest_video, list_seg_rep_csv)
        merger.copy_audio_segments(path_audio, dest_video, list_seg_rep_csv)
    merger.prepare_video_init(dest_video, calc_metrics)
    if calc_metrics == "True":
        if type=="youtube":
            youtube.copy_youtube_segments(os.path.join(dest_video,"youtube"),os.path.join(dest_video,"vmaf"), youtube_segments_dict)
            youtube.download_maxres_youtube_movie(dest_video,mpd_path, yt_movie_title)
            youtube.youtube_vmaf_split(dest_video,chunk_duration)
            metrics.scale_vmaf(dest_video,list_seg_rep_csv,True)
            metrics.calculate_vmaf(dest_video,movie_name,date,True)
        else:
            metrics.scale_vmaf(dest_video, list_seg_rep_csv)
            metrics.calculate_vmaf(dest_video,movie_name,date)
    if merge_video == "True":
        if type == "youtube":
            youtube.copy_youtube_segments(os.path.join(dest_video,"youtube"),dest_video, youtube_segments_dict)
            merger.concat_video_segments_final(dest_video, gif_path, final_path,list_inter_names,list_seg_rep_csv, list_stall_values, path_to_log, chunk_duration, True)
        else:
            merger.prepare_audio_init(dest_video)
            merger.concat_audio_video_ffmpeg(dest_video, auto_scale, scale_resolution, list_seg_rep_csv, list_resolutions)
            merger.concat_video_segments_final(dest_video, gif_path, final_path,list_inter_names,list_seg_rep_csv, list_stall_values, path_to_log)
    if cleanup == "True":
        utils.clean_folder(dest_video)
"""
        if args.log_location != 'local':
            # check mpd type
            type = check_mpd_type(mpd_path)
            if type == "youtube":
                get_youtube_title(mpd_path)
                download_youtube_movies(dest_video, mpd_path)
                youtube_split(dest_video, 4)
            elif (type == "regular"):
                parse_mpd(log_location)
                download_audio_segments(log_location, dest_video)
                download_video_segments(log_location, dest_video)
                if calc_metrics == "True":
                    download_max_res_segments(mpd_path, dest_video)
            elif (type == "byterange"):
                parse_mpd_bytecode(mpd_path, dest_video,calc_metrics)
            if calc_metrics == "True" and type != "youtube":
                init_vmaf_segments(dest_video)
        if args.log_location == 'local':
            copy_init_file(path_video, dest_video)
            copy_init_file(path_audio, dest_video)
            copy_video_segments(path_video, dest_video)
            copy_audio_segments(path_audio, dest_video)
        prepare_video_init(dest_video, calc_metrics)
        if calc_metrics == "True":
            if type=="youtube":
                copy_youtube_segments(os.path.join(dest_video,"youtube"),os.path.join(dest_video,"vmaf"))
                download_maxres_youtube_movie(dest_video,mpd_path)
                youtube_vmaf_split(dest_video,4)
                scale_vmaf(dest_video,True)
                calculate_vmaf(dest_video,True)
            else:
                scale_vmaf(dest_video)
                calculate_vmaf(dest_video)
        if merge_video == "True":
            if merge_video == "True":
                if type == "youtube":
                    copy_youtube_segments(os.path.join(dest_video, "youtube"), dest_video)
                    concat_video_segments_final_youtube(dest_video, gif_path, final_path, 4)
            else:
                prepare_audio_init(dest_video)
                concat_audio_video_ffmpeg(dest_video, args.auto_scale, args.scale_resolution)
                concat_video_segments_final(dest_video, gif_path, final_path)
        if args.cleanup == "True":
            clean_folder(dest_video)
"""