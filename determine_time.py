#!/usr/local/bin/python
import subprocess
import os
import json
import time

import util

def iter_items():
    data = []
    #data += json.load(file('data/clip.json'))
    data += json.load(file('data/whole.json'))
    data.sort(key=lambda x:x['time'])
    return data

def determine_time(fn):
    output = subprocess.check_output([
        './determine_time',
        fn,
        ])
    ts = map(float, output.split())
    print ts
    if not ts:
        return ''
    ts.sort()
    mid = ts[len(ts)/2]

    tt = [mid]
    for i in range(len(ts)/2+1, len(ts)):
        if abs(ts[i]-tt[-1]) < 1.5:
            tt.append(ts[i])
    for i in range(len(ts)/2-1, -1, -1):
        if abs(ts[i]-tt[0]) < 0.5:
            tt.insert(0, ts[i])

    print tt[0], tt[-1], len(tt), tt[-1]-tt[0]
    print time.ctime(tt[-1]), fn
    return '%.2f %d %f\n' % (tt[-1], len(tt), tt[-1]-tt[0])

def main():
    for o in reversed(iter_items()):
        url = o['video_url_w']
        fn = util.get_store_path(o['time'], url)
        if 'wmvid' not in o:
            continue # ??
        if not os.path.exists(fn):
            continue

        ofn = 'start_time/%d.txt' % int(o['wmvid'])
        if os.path.exists(ofn):
            continue

        print fn
        result = determine_time(fn)

        with file(ofn, 'w') as f:
            f.write(result)
        print '-' * 30


if __name__ == '__main__':
    main()
