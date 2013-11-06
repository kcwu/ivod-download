#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import os
import re
import urllib
import datetime
import json
import time

import requests

ivod_url = 'http://ivod.ly.gov.tw/'

committee = {
        6: {u'院會':17, 
            u'預算及決算': 7,
            u'司法':10,
            u'法制':11,
            u'外交僑務':2,
            u'衛生環境及社會福利':12,
            u'科技及資訊':3,
            u'經濟及能源':5,
            u'交通':9,
            u'內政':1,
            u'國防':4,
            u'教育及文化':8,
            u'財政':6,
            },
        7: {u'院會':27,
            u'內政':19,
            u'外交及國防':20,
            u'經濟':21,
            u'財政':22,
            u'教育及文化':23,
            u'交通':24,
            u'司法及法制':25,
            u'衛生環境及勞工':26,
            },
        8: {u'院會':27,
            u'內政':19,
            u'外交及國防':20,
            u'經濟':21,
            u'財政':22,
            u'教育及文化':23,
            u'交通':24,
            u'司法及法制':25,
            u'社會福利及衛生環境':26,
            u'程序':28,
            },
        }

def fix_mms(v):
    v = ''.join([c if ord(c) < 0x80 else '%%%02x'%ord(c) for c in v.encode('utf8')])
    return v

def guess_mms_from_url(bw, url):
    if not url:
        return 'n/a'

    m = re.search(ur'(?:CLIP|FILE)_NAME=(.+?)&', url)
    assert m
    path = m.group(1)
    path = urllib.unquote(path).decode('big5')
    assert path.startswith('tw/')

    mms = fix_mms('mms://mediavod01.ly.gov.tw/' + path[3:])
    if bw == 'n':
        # XXX when searching clip ('c'), the path is incorrect
        mms = mms.replace('wmv-clip/','wmv-clip-100k/').replace('wmv/','wmv-100k/')

    return mms

def extract_wmvid_from_url(url):
    m = re.search(r'WMVID=([^&]+)', url)
    assert m
    return m.group(1)

def fix_url(v):
    v = urllib.quote(v.encode('big5'), '&=?/')
    v = ivod_url + v
    return v

def extract_result(film, html):

    result = []
    if film == 'c':
        num = len(re.findall(ur'會議簡介', html))
        for m in re.finditer(ur'''
            <img\s*alt="委員影片縮圖"\s*src="(?P<thumb>[^"]+)".*?

            <td.align="left".valign="baseline".class="A.file_description">\s*
            <span.class="file_description">\s*第(?P<ad>\d+)屆\s*第(?P<session>\d+)會期\s*</span><br>\s*
            <span.class="file_description">會議別：(?P<committee>.+?)</span><br>.*?

            <tr>\s*
                <td.class="h12".valign="baseline">發言人：</td>\s*
              <td.valign="baseline"><span.class="file_description">\s*(?P<speaker>.+?)\s*</span></td>\s*
            </tr>.*?

            <span.class="file_description">\s*時間：(?P<time>.+?)\s*<br./>\s*長度：(?P<length>.+?)\s*</span>.*?

            會議簡介：<br>(?P<summary>[^<>]+?)\s*</td>.*?

            (?:<img\s*
                src="images/ch/icon_05.gif".alt="播放影片\(寬頻\)"\s*
                width="18".height="16">.<a\s*
                href="(?P<video_page_w>[^"]+)"\s*
                target="_self".title="播放影片\(寬頻\)">播放影片\(寬頻\)</a>
               |<span.class="h7">\(寬頻影片檔案格式轉換中...\)</span>)\s*
            (?:<img\s*
                src="images/ch/icon_05.gif"\s*
                alt="播放影片\(窄頻\)".width="18".height="16">.<a\s*
                href="(?P<video_page_n>[^"]+)"\s*
                target="_self".title="播放影片\(窄頻\)">播放影片\(窄頻\)</a>
               |<span.class="h7">\(窄頻影片檔案格式轉換中...\)</span>)
                ''', html, re.X|re.S):
            d = m.groupdict()
            result.append(d)
            for k, v in d.items():
                if k in ('video_page_w', 'video_page_n', 'thumb'):
                    if not v:
                        continue
                    v = fix_url(v)
                    d[k] = v
                print k, unicode(v).encode('utf8')
        print
    else:
        num = len(re.findall(ur'>主題<', html))
        for m in re.finditer(ur'''
            <tr.style="background-color:.\#FFFFCC;".align="left">\s*
                <td.width="10%".align="center".bgcolor="\#ebdbee".class="h14".nowrap>委員會</td>\s*
                <td.width="90%".align="center".bgcolor="\#ebdbee".class="h14".nowrap>主題</td>\s*
            </tr>\s*
            <tr.align="left">\s*
                <td.align="center".class="h3">(?P<committee>.+?)\s*</td>\s*
                <td><span.class="file_description">(?P<time>[^<]+)</span><br>\s*
                <span.class="h11">(?P<summary>.+?)</span></td>\s*
            </tr>\s*
            <tr.align="left">\s*
                <td.colspan=2><img.src="images/ch/icon_05.gif"\s*
                    alt="播放影片\(寬頻\)".width="18".height="16"><span\s*
                    class="A"><a\s*
                    href="(?P<video_page_w>[^"]+)"\s*
                    target="_self".title="播放影片\(寬頻\)">播放影片\(寬頻\)</a>\s*
                <img.src="images/ch/icon_05.gif"\s*
                    alt="播放影片\(窄頻\)".width="18".height="16"></span><span\s*
                    class="A"><a\s*
                    href="(?P<video_page_n>[^"]+)"\s*
                    target="_self".title="播放影片\(窄頻\)">播放影片\(窄頻\)</a></span>
        ''', html, re.X|re.S):
            d = m.groupdict()
            for k, v in d.items():
                if k in ('video_page_w', 'video_page_n'):
                    v = fix_url(v)
                    d[k] = v
                print k, unicode(v).encode('utf8')
            result.append(d)
        print

    assert len(result) == num

    return result

