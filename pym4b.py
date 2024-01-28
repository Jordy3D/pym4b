import os
import subprocess
import argparse

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

        # get the embedded cover art
        command = f'ffmpeg -y -loglevel error -i "{file}" -an -vcodec copy "{folder_name}/cover.jpg"'

        if debug:
            print(f"\nRunning command: {command}")

        # run the command
        os.system(command)

        clear_print("Done splitting file!")

        if convert_to_mp3:
            print("Converting files to MP3...")
            # convert the files to mp3
            self.convert_files(folder_name, delete_m4b=delete_m4b, bitrate=bitrate)

            clear_print("Done converting files!")

    def convert_files(self, folder, delete_m4b=False, bitrate=None):
        """Converts all M4B files in the folder to MP3 files"""

        # get the m4b files in the folder
        files = os.listdir(folder)
        files = [file for file in files if file.endswith(".m4b")]

        # convert each file to an MP3 file
        for file in files:
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
                os.remove(file_path)


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

if __name__ == "__main__":
    os.system("TITLE Bane's M4B Splitter")

    # Set up the argument parser
    parser = argparse.ArgumentParser(description="Split M4B files into chapters.")
    parser.add_argument("-i", "--input", help="Path to the M4B file.", default=None, dest="file_path")
    parser.add_argument("-c", "--convert", help="Convert the chapters to MP3.", action="store_true", default=False)
    parser.add_argument("-b", "--bitrate", help="Bitrate to encode the chapters at.", default=None)
    parser.add_argument("-d", "--delete", help="Delete the original M4B file after converting.", action="store_true", default=False)
    args = parser.parse_args()

    # Get the arguments
    file_path = args.file_path
    convert = args.convert
    bitrate = args.bitrate
    convert_delete = args.delete

    if file_path == None:
        file_path = input("Enter the path to the M4B file: ")

    if file_path == "":
        print("No file path entered.")
        exit()

    # Clean up the file path
    if file_path.startswith("& "):
        file_path = file_path[2:]
    if file_path.startswith("'") and file_path.endswith("'"):
        file_path = file_path[1:-1]

    # check if the file exists
    if not os.path.exists(file_path):
        print("File does not exist.")
        exit()

    file_path = f'"{file_path}"'

    # prepare metadata object
    abm = ABMeta()

    print(f"Loading metadata from {file_path}...", end="\r")
    abm.load_metadata(file=file_path)
    clear_print(f"Loaded metadata from {file_path}!")

    print("Chapters:")
    for chapter in abm.chapters:
        print(f"  {chapter.track_number} - {chapter.title}")

    abm.split(convert_to_mp3=convert, bitrate=bitrate, delete_m4b=convert_delete)

    print("Done!")
