# Crawler 使用说明

## 按顺序执行

### 本地 Mac 测试

```bash
cd /Users/choonteck/Desktop/work/python
source venv/bin/activate
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m playwright install chromium
venv/bin/python crawler.py --all-sources --limit 1
```

本地提交到正式入库接口：

```bash
export API="http://172.247.9.210:8901/api/sync/insertCili"
venv/bin/python crawler.py --all-sources --limit 1 --submit
```

确认当前终端使用的接口：

```bash
echo "$API"
```

### Ubuntu 服务器首次部署

```bash
cd ~/Crawler
git pull
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m playwright install chromium
sudo venv/bin/python -m playwright install-deps chromium
```

编辑服务器 `.env`：

```bash
nano .env
```

服务器 `.env` 内容：

```dotenv
CRAWLER_IMAGE_PATH=/home/Crawler/images
API=http://172.247.9.210:8901/api/sync/insertCili
```

确认 Python 已读取配置：

```bash
venv/bin/python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API =', os.getenv('API')); print('CRAWLER_IMAGE_PATH =', os.getenv('CRAWLER_IMAGE_PATH'))"
```

部署测试，抓取每个站点一条并提交：

```bash
venv/bin/python crawler.py --all-sources --limit 1 --submit
```

### Ubuntu 服务器日常正式运行

```bash
cd ~/Crawler
venv/bin/python crawler.py --all-sources --limit 1 --submit
```

每个站点尝试抓取三条：

```bash
venv/bin/python crawler.py --all-sources --limit 3 --submit
```

## 功能

`crawler.py` 会从以下站点抓取资源：

* 141love
* hjd2048
* sehuatang

抓取内容包括标题、磁力链接、封面图和其他资源信息，并可选择提交到入库接口。

## .env 配置

本地：

```dotenv
CRAWLER_IMAGE_PATH=images
API=http://127.0.0.1:5000/api/sync/insertCili
```

服务器：

```dotenv
CRAWLER_IMAGE_PATH=/home/Crawler/images
API=http://172.247.9.210:8901/api/sync/insertCili
```

如部分站点需要登录，可配置：

```dotenv
cookie1=xxx
cookie2=xxx
```

不要提交 `.env` 或 Cookie 到 Git。

## 常用命令

抓取测试，不入库：

```bash
venv/bin/python crawler.py --all-sources --limit 1
```

每个站点抓取三条，不入库：

```bash
venv/bin/python crawler.py --all-sources --limit 3
```

测试指定帖子：

```bash
venv/bin/python crawler.py --thread-url "帖子地址"
```

测试指定帖子并入库：

```bash
venv/bin/python crawler.py --thread-url "帖子地址" --submit
```

检查 Python 语法：

```bash
venv/bin/python -m py_compile crawler.py
```

## 成功标志

```text
Ready:
```

表示已成功解析帖子并找到磁力链接。

```text
API response: {'code': 0, ...}
```

表示成功入库。

```text
API response: {'code': 1, 'msg': 'Data already exists'}
```

表示资源已存在，属于正常情况。

## 图片

图片保存路径由 `CRAWLER_IMAGE_PATH` 控制。服务器查看图片：

```bash
ls -lah /home/Crawler/images
```

图片同步到资源服务器：

```bash
rsync -av --password-file="$HOME/.rsync.pd" \
/home/Crawler/images/ \
rsyncuser@43.225.196.166::mm_caiji/sehuatang/img/
```

同步后，图片公开地址格式：

```text
https://im.2ddvp57bd3.com/sehuatang/img/<filename>
```

## Sehuatang 专用运行方式

Sehuatang 有 Cloudflare / 18+ 验证，需要用服务器上的真实 Chrome 来打开页面。

简单理解：

```text
noVNC = 让我们看到服务器浏览器
真实 Chrome = 手动过 Sehuatang 验证
9222 = 让 crawler 连接这个 Chrome
```

### 1. 启动 noVNC

如果 noVNC 没有运行，在服务器执行：

```bash
export DISPLAY=:99
openbox &
x11vnc -display :99 -forever -shared -rfbport 5900 -noxdamage &
websockify --web=/usr/share/novnc 6080 localhost:5900 &
```

检查端口：

```bash
ss -ltnp | grep -E "5900|6080"
```

然后在本机浏览器打开：

```text
http://43.225.196.186:6080/vnc.html
```
ƒ√
点击 `Connect`。

### 2. 启动真实 Chrome

在服务器另一个终端执行：

```bash
export DISPLAY=:99

google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/home/sysmgr/chrome-sehuatang-profile \
  --no-sandbox \
  --disable-dev-shm-usage \
  about:blank
```

说明：

* `9222`：crawler 通过这个端口连接 Chrome。
* `chrome-sehuatang-profile`：保存 Sehuatang 的 cookie/session。
* `--new-window`：直接打开 Sehuatang 页面。

### 3. 手动通过验证

在 noVNC 里的 Chrome：

1. 点击 `满18岁 / If you are over 18`
2. 如果出现 Cloudflare，就等待或手动完成验证
3. 看到论坛列表页后，再跑 crawler

### 4. 确认 crawler 可以连接 Chrome

在服务器执行：

```bash
curl http://127.0.0.1:9222/json/version
```

如果有返回 JSON，表示 Chrome 正常，crawler 可以连接。

### 5. 运行 crawler

不要关闭 Chrome。然后在服务器另一个终端执行：

```bash
cd ~/Crawler
git pull
export DISPLAY=:99
venv/bin/python crawler.py --all-sources --limit 1 --submit
```

成功时会看到 需要自己按：
If Cloudflare/18 page appears, click through it, then press Enter here...
If Cloudflare/18 page appears, click through it, then press Enter here...

```text
Source: sehuatang | Tag: 素人系列
Ready:
Magnet:
API response: {'code': 0, ...}
```

### 6. 同步图片

```bash
rsync -av --password-file="$HOME/.rsync.pd" \
/home/Crawler/images/ \
rsyncuser@43.225.196.166::mm_caiji/sehuatang/img/
```

注意：跑 Sehuatang 前，一定要先打开真实 Chrome，并确认 `9222` 可用。

## 常见问题

### Sehuatang Cloudflare / 18+ 验证

出现以下提示时，按提示在浏览器完成验证：

```text
If Cloudflare/18 page appears, click through it, then press Enter here...
```

服务器运行 Sehuatang 需要 Playwright Chromium 的 Linux 依赖。若看到
`libnspr4.so` 缺失，请执行：

```bash
sudo venv/bin/python -m playwright install-deps chromium
```

### 找不到磁力链接

```text
no magnet URL found
```

可能是帖子没有磁力、需要登录、Cloudflare 拦截，或页面格式变更。

### 权限不足

```text
thread requires an authorized forum account
```

表示需要有效账号或 Cookie。

### 网络错误

```text
403 Forbidden
Read timed out
Connection refused
Connection reset
```

通常是 Cloudflare、Cookie 失效、网站异常或网络问题；稍后重试即可。
