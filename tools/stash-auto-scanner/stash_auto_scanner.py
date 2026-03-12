#!/usr/bin/env python3
"""
Stash Auto Scanner - 自动监控、入库、刮削、生成 NFO
功能：
1. 监控指定目录的文件变化
2. 自动 Scan 入库
3. 自动 Identify 刮削（使用默认设置）
4. 生成 Emby 兼容的 NFO 文件
"""

import os
import sys
import time
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# ==================== 配置 ====================
# Stash 配置
STASH_URL = "http://localhost:9999/graphql"
STASH_API_KEY = ""  # 如果有API Key，填在这里

# 监控路径（你的 Stash 库路径）
WATCH_PATHS = [
    "/Volumes/115/9.Porns/2.Western",
    "/Volumes/115/9.Porns/1.Japan",
]

# 排除的子目录
EXCLUDE_DIRS = [
    ".tmp", ".temp", ".grab", ".stfolder", 
    "trash", "temp", "tmp"
]

# 监控的文件扩展名
VIDEO_EXTENSIONS = [
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", 
    ".m4v", ".flv", ".webm", ".ts", ".m2ts"
]

# 延迟设置（秒）
SCAN_DELAY = 10       # 文件变化后等待多久开始 Scan
IDENTIFY_DELAY = 60   # Scan 完成后等待多久开始 Identify（给 Stash 时间处理）
NFO_DELAY = 90        # Identify 完成后等待多久生成 NFO

# 日志文件
LOG_FILE = os.path.expanduser("~/stash_auto_scanner.log")
# =============================================

