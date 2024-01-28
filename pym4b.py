import os
import argparse

debug = False

def clear_print(message, end="\n"):
    """Clears the line and prints the message"""
    print(" " * 100, end="\r")
    print(message, end=end)

def filename_string(string):
    """Removes any characters that are not allowed in filenames"""
    return "".join([c for c in string if c.isalpha() or c.isdigit() or c == " " or c == "." or c == "_" or c == "-"]).rstrip()


class ABMeta:
    # contains the metadata of the file:
    # major_brand, minor_version, compatible_brands, disc, genre, date, album, publisher, copyright, composer, comment, artist, album_artist, encoder, and an array of chapters, 
        
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

    def parse_metadata(self):
        # parse the metadata into the metadata class
        # split the metadata into lines
        metadata_lines = self.raw_metadata.splitlines()

        # get only the lines before the first instance of [CHAPTER]
        metadata_lines = metadata_lines[:metadata_lines.index("[CHAPTER]")]

        current_key = ""
        current_value = ""
        for line in metadata_lines:
            # ignore lines that start with a semicolon
            if line.startswith(";"):
                continue
            # if the line is [CHAPTER], then we've reached the end of the metadata
            if line.startswith("[CHAPTER]"):
                break

            # look for the first instance of an equals sign
            equals_index = line.index("=") if "=" in line else -1
            # if there is an equals sign, the content before the equals sign is the key
            # and the content after the equals sign is the value
            if equals_index != -1:
                current_key = line[:equals_index]
                current_value = line[equals_index + 1:]
                
                # set key to lowercase
                current_key = current_key.lower()

                # set the value of the key in the metadata class
                setattr(self, current_key, current_value)
            else:
                # if there is no equals sign, then it's a continuation of the previous key
                current_value += line
                
                # set key to lowercase
                current_key = current_key.lower()

                # set the value of the key in the metadata class
                setattr(self, current_key, current_value)

        # parse the chapters
        self.parse_chapters()
                
    def parse_chapters(self):
        # parse the chapters into the metadata class
        # split the metadata into lines
        metadata_lines = self.raw_metadata.splitlines()

        # get only the lines after the first instance of [CHAPTER]
        chapter_lines = self.raw_metadata.splitlines()[metadata_lines.index("[CHAPTER]"):]

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
        for chunk in chapter_chunks:
            # create a new chapter object
            chapter = ABChapter()
            chapter.timebase = chunk[0].split("=")[1]
            chapter.start = chunk[1].split("=")[1]
            chapter.end = chunk[2].split("=")[1]
            chapter.title = chunk[3].split("=")[1]

            chapters.append(chapter)

        # set the track number of each chapter
        for chapter in chapters:
            chapter.track_number = chapters.index(chapter) + 1

        self.chapters = chapters       

    def split(self, convert_to_mp3=True, bitrate=None, delete_m4b=False):
        """Splits the file into multiple files based on the chapters"""
        # split the file into multiple files based on the chapters
        file = self.file_name
        chapters = self.chapters

        file = file.replace("\"", "")

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
            command = f"ffmpeg -y -loglevel error -i \"{file}\" -ss {start} -to {end} -c copy "

            metadata = {
                "title": title,
                "track": track,
            }

            # add the metadata to the file
            if metadata != {}:
                for key in metadata:
                    command += f"-metadata {key}=\"{metadata[key]}\" "

            # add the output file an mp3 conversion
            command += f"\"{folder_name}/{track}. {file_tile}.m4b\""

            if debug:
                print(f"\nRunning command: {command}")

            # clear the line
            clear_print(f"Splitting chapter: {title}...", end="\r")

            # run the command
            os.system(command)

        # get the embedded cover art
        command = f"ffmpeg -y -loglevel error -i \"{file}\" -an -vcodec copy \"{folder_name}/cover.jpg\""

        if debug:
            print(f"\nRunning command: {command}")

        # run the command
        os.system(command)

        clear_print("Done splitting file!")

        if convert_to_mp3:
            print("Converting files to MP3...")
            # convert the files to mp3
            convert_files(folder_name, delete_m4b=delete_m4b, bitrate=bitrate)

            clear_print("Done converting files!")

class ABChapter:
    # a chapter contains the following:
    # timebase, start, end, title  
    
    def __init__(self, timebase=None, start=None, end=None, title=None, track_number=None):
        self.timebase = timebase
        self.start = start
        self.end = end
        self.title = title
        self.track_number = None

def get_metadata(file):
    """Gets the metadata of the file and returns it as raw text"""
    command = 'ffmpeg -y -loglevel error -i ' + file + ' -f ffmetadata temp.txt'
    
    if debug:
        print(f"Running command: {command}")

    os.system(command)

    # read the metadata from the temp file
    with open("temp.txt", "r", encoding="utf-8") as f:
        metadata = f.read()

    # delete the temp file
    if not debug:
        os.remove("temp.txt")

    # add the file name to the metadata in the second line
    metadata = metadata.splitlines()
    metadata.insert(1, f"file_name={file}")
    metadata = "\n".join(metadata)
    
    return metadata

def parse_metadata(metadata):
    """Parses the metadata into a metadata object"""
    meta_object = ABMeta(metadata)
    meta_object.parse_metadata()

    return meta_object

def load_metadata(file):
    """A shortcut for getting and parsing the metadata. 

    Calls `get_metadata()` and `parse_metadata()` and returns the metadata object.
    """
    raw_metadata = get_metadata(file)
    metadata = parse_metadata(raw_metadata)

    return metadata

def convert_files(folder, delete_m4b=False, bitrate=None):
    """Converts all M4B files in the folder to MP3 files"""

    # get all the files in the folder
    files = os.listdir(folder)

    # get only the M4B files
    files = [file for file in files if file.endswith(".m4b")]

    # convert each file to an MP3 file
    for file in files:
        # get the file path
        file_path = f"{folder}/{file}"

        # get the filename without the extension
        filename = os.path.basename(file_path)
        filename = filename.rsplit(".", 1)[0]

        # create the command
        command = f"ffmpeg -y -loglevel error -i \"{file_path}\" -vn -c:a libmp3lame " 
        if bitrate != None:
            # remove the k from the bitrate
            bitrate = bitrate.replace("k", "")
            command += f"-b:a {bitrate}k "
        command += f"\"{folder}/{filename}.mp3\""

        if debug:
            print(f"\nRunning command: {command}")

        clear_print(f"Converting file: {filename}...", end="\r")
        os.system(command)

        if delete_m4b:
            os.remove(file_path)


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

    file_path = f"\"{file_path}\""
 
    print(f"Loading metadata from {file_path}...", end="\r")
    metadata = load_metadata(file_path)
    clear_print(f"Loaded metadata from {file_path}!")

    print("Chapters:")
    for chapter in metadata.chapters:
        print(f"  {chapter.track_number} - {chapter.title}")

    metadata.split(convert_to_mp3=convert, bitrate=bitrate, delete_m4b=convert_delete)

    print("Done!")