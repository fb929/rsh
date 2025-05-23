build:
	install -d \
		build/usr/bin/ \
		build/etc/profile.d/ \
		build/opt/rsh/ \

	rsync -a \
		rshInventory.py \
		rshCompgen.py \
		sr \
		pExec \
		sExec \
		build/usr/bin/

	rsync -a rshCompletion.sh build/etc/profile.d/
	rsync -a --exclude "__pycache__/"  rsh build/opt/rsh/

clean:
	rm -rf build/
