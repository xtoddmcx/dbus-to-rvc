#!/bin/bash

# fix owner and group
chown -R root:root /data/dbus-to-rvc

# make files executable
chmod +x /data/dbus-to-rvc/*.py
chmod +x /data/dbus-to-rvc/*.sh
chmod +x /data/dbus-to-rvc/service/run
chmod +x /data/dbus-to-rvc/service/log/run

# create symlink to service, if it does not exist
if [ ! -L "/service/dbus-to-rvc" ]; then
    ln -s /data/dbus-to-rvc/service /service/dbus-to-rvc
fi

# remove old rc.local entry
sed -i "/ln -s \/data\/dbus-to-rvc\/service \/service\/dbus-to-rvc/d" /data/rc.local

# add entry to rc.local, if it does not exist
grep -qxF "bash /data/dbus-to-rvc/reinstall-local.sh" /data/rc.local || echo "bash /data/dbus-to-rvc/reinstall-local.sh" >> /data/rc.local

echo ""
echo "Installation successful! Please modify the settings.py file in /data/dbus-to-rvc to your needs and then reboot the device."
echo ""
