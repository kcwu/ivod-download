#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import re
import time
import cgi
import sqlite3
import random
import json
import collections
import threading

import cherrypy
from cherrypy.lib.static import serve_file
from cherrypy.lib import cptools, httputil

from ivod_db import DB

g_dblock = threading.RLock()

def error_page(status, message, traceback, version):
    return status + ' ' + message

class IVOD:
    @cherrypy.expose
    def index(self, *args):
        from mako.template import Template
        tmpl = Template(filename='template.mako', output_encoding='utf-8')
        data = {}
        cd = collections.defaultdict


        data['status'] = cd(lambda: cd(lambda: cd(lambda: cd(int))))

        db = DB()
        rows = db.get_status()
        db.close()
        for year, clip, bw, state, count in rows:
            print year, clip, bw, state, count
            state = {
                    'no': u'未下載',
                    '404': u'404 not found',
                    'downloading': u'下載中',
                    'downloaded': u'已下載(a)',
                    'stored': u'已下載(b)',
                    }.get(state, u'其他')
            data['status'][year][clip][bw][state] = count

        print data

        result = tmpl.render(**data)
        return result
        #return serve_file(os.path.join(current_dir, 'static', 'index.html'))

    @cherrypy.expose
    def register(self, name, contact):
        if not name or not contact:
            return json.dumps(dict(result='error', msg='empty name or contact'))
        pattern = r'^[a-zA-Z0-9_@.-]+$'
        if not re.match(pattern, name) or not re.match(pattern, contact):
            return json.dumps(dict(result='error', msg='valid pattern: %s' % pattern))

        db = DB()
        if db.get_user_token(name):
            return json.dumps(dict(result='error', msg='user exists'))
        assert name and contact
        token = str(random.getrandbits(32))
        db.add_user_token(name, contact, token)
        db.close()
        return json.dumps(dict(result='ok', token=token))

    @cherrypy.expose
    def metadata(self, vid):
        db = DB()
        cherrypy.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        data = db.get_metadata(vid)
        db.close()
        return data

    
    @cherrypy.expose
    def next(self, *args, **argd):
        bw = argd.get('bw')
        name = argd.get('name')
        token = argd.get('token')
        if not name or not token:
            return 'Empty name or token'
        db = DB()
        if db.get_user_token(name) != token:
            return json.dumps('invalid token')

        # bw, clip
        # 0, 0  200KB/s
        # 0, 1  500KB/s
        # 1, 0  70KB/s
        # 1, 1  70KB/s
        if bw == 'high':
            bw_cond = '1'
        elif bw == 'mid':
            # bw, clip != 0, 1
            bw_cond = '(bw = 1 OR clip = 0)'
        elif bw == 'low':
            # bw = 1
            bw_cond = '(bw = 1)'
        else:
            bw_cond = '1'

        with g_dblock:
            t0 = time.time()
            result = db.query('''
                    SELECT key, MIN(last_modified), state
                    FROM download_state 
                    WHERE (
                        (videodate < '2010-01-01' AND state = 'no')
                        OR (state = 'downloading' AND clip = 1 AND last_modified < date('now', '-1 hours'))
                        OR (state = 'downloading' AND clip = 0 AND last_modified < date('now', '-6 hours'))
                        OR (state = 'failed' AND last_modified < date('now', '-10 minutes'))
                        ) AND %s

                    -- ORDER BY last_modified 
                    -- LIMIT 1
                    ''' % bw_cond,
                    )
            print 't', time.time() - t0
            if not result:
                return 'done'

            row = result[0]
            key, last_modified, state = row


            #if last_modified < blah:
            #    return 'wait'
            with db.conn:
                db.change_job_state(key, name, 'downloading')
            db.close()
            return key

    @cherrypy.expose
    def change(self, *args, **argd):
        key = argd.get('key')
        state = argd.get('state')
        info = argd.get('info')
        name = argd.get('name')
        token = argd.get('token')
        db = DB()
        if db.get_user_token(name) != token:
            return 'invalid token'
        if state == 'downloaded' and not info:
            return 'invalid'

        assert state in ('404', 'downloaded', 'failed')
        with db.conn:
            db.change_job_state(key, name, state)
            if info:
                db.add_video_info(key, name, info)
        db.close()
        return 'ok'

    @cherrypy.expose
    def status(self):
        db = DB()
        rows = db.get_status()
        db.close()
        return json.dumps(rows)


current_dir = os.path.dirname(os.path.abspath(__file__))
if '--fastcgi' in sys.argv:
    app = cherrypy.tree.mount(IVOD())
    cherrypy.config.update({'engine.autoreload_on':False})
    cherrypy.config.update({
        'tools.sessions.on': True,
        'tools.sessions.timeout': 5,
        'log.screen': False,
        })
    cherrypy.config.update({'error_page.default':error_page})
    from flup.server.fcgi import WSGIServer
    WSGIServer(app).run()

else:
    cherrypy.config.update({'server.socket_host': '192.168.0.254'})
    cherrypy.quickstart(IVOD())
