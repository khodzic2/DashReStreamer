#all functions needed for metrics calculation

import os
import platform
import utils
import re
import pandas as pd

vmaf_list = []
vmaf_list1 = []
vmaf_list2 = []
vmaf_list3 = []

def calculate_vmaf(paths,  movie_name, date, checkYoutube=False, model_path='resources/vmaf_v0.6.1.json', model_path4k='resources/vmaf_4k_v0.6.1.json'):
    #movie name is parsed from mpd
    mv=movie_name.replace(" ", "")
    #temporary list to save every result row
    temp_list=[]

    path=os.path.join(paths,"vmaf")
    ##change hardcoded .mp4 to suffix variable
    suffix=""
    if checkYoutube:
        suffix = '.mkv'
    else:
        suffix = '.mp4'

#in vmaf folder find every original and reference segment and pair them to calculate metrics
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).startswith("scaled"):
            segment = re.search("(\d+)(?!.*\d)", filename.split(suffix)[0]).group(1)
            video1=str(filename)
            for file2 in os.listdir(path):
                filename2 = os.fsdecode(file2)
                if str(filename2).endswith("segment" + segment + suffix) and str(filename2).startswith("inited_max"):
                    video2 = str(filename2)
                    path_video_orig = os.path.join(path, video1)
                    path_video_ref = os.path.join(path, video2)
                    log= video1.split(suffix)[0]+'.xml'
                    #to avoid vmaf modelpath bug in windows ...
                    os.chdir(os.path.dirname(os.path.realpath(__file__)))
                    # ffmpeg command to calculate all metrics with specific vmaf model and store them to xml log
                    komanda = "ffmpeg -i " + path_video_orig+ " -i " + path_video_ref +  ' -lavfi libvmaf=model_path="' + model_path + '":n_threads=4:psnr=1:ssim=1:ms_ssim=1:log_fmt=xml:log_path=' + log + ' -f null - '
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
                    for index, row in (df.loc[df['name'] == 'psnr_y']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'float_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ms_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'float_ms_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    #adding all metrics for 1 segment to vmaf_list which will be stored to a final csv
                    vmaf_list.append(temp_list.copy())
                    temp_list.clear()
                    #delete ffmpeg metrics log when they are no longer needed
                    if os.path.isfile(log):
                        os.remove(log)

                    #calculate metrics with 4k model
                    komanda = "ffmpeg -i " + path_video_orig + " -i " + path_video_ref + ' -lavfi libvmaf=model_path="' + model_path4k + '":n_threads=4:psnr=1:ssim=1:ms_ssim=1:log_fmt=xml:log_path=' + log + ' -f null - '

                    os.system(komanda)
                    df = pd.read_xml(log,
                                     xpath="/VMAF/pooled_metrics/metric")
                    temp_list.append("segment" + segment)
                    temp_list.append(model_path4k)
                    for index, row in (df.loc[df['name'] == 'vmaf']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'psnr']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'psnr_y']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'float_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ms_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'float_ms_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    vmaf_list1.append(temp_list.copy())
                    temp_list.clear()
                    if os.path.isfile(log):
                        os.remove(log)

                    #4k model + phone
                    komanda = "ffmpeg -i " + path_video_orig + " -i " + path_video_ref + ' -lavfi libvmaf=model_path="' + model_path4k + '":n_threads=4:psnr=1:ssim=1:ms_ssim=1:phone_model:log_fmt=xml:log_path=' + log + ' -f null - '
                    os.system(komanda)
                    df = pd.read_xml(log,
                                     xpath="/VMAF/pooled_metrics/metric")
                    temp_list.append("segment" + segment)
                    temp_list.append(model_path4k + "_phone")
                    for index, row in (df.loc[df['name'] == 'vmaf']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'psnr']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'psnr_y']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'float_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ms_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'float_ms_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    vmaf_list2.append(temp_list.copy())
                    temp_list.clear()
                    if os.path.isfile(log):
                        os.remove(log)

                    #normal fullhd model + phone
                    komanda = "ffmpeg -i " + path_video_orig + " -i " + path_video_ref + ' -lavfi libvmaf=model_path="' + model_path + '":n_threads=4:psnr=1:ssim=1:ms_ssim=1:phone_model:log_fmt=xml:log_path=' + log + ' -f null - '
                    os.system(komanda)
                    df = pd.read_xml(log,
                                     xpath="/VMAF/pooled_metrics/metric")
                    temp_list.append("segment" + segment)
                    temp_list.append(model_path + "_phone")
                    for index, row in (df.loc[df['name'] == 'vmaf']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'psnr']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'psnr_y']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'float_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'ms_ssim']).iterrows():
                        temp_list.append(row['mean'])
                    for index, row in (df.loc[df['name'] == 'float_ms_ssim']).iterrows():
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

    #saving 4 different csv files for 4 different vmaf models
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


