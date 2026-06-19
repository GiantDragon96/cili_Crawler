# Crawler 使用说明

## 功能
`crawler.py` 会从以下站点抓取资源：

* 141love
* hjd2048
* sehuatang

抓取内容包括：

* 标题
* 磁力链接
* 封面图
* 其他资源信息

并可选择提交到入库接口：

```text
http://127.0.0.1:5000/api/sync/insertCili or http://172.247.9.210:8901/api/sync/insertCili
```

---

## 环境安装

首次执行：

```bash
python3 -m venv venv
source venv/bin/activate
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m playwright install chromium
```

---

## .env 配置

本地：

```env
CRAWLER_IMAGE_PATH=images
API=http://127.0.0.1:5000/api/sync/insertCili
```

服务器：

```env
CRAWLER_IMAGE_PATH=/home/Crawler/images
API=http://172.247.9.210:8901/api/sync/insertCili
```

如部分站点需要登录，可配置：

```env
cookie1=xxx
cookie2=xxx
```

---

## 常用命令

抓取测试（不入库）：

```bash
venv/bin/python crawler.py --all-sources --limit 1
```

每个站点抓取 3 条：

```bash
venv/bin/python crawler.py --all-sources --limit 3
```

抓取并提交入库：

```bash
venv/bin/python crawler.py --all-sources --limit 1 --submit
```

测试指定帖子：

```bash
venv/bin/python crawler.py --thread-url "帖子地址"
```

测试指定帖子并入库：

```bash
venv/bin/python crawler.py --thread-url "帖子地址" --submit
```

---

## 成功标志

看到：

```text
Ready:
```

表示已成功解析帖子并找到磁力链接。

看到：

```text
API response: {'code': 0}
```

表示成功入库。

看到：

```text
API response: {'code': 1, 'msg': 'Data already exists'}
```

表示资源已存在，属于正常情况。

---

## 常见问题

### 1. 需要点击 Cloudflare / 18+

出现：

```text
If Cloudflare/18 page appears, click through it, then press Enter here...
```

按提示打开浏览器完成验证即可。

---

### 2. 找不到磁力链接

出现：

```text
no magnet URL found
```

可能原因：

* 帖子没有磁力链接
* 需要登录才能查看
* 页面被 Cloudflare 拦截
* 帖子内容格式变更

---

### 3. 权限不足

出现：

```text
thread requires an authorized forum account
```

表示需要有效账号或 Cookie。

---

### 4. 网络错误

常见错误：

```text
403 Forbidden
Read timed out
Connection refused
Connection reset
```

通常是：

* Cloudflare 拦截
* Cookie 失效
* 网站异常
* 网络问题

稍后重试即可。

---

## 图片保存

图片保存路径由：

```env
CRAWLER_IMAGE_PATH
```

控制。

服务器查看图片：

```bash
ls -lah /home/Crawler/images
```
---

## 当前状态

目前测试结果正常：

```text
code = 0
```
成功入库。

```text
code = 1
```
资源已存在/失败响应。

