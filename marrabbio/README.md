# Marrabbio on systemd

## Project root

This setup assumes app root at:

`/home/licia/marrabbio`

## Quick install

```bash
cd /home/licia/marrabbio
bash scripts/install.sh
```

## Manual install

```bash
sudo cp /home/licia/marrabbio/systemd/marrabbio.service /etc/systemd/system/marrabbio.service
sudo systemctl daemon-reload
sudo systemctl enable marrabbio.service
sudo systemctl start marrabbio.service
```

## Logs and status

```bash
sudo systemctl status marrabbio.service
journalctl -u marrabbio.service -f
```

## Port 80

The service includes:

`AmbientCapabilities=CAP_NET_BIND_SERVICE`

so the app can bind port 80 without root.

## Tuning

Edit:

`/home/licia/marrabbio/config.toml`

Then:

```bash
sudo systemctl restart marrabbio.service
```

## Windows web test mode (no GPIO)

Set in `config.toml`:

```toml
[runtime]
gpio_enabled = false
```

Then run:

```bash
python3 marrabbio.py
```

