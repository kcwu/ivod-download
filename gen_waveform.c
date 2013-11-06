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
#include <assert.h>
#include <stdlib.h>
#include <libavutil/imgutils.h>
#include <libavutil/samplefmt.h>
#include <libavutil/timestamp.h>
#include <libavformat/avformat.h>

static AVFormatContext *fmt_ctx = NULL;
static AVCodecContext *audio_dec_ctx = NULL;
static AVStream *audio_stream = NULL;
static const char *src_filename = NULL;
static const char *audio_dst_filename = NULL;
static FILE *audio_dst_file = NULL;

static uint8_t **audio_dst_data = NULL;
static int       audio_dst_linesize;
static int audio_dst_bufsize;

static int audio_stream_idx = -1;
static AVFrame *frame = NULL;
static AVPacket pkt;
static int audio_frame_count = 0;

int64_t count_sample;
int waveform_length, waveform_capacity;
int64_t *waveform;

static int decode_packet(int *got_frame, int cached)
{
    int ret = 0;

    if (pkt.stream_index == audio_stream_idx) {
        /* decode audio frame */
        ret = avcodec_decode_audio4(audio_dec_ctx, frame, got_frame, &pkt);
        if (ret < 0) {
            fprintf(stderr, "Error decoding audio frame\n");
            return ret;
        }

        if (*got_frame) {
#if 0
            printf("audio_frame%s n:%d nb_samples:%d pts:%s\n",
                   cached ? "(cached)" : "",
                   audio_frame_count, frame->nb_samples,
                   av_ts2timestr(frame->pts, &audio_dec_ctx->time_base));
#endif
	    audio_frame_count++;

            ret = av_samples_alloc(audio_dst_data, &audio_dst_linesize, av_frame_get_channels(frame),
                                   frame->nb_samples, frame->format, 1);
            if (ret < 0) {
                fprintf(stderr, "Could not allocate audio buffer\n");
                return AVERROR(ENOMEM);
            }

            /* TODO: extend return code of the av_samples_* functions so that this call is not needed */
            audio_dst_bufsize =
                av_samples_get_buffer_size(NULL, av_frame_get_channels(frame),
                                           frame->nb_samples, frame->format, 1);

            /* copy audio data to destination buffer:
             * this is required since rawaudio expects non aligned data */
            av_samples_copy(audio_dst_data, frame->data, 0, 0,
                            frame->nb_samples, av_frame_get_channels(frame), frame->format);

#if 0
            /* write to rawaudio file */
            fwrite(audio_dst_data[0], 1, audio_dst_bufsize, audio_dst_file);
#endif
	    if ((count_sample + frame->nb_samples) / audio_dec_ctx->sample_rate >= waveform_capacity) {
		int cap = waveform_capacity;
		if (waveform_capacity == 0)
		    waveform_capacity = 1000;
		else
		    waveform_capacity *= 2;
		waveform = (int64_t*)realloc(waveform, sizeof(int64_t)*waveform_capacity);
		assert(waveform);
		memset(waveform + cap, 0, (waveform_capacity-cap)*sizeof(int64_t));
	    }
	    int num_channel = av_frame_get_channels(frame);
	    int c;
	    switch (audio_dec_ctx->sample_fmt) {
		case AV_SAMPLE_FMT_S32P: {
		    int32_t *sample = (int32_t*)audio_dst_data;
		    for (c = 0; c < num_channel; c++) {
			int i;
			for (i = 0; i < frame->nb_samples; i++) {
			    int idx = (count_sample + i) / audio_dec_ctx->sample_rate;
			    waveform[idx] += abs(*sample++);
			}
		    }
		}
		break;
		case AV_SAMPLE_FMT_FLTP: {
		    for (c = 0; c < num_channel; c++) {
			float *sample = (float*)frame->extended_data[c];
			int i;
			for (i = 0; i < frame->nb_samples; i++) {
			    float s = fabsf(*sample++);
			    if (s > 1.0) s = 1.0;
			    int idx = (count_sample + i) / audio_dec_ctx->sample_rate;
			    waveform[idx] += s * 32768;
			}
		    }

		}
		break;
		default: {
		    fprintf(stderr, "Not supported sample format: %d\n", audio_dec_ctx->sample_fmt);
		    exit(1);
		}
	    }
	    count_sample += frame->nb_samples;
	    waveform_length = (count_sample + audio_dec_ctx->sample_rate - 1) / audio_dec_ctx->sample_rate;


            av_freep(&audio_dst_data[0]);
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

    if (argc != 3) {
        fprintf(stderr, "usage: %s input_file audio_output_file\n"
                "API example program to show how to read frames from an input file.\n"
                "This program reads frames from a file, decodes them, and writes decoded\n"
                "audio frames to a rawaudio file named audio_output_file.\n"
                "\n", argv[0]);
        exit(1);
    }
    src_filename = argv[1];
    audio_dst_filename = argv[2];

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

    if (open_codec_context(&audio_stream_idx, fmt_ctx, AVMEDIA_TYPE_AUDIO) >= 0) {
        int nb_planes;

        audio_stream = fmt_ctx->streams[audio_stream_idx];
        audio_dec_ctx = audio_stream->codec;
        audio_dst_file = fopen(audio_dst_filename, "wb");
        if (!audio_dst_file) {
            fprintf(stderr, "Could not open destination file %s\n", audio_dst_filename);
            ret = 1;
            goto end;
        }

	printf("sample_fmt = %d\n", audio_dec_ctx->sample_fmt);
        nb_planes = av_sample_fmt_is_planar(audio_dec_ctx->sample_fmt) ?
            audio_dec_ctx->channels : 1;
        audio_dst_data = av_mallocz(sizeof(uint8_t *) * nb_planes);
        if (!audio_dst_data) {
            fprintf(stderr, "Could not allocate audio data buffers\n");
            ret = AVERROR(ENOMEM);
            goto end;
        }
    }

    /* dump input information to stderr */
    av_dump_format(fmt_ctx, 0, src_filename, 0);

    if (!audio_stream) {
        fprintf(stderr, "Could not find audio stream in the input, aborting\n");
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
    pkt.stream_index = audio_stream_idx;
    do {
        decode_packet(&got_frame, 1);
    } while (got_frame);

    printf("Demuxing succeeded.\n");

    printf("Generating waveform\n");
    int i;
    for (i = 0; i < waveform_length; i++)
	waveform[i] /= audio_dec_ctx->sample_rate;

#if 1
    // normalize
    int max = -1;
    for (i = 0; i < waveform_length; i++)
	if (waveform[i] > max)
	    max = waveform[i];

    for (i = 0; i < waveform_length; i++)
	waveform[i] = waveform[i] * 256 / (max+1);
#endif

    fprintf(audio_dst_file, "[");
    for (i = 0; i < waveform_length; i++)
	fprintf(audio_dst_file, "%ld%c", waveform[i], i == waveform_length-1?' ':',');
    fprintf(audio_dst_file, "]");

end:
    if (audio_dec_ctx)
        avcodec_close(audio_dec_ctx);
    avformat_close_input(&fmt_ctx);
    if (audio_dst_file)
        fclose(audio_dst_file);
    av_free(frame);
    av_free(audio_dst_data);

    return ret < 0;
}
