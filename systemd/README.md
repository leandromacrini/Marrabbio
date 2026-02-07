# Marrabbio systemd service

Install on Raspberry Pi OS:

```bash
sudo cp /home/licia/Marrabbio/systemd/marrabbio.service /etc/systemd/system/marrabbio.service
sudo systemctl daemon-reload
sudo systemctl enable marrabbio.service
sudo systemctl start marrabbio.service
```

Check status/logs:

```bash
sudo systemctl status marrabbio.service
journalctl -u marrabbio.service -f
```

If `rc.local` was starting the app, remove that line first, then:

```bash
sudo systemctl restart marrabbio.service
```

Stop/disable:

```bash
sudo systemctl stop marrabbio.service
sudo systemctl disable marrabbio.service
```
