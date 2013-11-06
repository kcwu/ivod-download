FFMPEG_LIBS= libavformat1 libavcodec1 libavutil1
CFLAGS = -Wall -g -O2

# ffmpeg1
#CFLAGS += `pkg-config --cflags $(FFMPEG_LIBS)`
#LDLIBS += `pkg-config --libs $(FFMPEG_LIBS)` -lm
# libav
#CFLAGS += -I/home/data/repos/git/libav
#LDLIBS += /home/data/repos/git/libav/libavformat/libavformat.a
#LDLIBS += /home/data/repos/git/libav/libavcodec/libavcodec.a
#LDLIBS += /home/data/repos/git/libav/libavutil/libavutil.a
#LDLIBS += -lz -lbz2 -pthread -lm
CFLAGS += -I/usr/local/include/ffmpeg2
LDLIBS += -L/usr/local/lib/ffmpeg2
LDLIBS += -lavformat2
LDLIBS += -lavcodec2
LDLIBS += -lavutil2
LDLIBS += -lz -lbz2 -pthread -lm


all:

gen_waveform: gen_waveform.c
	$(CC) $(CFLAGS) gen_waveform.c -o gen_waveform $(LDLIBS)
determine_time: determine_time.c
	$(CC) $(CFLAGS) determine_time.c -o determine_time $(LDLIBS)

dump:
	pg_dump -Fc ivod -f ivod.pgdump

daily:
	python get_metadata.py
	python process_metadata.py
	python result.py | pbzip2 -c > publish/ivod.json.bz2
