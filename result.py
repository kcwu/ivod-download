import json

import ivod_db

db = ivod_db.DB()

def main():
    youtube_urlmap = dict(db.query('SELECT key, youtube_id FROM upload_state'))

    result = []
    for o in json.load(file('data/clip.json')):
        o['firm'] = 'clip'
        result.append(o)
    for o in json.load(file('data/whole.json')):
        o['firm'] = 'whole'
        result.append(o)

    for o in result:
        url = o['video_url_w']
        if url in youtube_urlmap:
            youtube_url = youtube_urlmap[url]
            assert 'watch?v=' in youtube_url
            youtube_id = youtube_url.split('?v=')[1]
            o['youtube_id'] = youtube_id

    print json.dumps(result,
            sort_keys=True, indent=2, ensure_ascii=False).encode('utf8')

if __name__ == '__main__':
    main()
