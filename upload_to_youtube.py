#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import os
import json
import re
import sys
import subprocess
import time
import traceback

import process_metadata
import ivod_db
import util

db = ivod_db.DB()

account_name, account_passwd = open('.youtube_account').read().split()

STATE_UPLOADING = 'uploading'
STATE_UPLOADED = 'uploaded'
STATE_ERROR = 'error'
STATE_NO = 'no'

cached_upload_state = {}

def shrink_by_byte_len(s, n):
    assert type(s) is unicode
    assert n >= 0

    while len(s.encode('utf8')) > n:
        s = s[:-1]

    return s

def collect_metadata(firm, o):
    category = 'News'
    keywords = []
    keywords.append(u'立法院議事轉播')

    # brief
    brief = o['summary'].replace('\x0b', '\n').replace('\x15', '\n').split('\n')[0]
    m = re.match(ur'(.*?會議)', brief)
    if m:
        brief = m.group(1)
    brief = re.sub(ur'^立法院', '', brief)

    if firm == 'c':
        speaker = o['speaker'].split()[0]
        keywords.append(speaker)

        title = u'%s %s 發言片段, %s' % (o['time'][:10], speaker, brief)
    else:
        title = u'%s %s' % (o['time'][:10], brief)

    #title = title[:43]
    title = shrink_by_byte_len(title, 100)


    

    committee = None
    if o['committee']:
        if o['committee'] == 'WHL':
            committee = u'全院院會'
        else:
            committee = process_metadata.committees[o['committee']] + u'委員會'
    else:
        committee = u'全院院會'

    if committee:
        keywords.append(committee)

    if u'公聽會' in o['summary']:
        keywords.append(u'公聽會')

    description = u'''會議簡介: %s

時間: %s
原始影片: %s
***''' % (
        o['summary'].replace('\x0b', '\n').replace('\x15', '\n'),
        o['time'],
        o['video_url_w']
        )

    return dict(title=title,
            category=category,
            keywords=keywords,
            description=description)

def do_upload(url, cmd, state):

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    #p.wait()
    output = p.communicate()[0].strip()
    print 'output', repr(output)
    if 'http://www.youtube.com/watch' not in output:
        return dict(state=STATE_ERROR, sleep=60*10)

    return dict(state=STATE_UPLOADED, sleep=10, youtube_id=output)

def upload(firm, o):
    url = o['video_url_w']
    if url == 'n/a':
        return

    state = cached_upload_state.get(url)
    if not state:
        return

    if state == STATE_UPLOADED:
        return

    assert db.get_job_state(url) == 'stored'

    fn = util.get_store_path(o['time'], url)
    assert os.path.exists(fn)

    with db.conn:
        state = db.get_upload_state(url, for_update=True)
        assert state

        if state[0] == STATE_UPLOADED:
            return
        if state[0] == STATE_UPLOADING:
            # TODO check last_modified
            return
        if state[0] not in (STATE_ERROR, STATE_NO):
            # unkown state
            return

        db.change_upload_state(url, STATE_UPLOADING, '')
        cached_upload_state[url] = STATE_UPLOADING

    metadata = collect_metadata(firm, o)

    for k, v in metadata.items():
        if k == 'keywords':
            v = ','.join(v)
        print k, v


    cmd = [
            './youtube-upload',
            '-m', account_name,
            '-p', account_passwd,
            '-t', metadata['title'],
            '-c', metadata['category'],
            '-d', metadata['description'],
            '--keywords=' + ','.join(metadata['keywords']),
            fn.decode('utf8'),
            ]

    cmd = [x.encode('utf8') for x in cmd]

    result = None
    try:
        result = do_upload(url, cmd, state)
        assert db.get_upload_state(url)[0] != STATE_UPLOADED
    except Exception:
        traceback.print_exc()
    finally:
        if not result:
            result = dict(state=STATE_ERROR, sleep=60*30)
        with db.conn:
            db.change_upload_state(url, result['state'], result.get('youtube_id', ''))
            cached_upload_state[url] = result['state']
        print 'sleep', result['sleep']
        time.sleep(result['sleep'])
        print '-' * 30


    #sys.exit(0)




def main():
    cached_upload_state.update(db.get_all_upload_state())
    for o in json.load(file('data/clip.json')):
        upload('c', o)
    for o in json.load(file('data/whole.json')):
        upload('w', o)

if __name__ == '__main__':
    main()
