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

def gen_job2(o):

    for bw in ('w', 'n'):
        #if bw == 'w':
        #    continue

        url = o['video_url_'+bw]
        if url == 'n/a':
            continue

        fn = util.get_store_path(o['time'], url)
        assert fn

        key = util.make_download_key(o, url)
        state = db.get_job_state(key)

        if os.path.exists(fn):
            new_state = 'stored'
        else:
            new_state = 'no'

        if os.path.exists(fn):
            # video info
            info0 = db.get_video_info(key)
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
                    db.add_video_info(key, g_user, info)

        with db.conn:
            if state is None:
                db.add_job_state(key, g_user, new_state)
            elif new_state == 'stored' and state != 'stored':
                db.change_job_state(key, g_user, new_state)




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
    
    with db.conn:
        if not db.get_user_token(g_user):
            db.add_user_token(g_user, g_user, g_token)
    gen_job()




if __name__ == '__main__':
    main()
