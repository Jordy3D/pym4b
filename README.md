<div align="center">
  <h1>pym4b</h1>
  <p>...m4b to mp3 to m4b to mp3 to...</p>
</div>

## Features

### Split

- split m4b files into chapters
- set chapter metadata on chapters
  - title
  - track number
- convert the chapters to mp3

There's also a class that contains the metadata, in case you want to do something with it. 

### Stitch

- stitch chapters into m4b files
- set chapter metadata in stitch
  - title
  - timestamp
 
There's also also a class that does a bit of file information handling as well. That'll be cleaned up a little later...

## Requirements

- ffmpeg
- python3

\**with the addition of stitching relying on a bit of file metadata, this might only work on Windows. Untested elsewhere.*

## Usage

Basic usage for splitting an m4b file (the initial use-case of this tool) is:  
```bash
python pym4b.py -i <inputfile>
```

### Options

- `-i` or `--input` - input m4b file (SPLIT) or input folder (STITCH)
- `-c` or `--convert` - SPLIT: convert the resulting chapters to mp3
- `-b` or `--bitrate` - SPLIT: bitrate for the mp3 conversion (default: keep original bitrate)
- `-d` or `--delete` - SPLIT: delete the original m4b file after conversion
- `-cf` or `--chapter_filetype` - STITCH: the filetype of your chapters when you go to stitch them

### TODO

- [ ] clean up the code
- [ ] option to set output directory
- [ ] more metadata options if needed
- [ ] chapter data override in the event that the metadata is wrong
