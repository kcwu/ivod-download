#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import subprocess
import os
import sys
import json
import time

import util

def video_to_waveform(fn, ofn):
    subprocess.check_call([
        './gen_waveform',
        fn,
        ofn
        ])


def iter_items():
    data = json.load(file('data/clip.json')) + json.load(file('data/whole.json'))
    data.sort(key=lambda x:x['time'])
    return data

def main():
    for o in reversed(iter_items()):
        url = o['video_url_w']
        if url == 'n/a':
            continue
        fn = util.get_store_path(o['time'], url)
        if 'wmvid' not in o:
            continue # ??
        if not os.path.exists(fn):
            continue

        ofn = 'waveform/%d.json' % int(o['wmvid'])
        if os.path.exists(ofn):
            continue

        print url
        ofn_tmp = ofn + '.tmp'
        t0 = time.time()
        wf = video_to_waveform(fn, ofn_tmp)
        if not os.path.exists(ofn_tmp): # hack
            continue
        assert os.path.exists(ofn_tmp)

        os.rename(ofn_tmp, ofn)
        print 'time', time.time() - t0

        #print json.dumps(wf)

if __name__ == '__main__':
    main()