def query(keyword, commissionerName, film='c', select_type='class', condition=None):
    """
    film # c=片段, w=完整
    select_type # class=會期, time=時間
        for 'class'
        condition=(屆,會期,委員會)
        for 'time'
        condition=(yyyy,mm,dd,yyyy,mm,dd)
    """
    assert condition


    query = dict(
                keyWord=keyword,
                commissionerName=commissionerName,
                film=film, # c=片段, w=完整

                select_type=select_type, # class=會期, time=時間
                udlang='ch',
                )

    # 1. get cookie, and "as_fid"
    r = requests.get(ivod_url + 'new_vod_1t.jsp?udlang=ch')
    m = re.search(ur'<input type=hidden name="as_fid" value="([^"]+)" />', r.text)
    assert m
    query['as_fid'] = m.group(1)




    if select_type == 'class':
        query.update(dict(
                    select1=condition[0],
                    select2=condition[1],
                    select3=condition[2],
                    ))
    else:
        query.update(dict(
                period='3',
                startyear=condition[0],
                startmonth=condition[1],
                startday=condition[2],
                endyear=condition[3],
                endmonth=condition[4],
                endday=condition[5],
                ))

    # 2. real query
    query['pages'] = 1
    while True:
        time.sleep(1)
        r = requests.post(ivod_url + 'new_vod_1t.jsp',
                data=query,
                cookies=r.cookies,
                )

        result = extract_result(film, r.text)
        if len(result) == 0:
            break
        for i, x in enumerate(result):
            print query['pages'], i
            if 0:
                for vp in ('video_page_w', 'video_page_n'):
                    r = requests.get(x[vp])
                    m = re.search(ur'<param name="URL" value="([^"]+)"', r.text)
                    assert m
                    x[vp.replace('page', 'url')] = m.group(1)
            x['video_url_w'] = guess_mms_from_url('w', x['video_page_w'])
            x['video_url_n'] = guess_mms_from_url('n', x['video_page_n'])

            wmvid_w = wmvid_n = None
            if x['video_page_w']:
                wmvid_w = extract_wmvid_from_url(x['video_page_w'])
            if x['video_page_n']:
                wmvid_n = extract_wmvid_from_url(x['video_page_n'])
            if wmvid_w and wmvid_n:
                assert wmvid_w == wmvid_n
            if wmvid_w or wmvid_n:
                x['wmvid'] = wmvid_w or wmvid_n


            # normalize
            for k, v in sorted(x.items()):
                if k == 'length':
                    m = re.match(ur'^(\d+)分(\d+)秒$', v)
                    assert m
                    v = int(m.group(1))*60 + int(m.group(2))
                if k == 'time':
                    v = v.replace('&nbsp;', ' ')
                x[k] = v
                if k in ('video_page_w', 'video_page_n'):
                    del x[k]
                    continue

            yield x
            print

        query['pages'] += 1



    
def json_dumps(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False).encode('utf8')

# data bug:
# 第8屆第2,3會期都被 tag 成第1會期
# search clip ('c'), 窄頻的 link 是錯的

def query_by_date(date, film):
    day = date.toordinal()
    ndate = datetime.date.fromordinal(day+1)
    for d in query('', '',
            film=film,
            #select_type='class', condition=(7, 4, committee[7][u'院會']),
            #select_type='class', condition=(8, 3, committee[8][u'院會']),
            select_type='time', condition=(
                date.year,date.month,date.day,
                ndate.year,ndate.month,ndate.day),
            ):
        yield d

def date_range(d1, d2):
    for di in range(d1.toordinal(), d2.toordinal()):
        yield datetime.date.fromordinal(di)

def get_list_by_date(date, film):
    assert film in ('clip', 'whole')

    fn = 'data/%s/%s.txt' % (film, date)
    fn_tmp = fn + '.tmp'
    if os.path.exists(fn):
        d = time.strptime(os.path.basename(fn), '%Y-%m-%d.txt')
        if time.mktime(d) < time.time() - 86400*7:
            return

    print date, film
    with file(fn_tmp, 'w') as f:
        for d in query_by_date(date, film[0]):
            for k, v in sorted(d.items()):
                print k, unicode(v).encode('utf8')
            f.write(json_dumps(d) + '\n')
    os.rename(fn_tmp, fn)

def main():
    for date in date_range(
            datetime.date(2009,1,1),
            datetime.date.today() + datetime.timedelta(days=1)):
        get_list_by_date(date, 'clip')
        get_list_by_date(date, 'whole')

if __name__ == '__main__':
    main()
