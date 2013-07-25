#!/usr/local/bin/python
import json
import time
import os
import re
import sys
import urllib

import ivod_db
import util

db = ivod_db.DB()

g_user = ''
g_token = ''

def get_store_path(t, url):
    timecode = t.replace('-','/').replace(':','').replace(' ','-')
    dn = 'video/%s' % timecode[:10]
    if not os.path.exists(dn):
        os.makedirs(dn)

    url = urllib.unquote(url.encode('utf8'))
    urlpath = '/'.join(url.split('/')[3:])
    fn = urlpath.replace('/', '_')
    assert '..' not in fn
    path = os.path.join(str(dn), fn)
    return path

def gen_job2(o):

    for bw in ('w', 'n'):
        #if bw == 'w':
        #    continue
        url = o['video_url_'+bw].encode('utf8')
        if url == 'n/a':
            continue

        url = o['video_url_'+bw]
        if url == 'n/a':
            continue
        fn = get_store_path(o['time'], url)
        assert fn

        timecode = o['time'].replace('-','/').replace(':','').replace(' ','-')
        key = json.dumps((timecode[:10],url))
        state = db.get_job_state(key)

        if os.path.exists(fn):
            new_state = 'stored'
        else:
            new_state = 'no'

        if state is None:
            db.add_job_state(key, g_user, new_state)
        elif new_state == 'stored' and state != 'stored':
            db.change_job_state(key, g_user, new_state)

        # video info
        if os.path.exists(fn) and not db.get_video_info(key):
            info = util.collect_video_info(fn)
            db.add_video_info(key, g_user, json.dumps(info, sort_keys=True))



def gen_job():
    for o in json.load(file('data/clip.json')):
        with db.conn:
            gen_job2(o)
    for o in json.load(file('data/whole.json')):
        with db.conn:
            gen_job2(o)


def main():
    global g_user, g_token
    
    with file(self.token_file) as f:
        g_user = f.readline().strip()
        g_token = f.readline().strip()
        assert g_user and g_token
    
    with db.conn:
        if not db.get_user_token(g_user):
            db.add_user_token(g_user, g_user, g_token)
    gen_job()




if __name__ == '__main__':
    main()
