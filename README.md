# logMerger
This software aims to provide fast way to reproduce mp4 video with audio including all stalls and resolution changes from information stored in video log. Log is created on client in the time when video is originally watched where information about every adaptive stream segment downloaded to cliend is stored. Log can include many information like segment(chunk) index, duration, arrival time, height, width, fps, bitrate and other. For this software to work properly it is neccesary to have stored information about segment(chunk) index and bitrate and for eventual stalls to have information about stall duration and between which two segments it ocurred. Currently tab delimited, and comma separated value files are supported for log files. In picture 1 example of video log is shown.

![alt text](https://image.prntscr.com/image/ajXgmN4qS72U0hmfclQdCA.png)

Picture 1 - Video log example

Software is implemented in python programming language, version 3.10.0. Python modules used in implementation are: pandas, version 1.3.5, configparser, version 5.2.0 and mpegdash, version 0.3.0. First step is to parse video log file . This is implemented in two functions: read_replevels_log and  read_stalls_log. Read_replevels_log function takes 4 arguments: path to where file is stored, names of segment(chunk) index and bitrate column names in log and separator type, either csv or tab.  Log is parsed and result is saved in dictionary where key is index and value is bitrate. Read_stalls_log function also takes 4 arguments: path to where file is stored, names of segment(chunk) index and stall duration column names in log and separator type, either csv or tab. Log is parsed and result is saved in dictionary where key is index and value is stall duration.

Next step is to prepare all logged segments. Segments can be downloaded from server using url to mpd file or can be transferred from folder where all segments are locally stored. If segments are stored locally than those 3 functions are called:  copy_init_file,  copy_video_segments and  copy_audio_segments.  All those funcions takes two parameters: path to where segments, either audio or vide are stored, and path to destination where segments are going to be copied. In this function all files in parameter path are looped looking for init file, when init file is found it is copied to destination folder. This function is called two times if audio and video segments and init files are in different destinations. Than functions copy_video_segments and copy_audio_segments are called. They use dictionary created earlier in read_repleveles_log function to determine which segments to copy, finds them in parameter folder matching names with regular expression and than copies them to destination folder. If segments are not stored locally then they can be downloaded from server using url to where mpd file is stored. MPD (media presentation description) are XML (extensible markup language) files that contains information about stream and that a DASH client uses to determine which assets to request in order to perform adaptive streaming of the content [citat?]. MPD file example is shown in picture 2. 

![alt text](https://image.prntscr.com/image/ajXgmN4qS72U0hmfclQdCA.png)

Picture 2 - MPD file example

To parse this file python module mpegdash [citat link na github] was used to parse mpd file into python object with points of interest such as audio and video suburls saved into dictionaries to use them in latter functions for segments download. This is implemented in function parse_mpd that url to where mpd file is stored on server as argument. Functions download_video_segments and download_audio segments takes 3 parameters: url to mpd file, path to destination folder where segments are going to be downloaded, and os type to determine which operating system commands to use for remote download. Dictionaries created in parse_mpd are used with some regex manipulation to match segment(chunk) indexes in urls and than those segments are downloaded to destination folder. After this step all video and audio segments needed to reproduce video are saved in same destination locally.

Next step is to combine audio and video segments with their respective init files. That is implemented in two functions: prepare_video_init and prepare_audio init. They take two input parameters: path to where segments and init files are stored and operating system type because different terminal commands are used to combine files on windows and linux operating systems. Executing those functions results in new audio segments of .avi (audio vide interleave) type, and video segments of .mp4 (MPEG-4 video file format) type and they are stored in same folder as original segments. 

After that audio and video segments are combined into mkv segments using ffmpeg library. It is implemented in concat_audio_video_ffmpeg function that takes two parameters: path to where segments are stored and bool variable that determines wheter segments are going to be scaled to a resolution of a segment with maximal resolution of all segments to achieve some players playback manner. Concating segments is achieved using ffmpeg library as shown in code 1:


command = "ffmpeg -fflags +genpts -i " + path_video + " -i " + path_audio + " -c copy " + path_i_video
code 1

If autoscale option is included than first segment with max resolution is determined and then all segments are scaled as shown in code 2:

command = 'ffmpeg -i ' + path_i_video + ' -vf scale=' + str(max-height)+ + ':' + str(max-width) + " " + path_final
code 2

Final step is to create final video from segments with all resolution changes and stalls incorporated. That is implemented in function concat_audio_video_ffmpeg_final that takes 5 parameters: path to where segments are stored, path to where loading screen gif is scored, path to where final video should be stored, and operating system type. In this function, all segments are sorted and looped over, when stall is detected in dictionary created in step 1 then helper functions to create stalled segments with gif are called. To create stalled segment, first step was to extract last frame from a last segment before stall happened. That is achieved using ffmpeg as shown in code 3:

command= 'ffmpeg -sseof -3 -i ' + file_path + ' -update 1 -q:v 1 ' + jpg_path

After that this frame is extentend into video of stall duration with silence audio added as shown in code 4:

command = 'ffmpeg -loop 1 -i ' + jpg_path + ' -f lavfi -i anullsrc=channel_layout=' + str(audio_layout))+ ':sample_rate=' + str(audio_sample_rate) + ' -t ' + str(stall_duration) + ' -c:a ' + str(audio_codec) + ' -c:v libx264 -t ' + str(
    stall_duration) + ' -pix_fmt yuv420p -vf scale=' + str(video_height) + ':' + str(video_width) + ' -r ' + str(video_fps) + ' -y ' + path_mp4s

Information about video and audio metadata are obtained using ffprobe library. After that this stall segment is concated with original segment that was last segment before stall happened. Finally gif is added to a stalled part of segment using next ffmpeg command (code 5):

command = 'ffmpeg -i ' + path_mp4ss + ' -ignore_loop 0 -i ' + path_to_gif + ' -filter_complex "[1:v]format=yuva444p,scale=80:80,setsar=1,rotate=PI/6:c=black@0:ow=rotw(PI/6):oh=roth(PI/6) [rotate];[0:v][rotate] overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:shortest=1:enable=' + "'gte(t," + str(segment_duration) + ")'"""
 + '" -codec:a copy -y ' + ss_path


After all segments are prepared, they are merged into final video using ffmpeg concat method. When 
final video is created, all other files created in the process are cleaned calling function clean_folder. Parameters can be send to script from terminal or they can be stored in config file. Config .ini file is supported and example of config file is shown in picture 3:

![alt text](https://image.prntscr.com/image/ajXgmN4qS72U0hmfclQdCA.png)

Picture 3 - config file example

Parameters can be also sent directly from terminal when calling script like in example:

python .\latest_main.py --path_to_log="F:\Users\Kerim\Downloads\log.txt" --rep_lvl_column="Rep_Level" --chunk_index_column="Chunk_Index" -
-log_separator="tab" --stall_dur_column="Stall_Dur" --path_video="F:\Users\Kerim\Desktop\Darijo-projekat\skripta\bbb\x264\bbb\DASH_Files\full" --dest_video="F:\Users\Kerim\Desktop\Dar
ijo-projekat\skripta\bbb\x264\bbb\DASH_Files\full\merging" --path_audio="F:\Users\Kerim\Desktop\Darijo-projekat\skripta\bbb_audio\x264\bbb\DASH_Files\audio\full" --os="win" --gif_path
="F:\Users\Kerim\Desktop\Darijo-projekat\skripta\bbb\x264\bbb\DASH_Files\full\merging\gif.gif" --final_path="F:\Users\Kerim\Desktop\Darijo-projekat\skripta\bbb\x264\bbb\DASH_Files\ful
l\merging\final" --concat_type=0

How explained steps are connected is shown in activity diagram in picture 4:

![alt text](https://image.prntscr.com/image/ajXgmN4qS72U0hmfclQdCA.png)
Picture 4: Software activity diagram 


