import json
import os

import ivod_db

db = ivod_db.DB()

def main():
    youtube_urlmap = dict(db.query("SELECT key, youtube_id FROM upload_state WHERE state = 'uploaded'"))
    vinfo_map = dict(db.query("SELECT key, info FROM video_info"))

    result = []
    for o in json.load(file('data/clip.json')):
        o['firm'] = 'clip'
        result.append(o)
    for o in json.load(file('data/whole.json')):
        o['firm'] = 'whole'
        result.append(o)

    # build start_time[] cache
    start_time = {}
    for fn in os.listdir('start_time'):
        path = os.path.join('start_time', fn)
        if not os.path.exists(path):
            continue
        data = file(path).read()
        if not data:
            continue
        st, ps, diff = data.split()
        st, diff = map(float, [st, diff])
        wmvid = os.path.splitext(fn)[0]
        start_time[wmvid] = st

    # duration
    for o in result:
        if 'length' in o:
            continue
        url = o['video_url_w']
        vinfo = vinfo_map.get(url)
        if vinfo and vinfo != 'None':
            duration = int(json.loads(vinfo_map[url])['duration'])
            o['length'] = duration

    # process: add some fields
    for o in result:
        # youtube_id
        url = o['video_url_w']
        if url in youtube_urlmap:
            youtube_url = youtube_urlmap[url]
            assert 'watch?v=' in youtube_url
            youtube_id = youtube_url.split('?v=')[1]
            o['youtube_id'] = youtube_id

        # first_frame_timestamp
        if 'wmvid' in o and o['wmvid'] in start_time:
            o['first_frame_timestamp'] = start_time[o['wmvid']]

    result.sort(key=lambda o:o['time'])

    print json.dumps(result,
            sort_keys=True, indent=2, ensure_ascii=False).encode('utf8')

if __name__ == '__main__':
    main()
