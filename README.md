<div align="center">
  <h1>pym4b</h1>
  <p>split m4b files into chapters</p>
</div>

## Features

- split m4b files into chapters
- set chapter metadata
  - title
  - track number
- convert the chapters to mp3

There's also a class that contains the metadata, in case you want to do something with it.

## Requirements

- ffmpeg
- python3

## Usage

```bash
python pym4b.py -i <inputfile>
```

### Options

- `-i` or `--input` - input file
- `-c` or `--convert` - convert the resulting chapters to mp3
- `-b` or `--bitrate` - bitrate for the mp3 conversion (default: keep original bitrate)
- `-d` or `--delete` - delete the original m4b file after conversion

### TODO

- [ ] clean up the code
- [ ] option to set output directory
- [ ] more metadata options if needed
- [ ] chapter data override in the event that the metadata is wrong