def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg = f"[{timestamp}] {message}"
    print(msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def run_graphql_query(query, variables=None):
    """执行 GraphQL 查询"""
    try:
        import requests
        
        headers = {
            'Content-Type': 'application/json',
        }
        if STASH_API_KEY:
            headers['ApiKey'] = STASH_API_KEY
        
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        response = requests.post(
            STASH_URL,
            headers=headers,
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            log(f"GraphQL 错误: HTTP {response.status_code}")
            return None
    except Exception as e:
        log(f"GraphQL 异常: {e}")
        return None

def scan_path(path):
    """扫描指定路径"""
    log(f"📁 开始 Scan: {path}")
    
    query = """
    mutation Scan($path: String!) {
        metadataScan(input: {
            paths: [$path]
            scanGenerateCovers: true
            scanGeneratePreviews: true
            scanGenerateSprites: true
        })
    }
    """
    
    result = run_graphql_query(query, {'path': path})
    if result and 'data' in result:
        log(f"✅ Scan 已触发")
        return True
    else:
        log(f"❌ Scan 失败: {result}")
        return False

def run_auto_identify(scene_ids):
    """使用 Stash 默认设置进行 Identify"""
    if not scene_ids:
        return False
    
    log(f"🔍 开始 Identify {len(scene_ids)} 个场景...")
    
    # 使用 Stash 的自动识别（默认设置）
    query = """
    mutation Identify($sceneIds: [Int!]!) {
        metadataIdentify(input: {
            sceneIDs: $sceneIds
            sources: [
                {source: STASHDB}
                {source: THEPORNDB}
            ]
            options: {
                setCoverImage: true
                setOrganized: false
                includeMalePerformers: true
            }
        })
    }
    """
    
    result = run_graphql_query(query, {'sceneIds': scene_ids})
    if result and 'data' in result:
        log(f"✅ Identify 已触发")
        return True
    else:
        log(f"⚠️ Identify 结果: {result}")
        return False

def get_recent_scenes(path, minutes=10):
    """获取最近入库的场景"""
    from datetime import datetime, timedelta
    
    min_time = (datetime.now() - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
    
    query = """
    query FindRecentScenes($minTime: Timestamp!, $path: String!) {
        findScenes(
            filter: {per_page: 100}
            scene_filter: {
                path: {modifier: INCLUDES, value: $path}
                created_at: {modifier: GREATER_THAN, value: $minTime}
            }
        ) {
            scenes {
                id
                title
                path
                date
                rating
                performers {
                    name
                }
                studio {
                    name
                }
                tags {
                    name
                }
                files {
                    width
                    height
                    duration
                    video_codec
                    audio_codec
                }
            }
        }
    }
    """
    
    result = run_graphql_query(query, {'minTime': min_time, 'path': path})
    if result and 'data' in result and result['data'] and 'findScenes' in result['data']:
        scenes = result['data']['findScenes'].get('scenes', [])
        return scenes
    return []

def generate_nfo(scene, output_path):
    """生成 Emby 兼容的 NFO 文件"""
    try:
        root = ET.Element("movie")
        
        # 标题
        title = ET.SubElement(root, "title")
        title.text = scene.get('title', '')
        
        # 上映日期
        if scene.get('date'):
            premiered = ET.SubElement(root, "premiered")
            premiered.text = scene['date']
            year = ET.SubElement(root, "year")
            year.text = scene['date'][:4]
        
        # 评分
        if scene.get('rating'):
            rating = ET.SubElement(root, "rating")
            rating.text = str(scene['rating'])
        
        # 演员
        for performer in scene.get('performers', []):
            actor = ET.SubElement(root, "actor")
            name = ET.SubElement(actor, "name")
            name.text = performer.get('name', '')
        
        # 制片公司
        if scene.get('studio'):
            studio = ET.SubElement(root, "studio")
            studio.text = scene['studio'].get('name', '')
        
        # 标签
        for tag in scene.get('tags', []):
            genre = ET.SubElement(root, "genre")
            genre.text = tag.get('name', '')
            tag_elem = ET.SubElement(root, "tag")
            tag_elem.text = tag.get('name', '')
        
        # 文件信息
        files = scene.get('files', [])
        if files:
            file_info = files[0]
            resolution = ET.SubElement(root, "resolution")
            resolution.text = f"{file_info.get('width', 0)}x{file_info.get('height', 0)}"
            
            codec = ET.SubElement(root, "codec")
            codec.text = file_info.get('video_codec', '')
        
        # 保存文件
        tree = ET.ElementTree(root)
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        
        log(f"✅ NFO 已生成: {output_path}")
        return True
    except Exception as e:
        log(f"❌ NFO 生成失败: {e}")
        return False

def process_nfo_generation(scenes):
    """处理 NFO 生成"""
    log(f"📝 开始生成 {len(scenes)} 个 NFO 文件...")
    
    success_count = 0
    for scene in scenes:
        scene_path = scene.get('path', '')
        if not scene_path:
            continue
        
        # NFO 文件路径（和视频文件同名）
        base_path = os.path.splitext(scene_path)[0]
        nfo_path = base_path + ".nfo"
        
        # 如果 NFO 已存在，跳过
        if os.path.exists(nfo_path):
            log(f"⏭️ NFO 已存在，跳过: {nfo_path}")
            continue
        
        if generate_nfo(scene, nfo_path):
            success_count += 1
        
        time.sleep(0.5)  # 避免请求过快
    
    log(f"✅ NFO 生成完成: {success_count}/{len(scenes)}")

def should_process_file(filepath):
    """判断是否应该处理该文件"""
    filepath_lower = filepath.lower()
    
    for exclude in EXCLUDE_DIRS:
        if exclude.lower() in filepath_lower:
            return False
    
    ext = Path(filepath).suffix.lower()
    if ext not in VIDEO_EXTENSIONS:
        return False
    
    return True

def main():
    log("=" * 60)
    log("Stash Auto Scanner (NFO 版) 启动")
    log("=" * 60)
    log(f"监控路径: {WATCH_PATHS}")
    log(f"流程: 监控 → Scan → Identify → NFO")
    log("=" * 60)
    
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        log("❌ 请先安装 watchdog: pip3 install watchdog")
        sys.exit(1)
    
    pending_scans = set()
    processing_lock = False
    
    class Handler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            if should_process_file(event.src_path):
                dir_path = os.path.dirname(event.src_path)
                pending_scans.add(dir_path)
                log(f"📥 检测到新文件: {event.src_path}")
        
        def on_moved(self, event):
            if event.is_directory:
                return
            if should_process_file(event.dest_path):
                dir_path = os.path.dirname(event.dest_path)
                pending_scans.add(dir_path)
                log(f"📥 检测到文件移动: {event.dest_path}")
    
    observer = Observer()
    handler = Handler()
    
    for path in WATCH_PATHS:
        if os.path.exists(path):
            observer.schedule(handler, path, recursive=True)
            log(f"✅ 开始监控: {path}")
        else:
            log(f"⚠️ 路径不存在: {path}")
    
    observer.start()
    log("\n🚀 监控运行中... (按 Ctrl+C 停止)\n")
    
    try:
        while True:
            time.sleep(1)
            
            if processing_lock or not pending_scans:
                continue
            
            # 处理队列
            processing_lock = True
            to_process = list(pending_scans)
            pending_scans.clear()
            
            for path in to_process:
                log(f"\n{'='*60}")
                log(f"🎬 开始处理目录: {path}")
                log(f"{'='*60}")
                
                # Step 1: Scan
                log(f"\n⏳ 等待 {SCAN_DELAY} 秒后 Scan...")
                time.sleep(SCAN_DELAY)
                
                if not scan_path(path):
                    continue
                
                # Step 2: Identify
                log(f"\n⏳ 等待 {IDENTIFY_DELAY} 秒后 Identify...")
                time.sleep(IDENTIFY_DELAY)
                
                # 获取新入库的场景
                scenes = get_recent_scenes(path, minutes=15)
                if not scenes:
                    log("⚠️ 未找到新场景")
                    continue
                
                log(f"🎯 找到 {len(scenes)} 个新场景")
                scene_ids = [s['id'] for s in scenes]
                
                # 运行 Identify（默认设置）
                run_auto_identify(scene_ids)
                
                # Step 3: 生成 NFO
                log(f"\n⏳ 等待 {NFO_DELAY} 秒后生成 NFO...")
                time.sleep(NFO_DELAY)
                
                # 重新获取场景信息（Identify 后可能有更新）
                updated_scenes = get_recent_scenes(path, minutes=20)
                if updated_scenes:
                    process_nfo_generation(updated_scenes)
                else:
                    process_nfo_generation(scenes)
                
                log(f"\n✅ 目录处理完成: {path}")
            
            processing_lock = False
    
    except KeyboardInterrupt:
        log("\n🛑 停止监控")
        observer.stop()
    
    observer.join()
    log("👋 已退出")

if __name__ == "__main__":
    main()
