build:
	install -d \
		build/usr/bin/ \
		build/etc/profile.d/ \
		build/opt/rsh/ \

	rsync -a \
		rshAwsInventory.py \
		rshCompgen.py \
		sr \
		build/usr/bin/

	rsync -a rshCompletion.sh build/etc/profile.d/
	rsync -a --exclude "__pycache__/"  rsh build/opt/rsh/

clean:
	rm -rf build/
