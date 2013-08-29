import os
import re
import sys
import hashlib
import urllib
import json
import time

import wmv

def fix_mms(v):
    v = ''.join([c if ord(c) < 0x80 else '%%%02x'%ord(c) for c in v.encode('utf8')])
    return v

def make_download_key(o, url):
    timecode = o['time'].replace('-','/').replace(':','').replace(' ','-')
    key = json.dumps((timecode[:10],url))
    return key

def get_store_path(t, url):
    timecode = t.replace('-',os.sep).replace(':','').replace(' ','-')
    dn = os.path.join('video', timecode[:10])
    if not os.path.exists(dn):
        os.makedirs(dn)

    url = urllib.unquote(url.encode('utf8'))
    urlpath = '/'.join(url.split('/')[3:])
    fn = urlpath.replace('/', '_')
    assert '..' not in fn
    path = os.path.join(str(dn), fn)
    return path

def extract_mms_link_from_vodeo_page(html):
    m = re.search(ur'(mms://[^"]*)', html)
    if m:
        mms = m.group(1)
        mms = fix_mms(mms)
        return mms
    return None

def calc_checksum(fn):
    # sha512 is faster than sha256
    alg = 'sha512'
    h = hashlib.new(alg)
    with file(fn, 'rb') as f:
        while True:
            # don't make disks too busy
            b = f.read(2**16)
            time.sleep(0.002)
            if not b:
                break
            h.update(b)
    hd = h.hexdigest()
    return alg + ':' + hd

def collect_video_info(fn):
    d = wmv.extract_metadata(fn)
    if not d:
        d = {}
    assert 'checksum' not in d
    assert 'filesize' not in d
    d['checksum'] = calc_checksum(fn)
    d['filesize'] = os.path.getsize(fn)
    print d
    return d

def main():
    import requests
    url = sys.argv[1]
    r = requests.get(url)
    mms = extract_mms_link_from_vodeo_page(r.text)
    print mms

    pass

if __name__ == '__main__':
    main()
