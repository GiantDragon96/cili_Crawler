# 中文版

## 完整 JumpServer 流程

```bash
cd /home/sysmgr/Crawler
source venv/bin/activate
mkdir -p logs
```

### 启动 noVNC 桌面

```bash
export DISPLAY=:99

openbox &
x11vnc -display :99 -forever -shared -rfbport 5900 -noxdamage &
websockify --web=/usr/share/novnc 6080 localhost:5900 &
```

### 检查 noVNC

```bash
ss -ltnp | grep -E "5900|6080"
```

### 在 Mac 浏览器打开

```
http://43.225.196.186:6080/vnc.html
```

点击 Connect。

### 启动 Chrome CDP

```bash
export DISPLAY=:99

nohup google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/home/sysmgr/chrome-sehuatang-profile \
  --no-sandbox \
  --disable-dev-shm-usage \
  --new-window https://www.sehuatang.org/forum-104-1.html \
  > /home/sysmgr/Crawler/logs/chrome.log 2>&1 &
```

### 检查 Chrome CDP

```bash
curl http://127.0.0.1:9222/json/version
```

在 noVNC 的 Chrome 中，如有需要，通过 Sehuatang 18+/Cloudflare 验证。

### 运行一次爬虫

```bash
export DISPLAY=:99
venv/bin/python crawler.py --all-sources --limit 1 --submit
```

### 添加 cron

```bash
crontab -e
```

**测试用，每 5 分钟：**

```
*/5 * * * * cd /home/sysmgr/Crawler && /home/sysmgr/Crawler/venv/bin/python /home/sysmgr/Crawler/crawler.py --all-sources --limit 1 --submit >> /home/sysmgr/Crawler/logs/cron.log 2>&1
```

**生产环境，每小时：**

```
0 * * * * cd /home/sysmgr/Crawler && /home/sysmgr/Crawler/venv/bin/python /home/sysmgr/Crawler/crawler.py --all-sources --submit >> /home/sysmgr/Crawler/logs/cron.log 2>&1
```

### 查看日志

```bash
tail -f /home/sysmgr/Crawler/logs/cron.log
```

### 同步图片

```bash
rsync -av --password-file="$HOME/.rsync.pd" \
/home/Crawler/images/ \
rsyncuser@43.225.196.166::mm_caiji/sehuatang/img/
```

---

# English Version

## Full JumpServer Flow

```bash
cd /home/sysmgr/Crawler
source venv/bin/activate
mkdir -p logs
```

### Start noVNC desktop

```bash
export DISPLAY=:99

openbox &
x11vnc -display :99 -forever -shared -rfbport 5900 -noxdamage &
websockify --web=/usr/share/novnc 6080 localhost:5900 &
```

### Check noVNC

```bash
ss -ltnp | grep -E "5900|6080"
```

### Open on your Mac browser

```
http://43.225.196.186:6080/vnc.html
```

Click Connect.

### Start Chrome CDP

```bash
export DISPLAY=:99

nohup google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/home/sysmgr/chrome-sehuatang-profile \
  --no-sandbox \
  --disable-dev-shm-usage \
  --new-window https://www.sehuatang.org/forum-104-1.html \
  > /home/sysmgr/Crawler/logs/chrome.log 2>&1 &
```

### Check Chrome CDP

```bash
curl http://127.0.0.1:9222/json/version
```

Then in noVNC Chrome, pass Sehuatang 18+/Cloudflare if needed.

### Run crawler once

```bash
export DISPLAY=:99
venv/bin/python crawler.py --all-sources --limit 1 --submit
```

### Add cron

```bash
crontab -e
```

**Testing every 5 min:**

```
*/5 * * * * cd /home/sysmgr/Crawler && /home/sysmgr/Crawler/venv/bin/python /home/sysmgr/Crawler/crawler.py --all-sources --limit 1 --submit >> /home/sysmgr/Crawler/logs/cron.log 2>&1
```

**Production hourly:**

```
0 * * * * cd /home/sysmgr/Crawler && /home/sysmgr/Crawler/venv/bin/python /home/sysmgr/Crawler/crawler.py --all-sources --submit >> /home/sysmgr/Crawler/logs/cron.log 2>&1
```

### Watch

```bash
tail -f /home/sysmgr/Crawler/logs/cron.log
```

### Sync images

```bash
rsync -av --password-file="$HOME/.rsync.pd" \
/home/Crawler/images/ \
rsyncuser@43.225.196.166::mm_caiji/sehuatang/img/
```
