#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import os
import re
import json
import urllib

# committees name in
# https://github.com/g0v/twlyparser/blob/master/src/util.ls
committees = dict(x.split() for x in u'''
IAD 內政
FND 外交及國防
ECO 經濟
FIN 財政
EDU 教育及文化
TRA 交通
JUD 司法及法制
SWE 社會福利及衛生環境
WHL 全院
PRO 程序
# obsolete
IAP 內政及民族
IAF 內政及邊政
FRO 邊政
DEF 國防
FOR 外交及僑務
FOP 外交及僑政
OVP 僑政
DIP 外交
JUR 司法
LAW 法制
SCI 科技及資訊
ECE 經濟及能源
ESW 衛生環境及社會福利
ELB 衛生環境及勞工
BGT 預算及決算
BUD 預算
EDN 教育
'''.strip().splitlines())

committees_lookup = dict((v,k) for k,v in committees.items())

def parse_meeting(s, o):
    m = re.search(ur'第(?P<ad>\d+)屆第(?P<session>\d+)會期(.+?)委員會\s*第(?P<sitting>\d+)\s*次', s)
    if m:
        o.update(m.groupdict())
        return

    m = re.search(ur'第(?P<ad>\d+)屆第(?P<session>\d+)會期第(?P<sitting>\d+)次會議', s)
    if m:
        o.update(m.groupdict())
        return

    m = re.search(ur'第(?P<ad>\d+)屆第(?P<session>\d+)會期第(?P<extra>\d+)次臨時會第(?P<sitting>\d+)次會議', s)
    if m:
        o.update(m.groupdict())
        return

    m = re.search(ur'第(?P<ad>\d+)屆第(?P<session>\d+)會期', s)
    if m:
        o.update(m.groupdict())
        return

    #print s.encode('utf8')

def parse_one(film, line):
    o = json.loads(line)
    for k, v in o.items():
        if k == 'length':
            m = re.match(ur'^(\d+)分(\d+)秒$', unicode(v))
            if m:
                v = int(m.group(1))*60 + int(m.group(2))
        if k == 'time':
            v = v.replace('&nbsp;', ' ')
        if k == 'summary':
            parse_meeting(v, o)
        if k == 'committee':
            if v == u'院會':
                o[k] = None
            else:
                o[k] = committees_lookup[v]
    if film == 'c':
        mms = None
        # ex mms://mediavod01.ly.gov.tw/wmv-clip/張曉風/院會/張曉風-院會-2013-3-15-9-24-院內.wmv
        if o['video_url_w'] != 'n/a':
            mms = urllib.unquote(str(o['video_url_w'])).decode('utf8')
        elif o['video_url_n'] != 'n/a':
            mms = urllib.unquote(str(o['video_url_n'])).decode('utf8')
        if mms:
            v = mms.split('/')[5]
            v = v.replace(u'委員會', '')
            if v == u'院會':
                o['committee'] = None
            else:
                o['committee'] = committees_lookup[v]
    for k, v in o.items():
        if k in ('ad','session','extra','sitting'):
            o[k] = int(v)
    return o

def json_dumps(o):
    s = json.dumps(o, sort_keys=True, ensure_ascii=False, indent=1)

    s = re.sub(r'\n( +)',
            lambda m: '\n'+'\t'*len(m.group(1)),
            s)
    s = s.replace(' \n', '\n')
    return s

def parse_files(film):
    result = []
    if film == 'c':
        base = 'data/clip'
    elif film == 'w':
        base = 'data/whole'
    else:
        assert 0

    for root, dirs, files in os.walk(base):
        dirs.sort()
        files.sort()
        for fn in files:
            path = os.path.join(root, fn)
            for line in file(path):
                o = parse_one(film, line)
                result.append(o)
    return json_dumps(result).encode('utf8')

def main():
    with file('data/clip.json', 'w') as f:
        f.write(parse_files('c'))
    with file('data/whole.json', 'w') as f:
        f.write(parse_files('w'))

if __name__ == '__main__':
    main()
