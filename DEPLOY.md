# Running the Design Assistant on a Linux server

One server runs the app; everyone opens it in their web browser
(Chrome or Edge recommended) at `http://<server>:8000`. Nothing is installed
on the users' PCs.

## What you need

* A Linux server, x86_64 (64-bit Intel/AMD).
* Python 3.10, 3.11, 3.12 or 3.13, with its `venv` module
  (`python3 --version` shows which you have).
  Debian/Ubuntu: `sudo apt install python3 python3-venv`.
  RHEL/Rocky/Alma 9 come with 3.9, which is too old:
  `sudo dnf install python3.11`, then `PYTHON=python3.11 ./install.sh`.
* No internet: the zips carry every package in `wheels/` —
  `lodedata-server.zip` for Python 3.10–3.12, and `lodedata-python313.zip`
  adds the packages for Python 3.13 (unzip it into the same place, only if
  the server's Python is 3.13). On an ARM server `install.sh` fetches the
  packages from the internet instead.

## Install

```sh
sudo unzip lodedata-server.zip -d /opt          # makes /opt/lodedata
sudo unzip lodedata-python313.zip -d /opt       # only with Python 3.13
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

Yes. Each person opens their own `.ntw` in their own browser, and may use
the same spec set as others.

* **Everyone's files stay apart.** Every `.ntw` opened becomes its own
  network on the server, with its own copy of the spec set it was opened
  with. Two people opening files with the same name, or with the same spec
  set, do not touch each other's work.
* **Speed.** One change (a footage, a tap …) and the screen redrawn takes
  about 0.2 s. Measured on a 4-core machine, with everyone changing their
  own large network (AL004 / SN001) at the very same moment:

  | people changing at once | 1 server process | 4 server processes |
  |---|---|---|
  | 5  | 0.9 s | 0.3 s |
  | 10 | 1.7 s | 0.5 s |
  | 20 | 3.7 s | 0.8 s |

  People think between keystrokes, so real waits are shorter.
  `start-server.sh` runs one process per CPU core, at most 4;
  `WORKERS=2 ./start-server.sh` sets it yourself.
* **A network started from scratch** (File > New) is saved with the
  licence and user fields of the last `.ntw` that person opened in their
  browser — as Lode Data on their own PC would — never someone else's
  (blank if they have opened none; Lode Data opens that too).
* **One list of networks.** Everyone sees every network in File > Open.
  If two people ever do change the same network, both changes are kept —
  they are applied one after the other.
* **Opening and saving .ntw files** happens on each person's own PC: Open
  reads a file from their PC, Save writes it back there. Chrome and Edge
  write straight into the file only on `https://` addresses (or on the
  server itself); on a plain `http://` address the saved file is downloaded
  instead — to the Downloads folder — and they keep it from there.
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

* Back up `data/` — `designs.db` holds every network on the server. While
  the server runs, copy it with
  `sqlite3 data/designs.db ".backup /backups/designs.db"`
  (or stop the service and copy the folder).
* To update: stop the service, unzip the new version over the old one
  (`data/` is kept), run `./install.sh` again, start the service.

## Open questions

`docs/QUESTIONS.md` lists what still has to be checked in Lode Data to
finish the replica, and what to send for each.
