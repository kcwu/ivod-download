all:

server-init:
	rm -f ivod.db
	sqlite3 ivod.db < ivod.schema
