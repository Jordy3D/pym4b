import os
import win32com.client

class File:
    def __init__(self, file_path):
        self.path = file_path
        self.name = os.path.basename(file_path)
        self.ext = os.path.splitext(file_path)[1]
        self.properties = self.get_file_properties()

        media_exts = ['.mp3', '.m4a', '.m4b', '.m4v', '.mp4', '.mov', '.avi', '.mkv', '.flac', '.wav', '.ogg', '.opus']

        if self.ext in media_exts:
            self.get_duration()

    def get_file_properties(self, metadata=[]) -> dict:
        """Get file properties using the Windows Shell API.\n
        Args:
            metadata: List of properties to retrieve. If empty, all properties are retrieved.\n
        Returns:
            Dictionary of file properties.\n
        """
        properties = {}
        try:
            shell = win32com.client.Dispatch("Shell.Application")
            namespace = shell.NameSpace(os.path.dirname(self.path))
            item = namespace.ParseName(self.name)
            
            for i in range(200):
                property_name = namespace.GetDetailsOf(None, i)
                property_value = namespace.GetDetailsOf(item, i)
                if metadata:
                    if property_name in metadata:
                        properties[property_name] = property_value
                else:
                    if property_name and property_value:
                        properties[property_name] = property_value

        except Exception as e:
            print(f"Error: {e}")

        return properties

    def get_duration(self) -> float:
        """Use ffprobe to get the duration of the file in milliseconds and store it in the properties dictionary.\n
        The file's Length property is not accurate enough for some file types.\n
        Returns:
            Success: `duration` in milliseconds.\n
            Error:   `-1`
        """

        def insert_into_dict(dictionary, key, value, index):
            keys, vals = list(dictionary.keys()), list(dictionary.values())

            keys.insert(index, key)
            vals.insert(index, value)

            return dict(zip(keys, vals))

        try:
            command = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{self.path}"'
            duration = os.popen(command).read()
            duration = float(duration) * 1000
            # add Duration to properties next to the Length property
            length_index = list(self.properties.keys()).index('Length')
            self.properties = insert_into_dict(self.properties, 'Duration', duration, length_index + 1)
            
            return duration
        except:
            return -1

    def display_properties(self, prop_filter=[]):
        """Display the file's properties.\n
        Args:
            prop_filter: List of properties to display. If empty, all properties are displayed.\n
        """
        print(f"\nProperties for {self.name}:")
        for key, value in self.properties.items():
            if prop_filter:
                if key in prop_filter:
                    print(f"{key:>15}: {value}")
            else:
                print(f"{key:>15}: {value}")

        for key in prop_filter:
            if key not in self.properties.keys():
                print(f"{key:>15}: Not found or generated")


if __name__ == "__main__":

    # Example usage:
    file_path = r'D:\Users\jordy\Documents\GitHub\pym4b\test.mp3'

    file = File(file_path)
    props = file.properties

    prop_filter = ['#', 'Title', 'Album', 'Length', 'Duration', 'Type']
    # file.get_duration()
    file.display_properties(prop_filter)


    # print("\nAll properties:")
    # file.display_properties()