def scale_vmaf(paths,list_seg_rep_csv,youtube_check=False):
    #scale every segment to a maximum available resolution to use it as reference for metric calculation
    path=os.path.join(paths,"vmaf")
    #find maximum resolution segment and save its resolution to a variable
    if youtube_check:
        x = utils.helper_get_max_resolution_fps_duration(path, "inited_max", list_seg_rep_csv,".mkv")
    else:
        x = utils.helper_get_max_resolution_fps_duration(path, "inited_max", list_seg_rep_csv)
    for file2 in os.listdir(path):
        filename2 = os.fsdecode(file2)
        #every inited segment not already scaled
        if (str(filename2).startswith("inited") or str(filename2).startswith("merged")) and not(str(filename2).startswith("inited_max")):
            video = str(filename2)
            path_i_video = os.path.join(path, video)
            path_final = os.path.join(path, "scaled" + video)
            #scale every segment to a maximum resolution using ffmpeg
            komanda4 = 'ffmpeg -i ' + path_i_video + ' -vf scale=' + str(x[1]) + ':' + str(x[3]) + " " + path_final
            os.system(komanda4)

def init_vmaf_segments (paths):
    # combines video segments in vmaf folder with init file
    init = ""
    #check on which platform script is run
    osystem = platform.system()
    if osystem == 'Windows':
        suffix = "type "
    elif osystem == 'Linux':
        suffix = "cat "
    # add for mac :)
    else:
        suffix = "cat "

    path=os.path.join(paths,"vmaf")
    #first find init file
    for file in os.listdir(path):
        filename = os.fsdecode(file)
        if str(filename).__contains__("dash_init"):
            init = filename
    #than find every video segment and combine it with init to get playable .mp4 file
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


def download_max_res_segments(mpd_url, dest, list_mpd_video, list_seg_rep_csv):
    #download max bandwidth segments needed for vmaf and other metric
    destination=os.path.join(dest,"vmaf")
    if not os.path.exists(destination):
        os.makedirs(destination)
    #in videoSegments.txt segments paths for download will be stored
    full_path = os.path.join(destination, "videoSegments.txt")
    open(full_path, 'w')
    mpd_url2 = mpd_url.rsplit("/", 1)[0]
    #for every segment parsed from log
    for key in list_seg_rep_csv:
        #for every segment get max resolution parsed from mpd and stored in list_mpd_video
        substring = str(list_mpd_video[max(list_mpd_video)]).replace('$Number$', str(key))
        #save url to download in file
        komanda = " echo " + mpd_url2 + "/" + substring + " >> " + full_path
        os.system(komanda)
    komanda = " echo " + mpd_url2 + "/" + str(list_mpd_video[0]) + " >> " + full_path
    os.system(komanda)
    #check on which OS script is run
    osystem = platform.system()
    if osystem == 'Linux':
        komanda = 'wget -i ' + full_path + ' -P ' + destination
    elif osystem == 'Windows':
        os.chdir(destination)
        komanda = 'for /f "tokens=*" %a in (' + full_path + ') do curl -O %a'
    # add option for mac :)
    else:
        komanda = 'wget -i ' + full_path + ' -P ' + destination
    # download all files to specified location
    os.system(komanda)
