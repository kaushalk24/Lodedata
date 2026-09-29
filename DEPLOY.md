# Running the Design Assistant on a Linux server

One server runs the app; everyone opens it in their web browser
(Chrome or Edge recommended) at `http://<server>:8000`. Nothing is installed
on the users' PCs.

## What you need

* A Linux server, x86_64 (64-bit Intel/AMD).
* Python 3.10, 3.11, 3.12 or 3.13, with its `venv` module
  (Debian/Ubuntu: `sudo apt install python3 python3-venv`;
  RHEL/Rocky/Alma: `sudo dnf install python3`).
* No internet: the zip carries every package in `wheels/`. (On an ARM
  server `install.sh` fetches them from the internet instead.)

## Install

```sh
sudo unzip lodedata-server.zip -d /opt          # makes /opt/lodedata
sudo chown -R "$USER": /opt/lodedata
cd /opt/lodedata
./install.sh                                    # or: PYTHON=python3.12 ./install.sh
```

`install.sh` makes a Python environment in `.venv/` and installs the
packages into it. It touches nothing else on the server.

## Start it

```sh
./start-server.sh                  # http://<server>:8000
PORT=8600 ./start-server.sh        # another port
```

Open the port in the server's firewall if it has one
(`sudo ufw allow 8000/tcp`, or `sudo firewall-cmd --add-port=8000/tcp --permanent && sudo firewall-cmd --reload`).

### Keep it running (start at boot, restart on failure)

```sh
sudo useradd --system --home /opt/lodedata lodedata      # an account for it
sudo chown -R lodedata: /opt/lodedata
sudo cp deploy/lodedata.service /etc/systemd/system/     # edit paths/port inside first if needed
sudo systemctl daemon-reload
sudo systemctl enable --now lodedata
journalctl -u lodedata -f                                # its log
```

## Several people at once

Yes — several people can use it at the same time, each in their own
browser. (It is one Python process: a team of designers is fine; it is not
built for hundreds at once.)

* **One list of networks.** The networks people open are kept on the server
  in `data/designs.db`, and everyone sees the same list. There are no
  logins or per-user folders.
* **Working on the same network.** Changes are applied one at a time, so
  two people changing one network at the same moment both keep their
  changes. Each sees the other's changes when their screen next refreshes
  (after their own next change, or when they reopen the network). The
  simplest practice is one person per network at a time.
* **Opening and saving .ntw files** happens on each person's own PC: Open
  reads a file from their PC, Save writes it back there. Chrome and Edge
  write straight into the file only on `https://` addresses (or on the
  server itself); on a plain `http://` address the saved file is downloaded
  instead — to the Downloads folder — and they keep it from there.
* **One server process.** Run it with `start-server.sh` as given; do not
  add uvicorn's `--workers`, which would split the networks' one-at-a-time
  handling across processes.
* **No password.** Anyone who can reach the port can open, change and
  delete networks. Keep the port inside the company network (or VPN), or
  put it behind the company's reverse proxy with a login and HTTPS, for
  example nginx:

  ```nginx
  server {
      listen 443 ssl;
      server_name lodedata.example.local;
      ssl_certificate     /etc/ssl/certs/lodedata.crt;
      ssl_certificate_key /etc/ssl/private/lodedata.key;
      auth_basic "Design Assistant";
      auth_basic_user_file /etc/nginx/lodedata.htpasswd;   # htpasswd -c ... username
      client_max_body_size 50m;                            # .ntw and spec uploads
      location / { proxy_pass http://127.0.0.1:8000; proxy_set_header Host $host; }
  }
  ```
  and start the app with `HOST=127.0.0.1 ./start-server.sh` so only the
  proxy can reach it. HTTPS also lets Save write straight into the file.

## Tests

```sh
./run-tests.sh
```

The checks against real Lode Data files need those files in `samples/`
(the separate samples zip unpacks there — see `samples/README.md` for the
layout, or point `LODEDATA_SAMPLES=/path/to/files` at them). Without them
those checks are skipped and the rest still run.

The browser checks (`tests/test_ui.py`) also need Playwright and a Chromium
build, which are not in the zip:

```sh
.venv/bin/python -m pip install playwright
.venv/bin/python -m playwright install --with-deps chromium    # needs internet
CHROMIUM_PATH=$(ls -d ~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome | head -1) ./run-tests.sh
```

## Back up and update

* Back up `data/designs.db` — it holds every network on the server.
* To update: stop the service, unzip the new version over the old one
  (`data/` is kept), run `./install.sh` again, start the service.

## Open questions

`docs/QUESTIONS.md` lists what still has to be checked in Lode Data to
finish the replica, and what to send for each.
