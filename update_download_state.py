#!/usr/local/bin/python
import json
import time
import os
import re
import sys

import ivod_db
import util

db = ivod_db.DB()

g_user = ''
g_token = ''
token_file = 'token.txt'

cached_download_state = {}
cached_video_info = {}

def gen_job2(o):

    for bw in ('w', 'n'):
        #if bw == 'w':
        #    continue

        url = o['video_url_'+bw]
        if url == 'n/a':
            continue

        fn = util.get_store_path(o['time'], url)
        assert fn

        state = cached_download_state.get(url)

        if os.path.exists(fn):
            new_state = 'stored'
        else:
            new_state = 'no'

        if os.path.exists(fn):
            # video info
            info0 = cached_video_info.get(url)
            if info0 == 'None':
                info0 = None
            assert info0 != 'None'
            if state != new_state:
                print repr(info0)

            info = None
            if not info0 or state != 'stored':
                info = util.collect_video_info(fn)
                assert info
                info = json.dumps(info, sort_keys=True)

            if info0:
                if state != 'stored':
                    assert info
                    info0 = json.dumps(json.loads(info0), sort_keys=True)
                    print 'info0', repr(info0)
                    print 'info1', repr(info)
                    assert info == info0, url
            else:
                assert info
                with db.conn:
                    cached_video_info[url] = info
                    db.add_video_info(url, g_user, info)

        with db.conn:
            if state is None:
                bw = 1 if '-100k' in url else 0
                clip = 1 if '-clip' in url else 0
                videodate = o['time'][:10]
                db.add_job_state(url, g_user, new_state, bw,clip,videodate)
                cached_download_state[url] = new_state
            elif new_state == 'stored' and state != 'stored':
                db.change_job_state(url, g_user, new_state)
                cached_download_state[url] = new_state




def gen_job():
    for o in json.load(file('data/clip.json')):
        gen_job2(o)
    for o in json.load(file('data/whole.json')):
        gen_job2(o)


def main():
    global g_user, g_token
    
    with file(token_file) as f:
        g_user = f.readline().strip()
        g_token = f.readline().strip()
        assert g_user and g_token

    cached_download_state.update(db.get_all_download_state())
    print len(cached_download_state)
    cached_video_info.update(db.get_all_video_info())
    print len(cached_video_info)

    with db.conn:
        if not db.get_user_token(g_user):
            db.add_user_token(g_user, g_user, g_token)

    gen_job()

    with db.conn:
        db.modify('''
            INSERT INTO upload_state(key, state)
                SELECT key, 'no'
                FROM download_state
                WHERE state='stored' AND bw=0 AND NOT EXISTS (
                    SELECT key
                        FROM upload_state
                        WHERE download_state.key = upload_state.key
                );
        ''')
    



if __name__ == '__main__':
    main()
