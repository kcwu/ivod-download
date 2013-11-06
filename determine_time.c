/*
 * Copyright (c) 2012 Stefano Sabatini
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

/**
 * @file
 * libavformat demuxing API use example.
 *
 * Show how to use the libavformat and libavcodec API to demux and
 * decode audio and video data.
 * @example doc/examples/demuxing.c
 */

#include <stdint.h>
#include <stdlib.h>
#include <assert.h>
#include <ctype.h>
#include <time.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>

#include <libavutil/imgutils.h>
#include <libavutil/samplefmt.h>
#include <libavutil/timestamp.h>
#include <libavformat/avformat.h>

static AVFormatContext *fmt_ctx = NULL;
static AVCodecContext *video_dec_ctx = NULL;
static AVStream *video_stream = NULL;
static const char *src_filename = NULL;

static uint8_t *video_dst_data[4] = {NULL};
static int      video_dst_linesize[4];
static int video_dst_bufsize;

static int video_stream_idx = -1;
static AVFrame *frame = NULL;
static AVPacket pkt;
static int video_frame_count = 0;

int flag_limit = 90;
int count_detected = 0;

void write_pgm(int fd, uint8_t *image, int width, int height)
{
    int i;
    uint8_t *p = image;
    char header[1024];
    int skip = height * 7 / 8;
    sprintf(header, "P5\n%d %d\n%d\n", width, height - skip, 255);
    write(fd, header, strlen(header));
    for (i = 0; i < height; i++) {
	if (i >= skip)
	    write(fd, p, width);
	p += width;
    }
}

time_t parse_time(char *line)
{
    int i;
    int num_digit = 0;
    for (i = 0; line[i]; i++)
	if (isdigit(line[i]))
	    num_digit++;
	else
	    line[i] = ' ';
    if (num_digit > 8)
	fprintf(stderr, "%s\n", line);
    if (num_digit < 12)
	return (time_t)-1;
    struct tm t;
    int n;
    if (sscanf(line, "%d %d %d %d %d %d %n",
	    &t.tm_mon,
	    &t.tm_mday,
	    &t.tm_year,
	    &t.tm_hour,
	    &t.tm_min,
	    &t.tm_sec, &n) != 6 || n!=strlen(line))
	return (time_t)-1;

    if (!(1 <= t.tm_mon && t.tm_mon <= 12))
	return (time_t)-1;
    if (!(1 <= t.tm_mday && t.tm_mday <= 31))
	return (time_t)-1;
    if (!(95 <= t.tm_year))
	return (time_t)-1;
    if (!(0 <= t.tm_hour && t.tm_hour <= 24))
	return (time_t)-1;
    if (!(0 <= t.tm_min && t.tm_min <= 60))
	return (time_t)-1;
    if (!(0 <= t.tm_sec && t.tm_sec <= 60))
	return (time_t)-1;

    t.tm_year += 1911 - 1900;
    t.tm_mon -= 1;
    time_t tv = timegm(&t);
    tv -= 8*3600; // GMT+8
    if (tv > time(NULL))
	return (time_t)-1;
    //printf("tv %ld\n", tv);
    return tv;
}

time_t ocr_timestamp(int width, int height, uint8_t *image)
{
    int infd[2], outfd[2];
    pid_t pid;

    pipe(infd);
    pipe(outfd);
    pid = fork();
    if (pid < 0) {
	perror("fork");
	exit(1);
    } else if (pid == 0) {
	// child
	close(outfd[1]);
	close(infd[0]);
	dup2(infd[1], 1);
	dup2(outfd[0], 0);
	close(infd[1]);
	close(outfd[0]);
	execlp("gocr", "gocr", "-C", "0-9:-", "-", NULL);
	exit(0);
    }
    // parent after fork()
    close(outfd[0]);
    close(infd[1]);

    write_pgm(outfd[1], image, width, height);
    close(outfd[1]);
    waitpid(pid, NULL, WEXITED);

    char line[1024];
    FILE *fp = fdopen(infd[0], "r");
    line[0] = 0;
    while (fgets(line, sizeof(line), fp)) {
	//printf("line[%s]\n", line);
    }
    int len = strlen(line);
    if (line[len-1] == '\n')
	line[len-1] = '\0';
    close(infd[0]);

    time_t t = parse_time(line);
    if (t != (time_t)-1) {
	//printf("time[%s]\n", line);
	return t;
    }

    return (time_t)-1;
}

