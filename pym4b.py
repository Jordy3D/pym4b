import os
import subprocess
import argparse

import win32com

debug = False


# region Helper Functions
def clear_print(message, end="\n"):
    """Clears the line and prints the message"""
    print(" " * 100, end="\r")
    print(message, end=end)


def filename_string(string):
    """Removes any characters that are not allowed in filenames"""
    disallowed_chars = set(r'<>:"/\|?*')
    return "".join(c for c in string if c not in disallowed_chars).strip()


def load_metadata_from_file(file):
    command = "ffmpeg -y -loglevel error -i " + file + " -f ffmetadata -"
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    output, error = result.stdout, result.stderr
    return output, error
# endregion


# region Classes
class ABMeta:
    def __init__(self, metadata=None):
        self.raw_metadata = metadata
        self.file_name = None
        self.major_brand = None
        self.minor_version = None
        self.compatible_brands = None
        self.disc = None
        self.genre = None
        self.date = None
        self.album = None
        self.publisher = None
        self.composer = None
        self.comment = None
        self.artist = None
        self.album_artist = None
        self.encoder = None
        self.chapters = None

    # METADATA
    def load_metadata(self, file):
        """Loads the metadata from the file as raw metadata"""

        metadata = load_metadata_from_file(file)[0]

        # add the file name to the metadata in the second line
        metadata = metadata.splitlines()
        metadata.insert(1, f"file_name={file}")
        metadata = "\n".join(metadata)

        self.raw_metadata = metadata
        self.file_name = file

        self.parse_metadata()

    def parse_metadata(self):
        """Parses the raw metadata into the metadata class"""

        # split the metadata into lines
        metadata_lines = self.raw_metadata.splitlines()

        # get only the lines before the first instance of [CHAPTER]
        metadata_lines = metadata_lines[: metadata_lines.index("[CHAPTER]")]

        current_key = ""
        current_value = ""
        for line in metadata_lines:
            if line.startswith(";"):            # ignore lines starting with a ;
                continue
            if line.startswith("[CHAPTER]"):    # end of normal metadata
                break

            # look for the first instance of =, which is the key/value separator
            equals_index = line.index("=") if "=" in line else -1

            if equals_index != -1:
                current_key = line[:equals_index].lower()
                current_value = line[equals_index + 1 :]

                setattr(self, current_key, current_value)
            else:
                # if there is no =, then it is a continuation of the previous key
                # pretty sure this is only for the comment
                current_value += line

                setattr(self, current_key, current_value)

        # parse the chapters
        self.parse_chapters()

    def parse_chapters(self):
        """Parses the chapters from the raw metadata"""
        
        # split the metadata into lines
        metadata_lines = self.raw_metadata.splitlines()

        # get only the lines after the first instance of [CHAPTER]
        start_point = metadata_lines.index("[CHAPTER]")
        chapter_lines = self.raw_metadata.splitlines()[start_point:]

        # split the array of chapter lines by every instance of [CHAPTER]
        chapter_chunks = []
        current_chunk = []
        for line in chapter_lines:
            if line.startswith("[CHAPTER]"):
                # append the current chunk to the array of chunks
                chapter_chunks.append(current_chunk)
                # reset the current chunk
                current_chunk = []
            else:
                # append the line to the current chunk
                current_chunk.append(line)

        # append the last chunk to the array of chunks
        chapter_chunks.append(current_chunk)

        # remove any empty chunks
        chapter_chunks = [chunk for chunk in chapter_chunks if chunk != []]

        chapters = []
        for i, chunk in enumerate(chapter_chunks):
            # create a new chapter object
            chapter = ABChapter()                       # examples below
            chapter.timebase = chunk[0].split("=")[1]   # timebase=1/1000
            chapter.start = chunk[1].split("=")[1]      # start=0
            chapter.end = chunk[2].split("=")[1]        # end=52387
            chapter.title = chunk[3].split("=")[1]      # title=Chapter 1
            chapter.track_number = i + 1                

            chapters.append(chapter)

        self.chapters = chapters

    # FILES
    def split(self, convert_to_mp3=True, bitrate=None, delete_m4b=False):
        """Splits the file into multiple files based on the chapters"""

        file = self.file_name
        chapters = self.chapters

        file = file.replace('"', "")

        # get the filename from the file path
        filename = os.path.basename(file)
        # get the filename splitting at the last period
        folder_name = filename.rsplit(".", 1)[0]
        folder_name = f"{folder_name}_split"

        # create a directory for the split files
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)

        # split the file into multiple files
        for chapter in chapters:
            # get the start and end times of the chapter
            start = chapter.start
            end = chapter.end

            # get the title of the chapter
            title = chapter.title
            file_tile = filename_string(title)

            # get the track number of the chapter
            track = chapter.track_number

            # convert the start and end times from milliseconds to seconds
            start = int(start) / 1000
            end = int(end) / 1000

            # create the command
            command = f'ffmpeg -y -loglevel error -i "{file}" -ss {start} -to {end} -c copy '

            metadata = { "title": title, "track": track }

            # add the metadata to the file
            if metadata != {}:
                for key in metadata:
                    command += f'-metadata {key}="{metadata[key]}" '

            # add the output file an mp3 conversion
            command += f'"{folder_name}/{track}. {file_tile}.m4b"'

            if debug:
                print(f"\nRunning command: {command}")

            # clear the line
            clear_print(f"Splitting chapter: {title}...", end="\r")

            # run the command
            os.system(command)

            if convert_to_mp3:
                # convert the file to an mp3 file
                self.convert_file(f"{track}. {file_tile}.m4b", folder_name, delete_m4b=delete_m4b, bitrate=bitrate)
        # get the embedded cover art
        command = f'ffmpeg -y -loglevel error -i "{file}" -an -vcodec copy "{folder_name}/cover.jpg"'

        if debug:
            print(f"\nRunning command: {command}")

        # run the command
        os.system(command)

        clear_print("Done splitting file!")

    def convert_file(self, file, folder, delete_m4b=False, bitrate=None):
        """Converts the file to an MP3 file"""

        file_path = f"{folder}/{file}"

        # get the filename without the extension
        filename = os.path.basename(file_path)
        filename = filename.rsplit(".", 1)[0]

        command = f'ffmpeg -y -loglevel error -i "{file_path}" -vn -c:a libmp3lame '
        if bitrate is not None:
            # remove the k from the bitrate
            bitrate = bitrate.replace("k", "")
            command += f"-b:a {bitrate}k "
        command += f'"{folder}/{filename}.mp3"'

        if debug:
            print(f"\nRunning command: {command}")

        clear_print(f"Converting file: {filename}...", end="\r")
        os.system(command)

        if delete_m4b:
            print(f"Deleting file: {file_path}", end="\r")
            os.remove(f'{folder}/{file}')


