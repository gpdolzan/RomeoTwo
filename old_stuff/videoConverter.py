import sys
from moviepy.editor import VideoFileClip
import ffmpeg
import os
import subprocess

def get_video_info(file_name):
    with VideoFileClip(file_name) as clip:
        fps = clip.fps
        duration = clip.duration
        n_frames = clip.reader.nframes
        size = clip.size

    info = {
        "fps": fps,
        "duration": duration,
        "n_frames": n_frames,
        "width": size[0],
        "height": size[1]
    }

    return info

def convert_video(file_name, output_resolution, output_fps):
    dir_name = os.path.dirname(file_name)  # Get the directory of the video
    if not dir_name:  # Handle cases where the video is in the current directory
        dir_name = "."

    base_name = os.path.basename(file_name)  # Get the video's base filename

    # Construct the new filename
    output_file = os.path.join(dir_name, "converted_" + base_name)

    # Check if the file already exists and delete if true
    if os.path.exists(output_file):
        os.remove(output_file)

    stream = ffmpeg.input(file_name)
    stream = ffmpeg.output(stream, output_file, vf=f'scale={output_resolution}', r=output_fps, vcodec='libx264')

    # Suppress output from ffmpeg
    cmd = ffmpeg.compile(stream)
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def main():
    if len(sys.argv) < 2:
        print("Usage: python script_name.py video_file [resolution] [fps]")
        sys.exit(1)

    video_file = sys.argv[1]

    # Get the video's information
    info = get_video_info(video_file)

    print("Video Information:")
    print(f"Resolution: {info['width']}x{info['height']}")
    print(f"Frame rate: {info['fps']}")
    print(f"Duration (seconds): {info['duration']}")
    print(f"Number of frames: {info['n_frames']}")

    # If only video filename is provided, just print info and exit
    if len(sys.argv) == 2:
        sys.exit(0)

    # Default values
    resolution = f"{info['width']}x{info['height']}"  # Default to the current video's resolution
    fps = info['fps']  # Default to the current video's fps

    if 'x' in sys.argv[2]:  # Looks like a resolution
        resolution = sys.argv[2]
    else:  # Assume it's fps
        fps = sys.argv[2]
        if float(fps) > float(info['fps']):
            print(f"Input fps {fps} is higher than the video's current fps {info['fps']}. Aborting.")
            sys.exit(1)

    if len(sys.argv) == 4:  # If both resolution and fps are provided
        fps = sys.argv[3]
        if float(fps) > float(info['fps']):
            print(f"Input fps {fps} is higher than the video's current fps {info['fps']}. Aborting.")
            sys.exit(1)

    # Checking resolution constraints
    desired_width, desired_height = map(int, resolution.split('x'))
    if desired_width > info['width'] or desired_height > info['height']:
        print(f"Desired resolution {resolution} is larger than the video's current resolution {info['width']}x{info['height']}. Using video's current resolution instead.")
        resolution = f"{info['width']}x{info['height']}"

    print("Converting video...")
    convert_video(video_file, resolution, str(fps))
    print("Conversion complete!")



if __name__ == "__main__":
    main()