static int decode_packet(int *got_frame, int cached)
{
    int ret = 0;
    static int last_detected = 0;

    if (pkt.stream_index == video_stream_idx) {
        /* decode video frame */
        ret = avcodec_decode_video2(video_dec_ctx, frame, got_frame, &pkt);
        if (ret < 0) {
            fprintf(stderr, "Error decoding video frame\n");
            return ret;
        }

        if (*got_frame) {
#if 0
            printf("video_frame%s n:%d coded_n:%d pts:%s\n",
                   cached ? "(cached)" : "",
                   video_frame_count, frame->coded_picture_number,
                   av_ts2timestr(frame->pts, &video_dec_ctx->time_base));
#endif
	    video_frame_count++;
	    if (video_frame_count % 1000 == 0) {
		fprintf(stderr, "%d %d\n", video_frame_count, count_detected);
	    }

	    if (!last_detected) {
		if (video_frame_count % 20 != 0)
		    return ret;
	    }

	    assert(video_dec_ctx->pix_fmt == AV_PIX_FMT_YUV420P);
#if 0
            av_image_copy(video_dst_data, video_dst_linesize,
                          (const uint8_t **)(frame->data), frame->linesize,
                          video_dec_ctx->pix_fmt, video_dec_ctx->width, video_dec_ctx->height);

	    int i;
	    double t;
	    for (i = 0; i < 3; i++) {
		int h = video_dec_ctx->height;
		if (i > 0) h /= 2;
		t = ocr_timestamp(
			video_dst_linesize[i],
			h,
			video_dst_data[i]
			);
		if (t != (time_t)-1)
		    break;
	    }
#else
	    uint8_t *image = alloca(video_dec_ctx->width*video_dec_ctx->height);
	    av_image_copy_plane(image, video_dec_ctx->width,
		    frame->data[0], frame->linesize[0],
		    video_dec_ctx->width, video_dec_ctx->height);
	    double t = ocr_timestamp(
		    video_dec_ctx->width,
		    video_dec_ctx->height,
		    image
		    );
#endif


	    last_detected = 0;

	    if (t != (time_t)-1) {
		if (frame->pts == AV_NOPTS_VALUE) {
		    double elapsed = video_frame_count/av_q2d(video_stream->r_frame_rate);
		    //printf("elapsed %f\n", elapsed);

		    time_t tt = (time_t)t;
		    fprintf(stderr, "%s", ctime(&tt));
		    t -= elapsed;
		    tt = (time_t)t;
		    fprintf(stderr, "-> %s", ctime(&tt));
		    printf("%.2f\n", t);
		    count_detected++;
		    last_detected = 1;
		    if (count_detected >= flag_limit)
			exit(0);
		}
	    }
        }
    }

    return ret;
}

static int open_codec_context(int *stream_idx,
                              AVFormatContext *fmt_ctx, enum AVMediaType type)
{
    int ret;
    AVStream *st;
    AVCodecContext *dec_ctx = NULL;
    AVCodec *dec = NULL;

    ret = av_find_best_stream(fmt_ctx, type, -1, -1, NULL, 0);
    if (ret < 0) {
        fprintf(stderr, "Could not find %s stream in input file '%s'\n",
                av_get_media_type_string(type), src_filename);
        return ret;
    } else {
        *stream_idx = ret;
        st = fmt_ctx->streams[*stream_idx];

        /* find decoder for the stream */
        dec_ctx = st->codec;
        dec = avcodec_find_decoder(dec_ctx->codec_id);
        if (!dec) {
            fprintf(stderr, "Failed to find %s codec\n",
                    av_get_media_type_string(type));
            return ret;
        }

        if ((ret = avcodec_open2(dec_ctx, dec, NULL)) < 0) {
            fprintf(stderr, "Failed to open %s codec\n",
                    av_get_media_type_string(type));
            return ret;
        }
    }

    return 0;
}

int main (int argc, char **argv)
{
    int ret = 0, got_frame;

    if (argc != 2) {
        fprintf(stderr, "usage: %s input_file\n"
                "API example program to show how to read frames from an input file.\n"
                "This program reads frames from a file, decodes them, and writes decoded\n"
                "video frames to a rawvideo file named video_output_file, and decoded\n"
                "audio frames to a rawaudio file named audio_output_file.\n"
                "\n", argv[0]);
        exit(1);
    }
    src_filename = argv[1];

    /* register all formats and codecs */
    av_register_all();

    /* open input file, and allocate format context */
    if (avformat_open_input(&fmt_ctx, src_filename, NULL, NULL) < 0) {
        fprintf(stderr, "Could not open source file %s\n", src_filename);
        exit(1);
    }

    /* retrieve stream information */
    if (avformat_find_stream_info(fmt_ctx, NULL) < 0) {
        fprintf(stderr, "Could not find stream information\n");
        exit(1);
    }

    if (open_codec_context(&video_stream_idx, fmt_ctx, AVMEDIA_TYPE_VIDEO) >= 0) {
        video_stream = fmt_ctx->streams[video_stream_idx];
        video_dec_ctx = video_stream->codec;

        /* allocate image where the decoded image will be put */
        ret = av_image_alloc(video_dst_data, video_dst_linesize,
                             video_dec_ctx->width, video_dec_ctx->height,
                             video_dec_ctx->pix_fmt, 1);
	if (video_dec_ctx->pix_fmt != AV_PIX_FMT_YUV420P) {
	    fprintf(stderr, "Not yet support pix_fmt %d\n",
		    video_dec_ctx->pix_fmt);
	    goto end;
	}
        if (ret < 0) {
            fprintf(stderr, "Could not allocate raw video buffer\n");
            goto end;
        }
        video_dst_bufsize = ret;
    }

    /* dump input information to stderr */
    //av_dump_format(fmt_ctx, 0, src_filename, 0);

    if (!video_stream) {
        fprintf(stderr, "Could not find audio or video stream in the input, aborting\n");
        ret = 1;
        goto end;
    }

    frame = avcodec_alloc_frame();
    if (!frame) {
        fprintf(stderr, "Could not allocate frame\n");
        ret = AVERROR(ENOMEM);
        goto end;
    }

    /* initialize packet, set data to NULL, let the demuxer fill it */
    av_init_packet(&pkt);
    pkt.data = NULL;
    pkt.size = 0;

    /* read frames from the file */
    while (av_read_frame(fmt_ctx, &pkt) >= 0) {
        decode_packet(&got_frame, 0);
        av_free_packet(&pkt);
    }

    /* flush cached frames */
    pkt.data = NULL;
    pkt.size = 0;
    pkt.stream_index = video_stream_idx;
    do {
        decode_packet(&got_frame, 1);
    } while (got_frame);

    fprintf(stderr, "processed %d frames\n", video_frame_count);
    fprintf(stderr, "Demuxing succeeded.\n");

end:
    if (video_dec_ctx)
        avcodec_close(video_dec_ctx);
    avformat_close_input(&fmt_ctx);
    av_free(frame);
    av_free(video_dst_data[0]);

    return ret < 0;
}
