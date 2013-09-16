#!/usr/local/bin/python
# TODO make sure "done", "wait" works
import json
import subprocess
import time
import sys
import os
import urllib
import urllib2
import traceback
import hashlib
import datetime
import random
from optparse import OptionParser

import util

parser = OptionParser()
parser.add_option('-v', '--verbose', action='store_true')
parser.add_option('--msdl_bin', type=str)

msdl_bin = './msdl'

g_alt_server = False
jm = None

program_start_time = time.time()

class JobManager:
    def __init__(self):
        self.host = 'http://ivod.kcwu.csie.org/'
        self.name = ''
        self.token = ''
        self.token_file = 'token.txt'

    def load_token(self):
        if not os.path.exists(self.token_file):
            return False
        with file(self.token_file) as f:
            self.name = f.readline().strip()
            self.token = f.readline().strip()
            assert self.name and self.token
        return True

    def _request(self, path, **argd):
        for i in range(5):
            if self.name and self.token:
                d = dict(name=self.name, token=self.token)
            else:
                d = {}
            d.update(argd)
            data = urllib.urlencode(d)
            try:
                url = self.host + path
                r = urllib2.urlopen(url, data)
            except Exception:
                traceback.print_exc()
                print 'url:', url
                print 'data:', data
                print 'sleep...'
                time.sleep(60*10)
                print 'retry'
                continue

            result = r.read()
            #print result
            return result

    def get(self, bw=None):
        return self._request('next', bw=bw)

    def change_state(self, job, state, info):
        #print 'change_state', job, state
        if info:
            self._request('change', key=job, state=state, info=info)
        else:
            self._request('change', key=job, state=state)

    def register(self, name, contact):
        r = json.loads(self._request('register', name=name, contact=contact))
        if r['result'] == 'error':
            print 'error:', r['msg']
            sys.exit(1)
        elif r['result'] == 'ok':
            with file(self.token_file, 'w') as f:
                f.write('%s\n%s\n' % (name, r['token']))


def my_unlink(fn):
    try:
        os.unlink(fn)
    except OSError:
        pass

def os_filename(fn):
    if sys.platform == 'win32':
        return fn.decode('utf8')
    return fn

def is_success(logdata, tmp_a, tmp_b, tmp_c):
    if not os.path.exists(tmp_a):
        return False
    if not logdata:
        return False
    if os.path.getsize(tmp_a) <= 0:
        return False

    if os.path.exists(tmp_b):
        if os.path.exists(tmp_c) and os.path.getsize(tmp_a) == os.path.getsize(tmp_c) == 114845 and os.path.getsize(tmp_b) > 0:
            print 'found copyright file'
            # copyright file
            os.rename(tmp_b, tmp_a)
        else:
            print 'unknown extra file ???????????????????'
            #assert 0
            return False

    if 'fail' in logdata:
        return False
    return 'finished' in logdata and 'FINISHED' in logdata



def fetch(job):
    global g_alt_server

    t, url = json.loads(job)

    # prepare
    if g_alt_server:
        url = url.replace('mediavod01', 'mediavod02')

    fn = util.get_store_path(t, url)
    print url
    if options.verbose:
        print fn

    assert not os.path.exists(fn)


    # start fetch

    pid = os.getpid()

    tmp_a = os.path.join('tmp', '%d.a.wmv' % pid)
    tmp_b = os.path.join('tmp', '%d.b.wmv' % pid)
    tmp_c = os.path.join('tmp', '%d.c.wmv' % pid)
    tmp_log = os.path.join('tmp', '%d.log' % pid)
    my_unlink(tmp_a)
    my_unlink(tmp_b)
    my_unlink(tmp_c)
    my_unlink(tmp_log)

    cmd = '"%s" -s 5 -o %s -o %s -o %s "%s" 2>&1 | tee %s' % (
            msdl_bin,
            tmp_a, tmp_b, tmp_c, url, tmp_log)
    p = subprocess.Popen(cmd, shell=True)
    p.wait()

    logdata = ''
    if os.path.exists(tmp_log):
        logdata = file(tmp_log).read()
    if is_success(logdata, tmp_a, tmp_b, tmp_c):
        os.rename(tmp_log, os_filename(fn + '.log'))
        os.rename(tmp_a, os_filename(fn))

        info = util.collect_video_info(os_filename(fn))
        assert info
        return dict(state='downloaded', sleep=10, info=json.dumps(info, sort_keys=True))

    g_alt_server = not g_alt_server
    if '404 (Not Found)' in logdata:
        return dict(state='404', sleep=3)
    else:
        return dict(state='failed', sleep=60)

def worker(bw):
    while True:
        print '-'*30

        job = jm.get(bw)
        if options.verbose:
            print 'job', job
        if not job:
            break
        if job == 'done':
            print 'done'
            break
        if job == 'wait':
            print 'wait'
            time.sleep(60 * 10)
            continue

        result = None
        try:
            result = fetch(job)
        finally:
            if not result:
                result = dict(state='failed', sleep=60*10)
            jm.change_state(job, result['state'], result.get('info'))

        if os.path.exists('stop-download') and os.path.getmtime('stop-download') > program_start_time:
            print 'stop-download'
            break

        if result['sleep']:
            print 'sleep', result['sleep'], 'seconds'
            time.sleep(result['sleep'])

def check_dependency():
    if not os.path.exists('tmp'):
        os.mkdir('tmp')

    assert 'sha512' in hashlib.algorithms
    assert hashlib.sha512('hello').hexdigest() == '9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca72323c3d99ba5c11d7c7acc6e14b8c5da0c4663475c2e5c3adef46f73bcdec043'

    global msdl_bin
    if options.msdl_bin:
        msdl_bin = options.msdl_bin
    else:
        if sys.platform == 'win32':
            msdl_bin = r'msdl_win32\msdl.exe'

    p = subprocess.Popen([msdl_bin], stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    t = stderr

    assert 'no target' in t

def usage():
    print 'Usage: %s <cmd>' % sys.argv[0]
    print '''
Commands are:
    register <name> <contact>
    run {high|low}
        high <= 500KB/s
        mid <= 230KB/s
        low <= 70KB/s
'''

def main():
    global jm
    global options
    global args

    options, args = parser.parse_args()

    check_dependency()

    if len(args) == 0:
        usage()
        return

    cmd = args.pop(0)
    jm = JobManager()
    if cmd == 'register':
        name = raw_input('Please input your name: ')
        contact = raw_input('Please input your contact info (email or irc nick): ')
        jm.register(name, contact)
        return

    if not jm.load_token():
        print 'Please register first'
        usage()
        return

    if cmd == 'run':
        if args:
            bw = args.pop(0)
            assert bw in ('low', 'high', 'mid')
        else:
            bw = 'high'
        worker(bw)

if __name__ == '__main__':
    main()