class ABChapter:
    def __init__(
        self, timebase=None, start=None, end=None, title=None, track_number=None
    ):
        self.timebase = timebase
        self.start = start
        self.end = end
        self.title = title
        self.track_number = track_number

# endregion
        
def from_m4b(file, convert_to_mp3=True, bitrate=None, delete_m4b=False):
    """Splits the file into multiple files based on the chapters"""
    file = f'"{file}"'

    # prepare metadata object
    abm = ABMeta()

    print(f"Loading metadata from {file}...", end="\r")
    abm.load_metadata(file=file)
    clear_print(f"Loaded metadata from {file}!")

    print("Chapters:")
    for chapter in abm.chapters:
        print(f"  {chapter.track_number} - {chapter.title}")

    abm.split(convert_to_mp3=convert_to_mp3, bitrate=bitrate, delete_m4b=delete_m4b)

    print("Done!")


def to_m4b(folder, chapters, chapter_filetype="m4b", delete_chapters=False):
    import file as f

    """Combines the chapters into a single file"""  

    # get the chapter files
    chapter_files = [f"{folder}/{chapter}" for chapter in chapters if chapter.endswith(chapter_filetype)]

    print(f"Loading files...", end=" ")
    chapter_files = [f.File(chapter) for chapter in chapter_files]
    chapter_files.sort(key=lambda x: int(x.properties["#"]))
    print("Done!")

    # store the first file for getting basic metadata
    first_file = chapter_files[0]

    title = first_file.properties["Album"]
    folder = filename_string(title)
    # create a directory for the combined file
    os.makedirs(f"combined/{folder}", exist_ok=True)
    artist = first_file.properties["Contributing artists"]

    def length_to_milliseconds(length):
        """Converts a length string to milliseconds"""
        length = length.split(":")
        hours = int(length[0])
        minutes = int(length[1])
        seconds = int(length[2])
        return (hours * 60 * 60 + minutes * 60 + seconds) * 1000

    # create a metadata file
    print(f"Creating metadata file for {first_file.properties['Album']}...", end=" ")
    metadata_file = f"combined/{folder}/metadata.txt"
    with open(metadata_file, "w", encoding="utf-8") as file:
        file.write(";FFMETADATA1\n")
        file.write(f"title={title}\n")
        file.write(f"album={title}\n")
        file.write(f"artist={artist}\n")

        start = 0
        for i, chapter in enumerate(chapter_files):
            chapter_file = chapter
            file.write(f"\n[CHAPTER]\n")
            file.write(f"TIMEBASE=1/1000\n")
            file.write(f"START={start}\n")
            end = chapter_file.get_duration()
            end += start
            file.write(f"END={end}\n")
            file.write(f"TITLE={chapter_file.properties['Title']}\n")

            start = end
    print("Done!")

    print(f"Creating concat file...", end=" ")
    concat_file = f"combined/{folder}/concat.txt"
    with open(concat_file, "w", encoding="utf-8") as file:
        for chapter in chapter_files:
            path = chapter.path
            file.write(f"file 'file:{path}'\n")
    print("Done!")

    # create the command
    print(f"Creating merged MP3 file...", end=" ")
    command = f'ffmpeg -y -loglevel error -f concat -safe 0 -i "{concat_file}" -c copy "combined/{folder}/output.mp3"'
    os.system(command)
    print("Done!")

    # convert output to m4a
    print(f"Converting to M4A...", end=" ")
    command = f'ffmpeg -y -loglevel error -i "combined/{folder}/output.mp3" "combined/{folder}/output.m4a"'
    os.system(command)
    print("Done!")

    print(f"Converting to M4B...", end=" ")
    command = f'ffmpeg -y -loglevel error -i "combined/{folder}/output.m4a" -i "{metadata_file}" -map_metadata 1 -codec copy "combined/{folder}/{folder}.m4b"'
    os.system(command)
    print(command)

    print("Done!")

    print(f"Deleting temp files...", end=" ")
    os.remove(metadata_file)
    os.remove(concat_file)
    os.remove(f"combined/{folder}/output.mp3")
    os.remove(f"combined/{folder}/output.m4a")
    print("Done!")

    
