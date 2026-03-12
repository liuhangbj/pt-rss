# Stash Auto Scanner

自动监控 Stash 库文件变化，完成 Scan → Identify → NFO 生成全流程。

## 功能

1. **监控文件变化** - 实时检测指定目录的新文件/移动文件
2. **自动 Scan 入库** - 延迟 10 秒后自动扫描入库
3. **自动 Identify** - 延迟 60 秒后使用默认设置刮削（StashDB + ThePornDB）
4. **生成 Emby NFO** - 延迟 90 秒后生成兼容 Emby 的 NFO 文件

## 安装

```bash
pip3 install watchdog requests
```

## 配置

编辑 `stash_auto_scanner.py` 第 16-24 行：

```python
STASH_API_KEY = "你的APIKey"  # 可选
WATCH_PATHS = [
    "/Volumes/115/9.Porns/2.Western",
    "/Volumes/115/9.Porns/1.Japan",
]
```

## 使用

```bash
python3 stash_auto_scanner.py
```

后台运行：
```bash
nohup python3 stash_auto_scanner.py > ~/auto_scanner.log 2>&1 &
```

## NFO 内容

- 标题、日期、评分
- 演员列表
- 制片公司
- 标签（genre + tag）
- 分辨率、编码信息

## 延迟设置

```python
SCAN_DELAY = 10       # 文件变化后等待
IDENTIFY_DELAY = 60   # Scan 后等待
NFO_DELAY = 90        # Identify 后等待
```

## 日志

日志保存在 `~/stash_auto_scanner.log`

## 工作流程

```
检测到新文件
    ↓
等待 10 秒（文件写入完成）
    ↓
Scan 入库
    ↓
等待 60 秒（Stash 处理时间）
    ↓
Identify 刮削（StashDB + ThePornDB）
    ↓
等待 90 秒（刮削完成时间）
    ↓
生成 NFO 文件（和视频文件同名 .nfo）
```

## Emby 配置

Emby 会自动读取同目录下的 `.nfo` 文件作为元数据。确保你的 Emby 库设置中启用了 NFO 元数据读取。
