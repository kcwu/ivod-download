all:

dump:
	pg_dump -Fc ivod -f ivod.pgdump

daily:
	python get_metadata.py
	python result.py | pbzip2 -c > publish/ivod.json.bz2