if __name__ == "__main__":
    os.system("TITLE pym4b")

    # Set up the argument parser
    parser = argparse.ArgumentParser(description="Split M4B files into chapters.")
    parser.add_argument("-i", "--input", help="Path input file or folder.", default=None, dest="file_path")
    parser.add_argument("-c", "--convert", help="Convert the chapters to MP3.", action="store_true", default=False)
    parser.add_argument("-b", "--bitrate", help="Bitrate to encode the chapters at.", default=None)
    parser.add_argument("-d", "--delete", help="Delete the original M4B file after converting.", action="store_true", default=False)
    parser.add_argument("-cf", "--chapter_filetype", help="Filetype of the chapters.", default="mp3")
    args = parser.parse_args()

    # Get the arguments
    file_path = args.file_path
    convert = args.convert
    bitrate = args.bitrate
    convert_delete = args.delete
    chapter_filetype = args.chapter_filetype

    if file_path == None:
        file_path = input("Enter the input file or folder: ")

    if file_path == "":
        print("No file path entered.")
        exit()

    # Clean up the file path
    if file_path.startswith("& "):
        file_path = file_path[2:]
    if file_path.startswith("'") and file_path.endswith("'"):
        file_path = file_path[1:-1]
    if file_path.startswith('"') and file_path.endswith('"'):
        file_path = file_path[1:-1]

    # check if the file exists
    if not os.path.exists(file_path):
        print("File does not exist.")
        input("Press enter to exit...")
        exit()

    # if the input is a .m4b file
    if file_path.endswith(".m4b"):
        from_m4b(file_path, convert_to_mp3=convert, bitrate=bitrate, delete_m4b=convert_delete)
    # if the input is a folder
    if os.path.isdir(file_path):
        to_m4b(file_path, os.listdir(file_path), chapter_filetype=chapter_filetype, delete_chapters=False)