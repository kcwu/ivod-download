import json

import psycopg2

class DB:
    def __init__(self):
        self.conn = psycopg2.connect('dbname=ivod user=ivod')

    def close(self):
        self.conn.close()
        self.conn = None
    
    def query(self, sql, *bind):
        #print 'SQL:', sql, bind
        c = self.conn.cursor()
        c.execute(sql, bind)
        result = c.fetchall()
        c.close()
        return result

    def modify(self, sql, *bind):
        c = self.conn.cursor()
        c.execute(sql, bind)
        #self.conn.commit()
        c.close()

    def get_user_token(self, name):
        rows = self.query('SELECT token FROM users WHERE name = %s LIMIT 1', name)
        if not rows:
            return None
        return rows[0][0]

    def add_user_token(self, name, contact, token):
        with self.conn:
            self.modify('INSERT INTO users (name, contact, token) VALUES (%s,%s,%s)',
                name, contact, token)

    def get_metadata(self, vid):
        return self.query('SELECT data FROM metadata WHERE vid = %s', vid)

    def change_job_state(self, key, name, state):
        self.modify('''
        UPDATE download_state 
        SET state = %s, username = %s, last_modified = now()
        WHERE key = %s''',
                state, name, key)
        self.modify('INSERT INTO download_state_history (key,username, state) VALUES (%s,%s,%s)',
                key, name, state)

    def add_upload_state(self, key, state, youtube_id):
        self.modify('''
        INSERT INTO upload_state(key,state,youtube_id) VALUES(%s,%s,%s)''',
        key, state, youtube_id)

    def change_upload_state(self, key, state, youtube_id):
        self.modify('''
        UPDATE upload_state
        SET state = %s, youtube_id = %s, last_modified = now()
        WHERE key = %s''',
        state, youtube_id, key)

    def get_upload_state(self, key):
        rows = self.query('SELECT state,youtube_id,last_modified FROM upload_state WHERE key = %s LIMIT 1', key)
        if not rows:
            return None
        return rows[0]

    def add_job_state(self, key, name, state):
        bw = 1 if '-100k' in key else 0
        clip = 1 if '-clip' in key else 0
        timecode = json.loads(key)[0]
        timecode = timecode.replace('/', '-')
        self.modify('INSERT INTO download_state(key,username,state,bw,clip,videodate) VALUES(%s,%s,%s,%s,%s,%s)',
                key,name,'no', bw, clip, timecode)
        if state != 'no':
            self.change_job_state(key, name, state)

    def get_job_state(self, key):
        rows = self.query('SELECT state FROM download_state WHERE key = %s LIMIT 1', key)
        if not rows:
            return None
        return rows[0][0]

    def get_video_info(self, key):
        rows = self.query('SELECT info FROM video_info WHERE key = %s LIMIT 1', key)
        if not rows:
            return None
        return rows[0][0]

    def add_video_info(self, key, name, info):
        self.modify('INSERT INTO video_info (key,username, info) VALUES (%s,%s,%s)',
                key, name, info)

    def get_status(self):
        return self.query('''
                SELECT 
                    date_part('year', videodate)::int as year,
                    clip, 
                    bw, 
                    state,
                    count(*) 
                FROM download_state 
                GROUP BY year, clip, bw, state''')

