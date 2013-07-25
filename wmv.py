import os
import sys

import videoparser
import videoparser.plugins.asf

ASFParser = videoparser.plugins.asf.Parser
def hack_extract_information(self, header, video):
    video.header = header
    return video
ASFParser.extract_information = hack_extract_information

VERIFIED_RESULT_INVALID = 'invalid header'
VERIFIED_RESULT_OK = 'ok'
VERIFIED_RESULT_BADSIZE = 'bad size'
VERIFIED_RESULT_ZERO_DURATION = 'zero duration'

def extract_metadata(fn):
    print fn
    video_parser = videoparser.VideoParser()
    video = video_parser.parse_file(fn)
    if not video:
        return None
    h = video.header
    d = {}

    #print h
    for o in h.objects:
        if isinstance(o, ASFParser.FileProperties):
            d['duration'] = o.play_duration.seconds
            d['date'] = str(o.create_date)
            d['size'] = o.size
        if isinstance(o, ASFParser.StreamProperties):
            td = o.type_data
            if o.type == 'ASF_Audio_Media':
                d['audio_sample_rate'] = td.sample_rate
                d['audio_codec'] = td.codec_ids.get(td.codec_id, td.codec_id)
                d['audio_bit_per_sample'] = td.bits_per_sample
            if o.type == 'ASF_Video_Media':
                d['resolution'] = td.width, td.height
                d['codec'] = td.format_data.compression_id

        if isinstance(o, ASFParser.HeaderExtension):
            for o in o.extension_data:
                if isinstance(o, ASFParser.ExtendedStreamProperties):
                    d.setdefault('data_bitrate', []).append(o.data_bitrate)


    return d


def verify_video(fn, d=None):
    if d is None:
        d = extract_metadata(fn)
        if not d:
            return VERIFIED_RESULT_INVALID
    expect_size = sum(d['data_bitrate'])/8 * d['duration']
    actual_size = os.path.getsize(fn)

    print 'expect_size', expect_size
    print 'actual_size', actual_size

    if expect_size == 0:
        if not (actual_size <= 10*1024):
            return VERIFIED_RESULT_ZERO_DURATION
    else:
        if not (0.8 <= 1.* actual_size / expect_size <= 1.2):
            return VERIFIED_RESULT_BADSIZE

    return VERIFIED_RESULT_OK

def main():
    if len(sys.argv) > 1:
        print verify_video(sys.argv[1])
    else:
        for root, dirs, files in os.walk('video'):
            if root < 'video/2013/03/15':
                continue
            dirs.sort()
            files.sort()
            for fn in files:
                if not fn.endswith('.wmv'):
                    continue
                path = os.path.join(root, fn)
                r = verify_video(path)
                if r not in (VERIFIED_RESULT_OK, VERIFIED_RESULT_ZERO_DURATION):
                    print r
                    break

if __name__ == '__main__':
    main()
