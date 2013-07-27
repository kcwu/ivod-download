import sqlite3

class DB:
    def __init__(self):
        self.conn = sqlite3.connect('ivod.db')
        c = self.conn.cursor()
        c.execute('PRAGMA journal_mode=WAL')
        c.close()

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
        rows = self.query('SELECT token FROM users WHERE name = ? LIMIT 1', name)
        if not rows:
            return None
        return rows[0][0]

    def add_user_token(self, name, contact, token):
        with self.conn:
            self.modify('INSERT INTO users (name, contact, token) VALUES (?,?,?)',
                name, contact, token)

    def get_metadata(self, vid):
        return self.query('SELECT data FROM metadata WHERE vid = ?', vid)

    def change_job_state(self, key, name, state):
        self.modify('''
        UPDATE download_state 
        SET state = ?, username = ?, last_modified = (strftime('%Y-%m-%d %H:%M:%f', 'now'))
        WHERE key = ?''',
                state, name, key)
        self.modify('INSERT INTO download_state_history (key,username, state) VALUES (?,?,?)',
                key, name, state)

    def add_job_state(self, key, name, state):
        bw = 1 if '-100k' in key else 0
        clip = 1 if '-clip' in key else 0
        timecode = json.loads(key)[0]
        timecode = timecode.replace('/', '-')
        self.modify('INSERT INTO download_state(key,username,state,bw,clip,videodate) VALUES(?,?,?,?,?,?)',
                key,name,'no', bw, clip, timecode)
        if state != 'no':
            self.change_job_state(key, name, state)

    def get_job_state(self, key):
        rows = self.query('SELECT state FROM download_state WHERE key = ? LIMIT 1', key)
        if not rows:
            return None
        return rows[0][0]

    def get_video_info(self, key):
        rows = self.query('SELECT info FROM video_info WHERE key = ? LIMIT 1', key)
        if not rows:
            return None
        return rows[0][0]

    def add_video_info(self, key, name, info):
        self.modify('INSERT INTO video_info (key,username, info) VALUES (?,?,?)',
                key, name, info)


    def get_status(self):
        return self.query('''
                SELECT 
                    substr(videodate,1,4) as year, 
                    clip, 
                    bw, 
                    state,
                    count(*) 
                FROM download_state 
                GROUP BY year, clip, bw, state''')

