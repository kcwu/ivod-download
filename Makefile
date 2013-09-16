all:

dump:
	pg_dump -Fc ivod -f ivod.pgdump
