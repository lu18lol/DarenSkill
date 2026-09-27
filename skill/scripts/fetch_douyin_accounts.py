#!/usr/bin/env python
"""抖音达人数据拉取脚手架（确定性部分）。

输入: 一个 JSON 文件，形如 [{"row":81,"nickname":"晴儿","douyin_id":"4747521m","link":"https://v.douyin.com/..."},{"row":..., "link":"https://www.douyin.com/user/MS4wLjAB..."}]
标红线: 批量拉可达人作品列表，耗时按账号数线性增长。用 execute_code 运行为佳，mid-batch 落盘。

用法:
  python fetch_douyin_accounts.py accounts.json out_prefix
  产出 out_prefix_cache.json(资料+作品) 和 out_prefix_analysis.txt(签名+前10条作品，供人工评估)

依赖: requests；前提是本地 18000 端口已 SSH 隧道转发到 <你的服务器别名> 的 Douyin_API(8000)。
隧道: ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=6 -N -L 18000:127.0.0.1:8000 <你的服务器别名>
"""
import json, os, re, sys, time, requests

BASE = "http://127.0.0.1:18000"

def wait_tunnel(tries=8, timeout=4):
    for _ in range(tries):
        try:
            requests.get(f"{BASE}/openapi.json", timeout=timeout); return True
        except Exception:
            time.sleep(2)
    return False

def extract_link(cell):
    """从可能被污染的单元格文本里提取纯抖音/考拉KOC链接。"""
    m = re.search(r"https://v\.douyin\.com/[A-Za-z0-9_\-]+", cell)
    if m: return m.group(0)
    m = re.search(r"https://www\.douyin\.com/user/[A-Za-z0-9_\-\?=&]+", cell)
    if m: return m.group(0).split("?")[0]
    m = re.search(r"https://www\.koc_platform\.com/[^ ]+", cell)
    if m: return m.group(0)
    return ""

def resolve_sec_uid(link, douyin_id, sess):
    """链接优先；短链走 302 重定向；koc_platform 等非抖音链接用抖音号走 unique_id。"""
    UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0"}
    # 优先用抖音号走 unique_id 解析（最可靠，能识别被截断的 www.douyin.com/user/ 链接，避免抓到错误账号）
    if douyin_id:
        try:
            r = sess.get(f"{BASE}/api/douyin/web/get_user_info_by_unique_id",
                         params={"unique_id": douyin_id}, timeout=20).json()
            if r.get("code") == 200 and isinstance(r.get("data"), dict):
                sc = r["data"].get("user_info", {}).get("sec_uid") or r["data"].get("sec_uid")
                if sc: return sc
        except Exception:
            pass
    m = re.search(r"douyin\.com/user/([A-Za-z0-9_\-]+)", link)
    if m: return m.group(1)
    if "v.douyin.com" in link:
        rr = sess.get(link + "/", headers=UA, allow_redirects=False, timeout=12)
        loc = rr.headers.get("Location") or ""
        m2 = re.search(r"sec_uid=([A-Za-z0-9_\-]+)", loc) or re.search(r"(?:user|share/user)/([A-Za-z0-9_\-]+)", loc)
        if m2: return m2.group(1)
    return ""

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    accounts = json.load(open(sys.argv[1], encoding="utf-8"))
    prefix = sys.argv[2]
    if not wait_tunnel():
        print("ERROR: can't reach Douyin_API on :18000 — start/extend SSH tunnel first."); sys.exit(2)
    sess = requests.Session()
    cache = {"profiles": {}, "posts": {}}
    for a in accounts:
        sec = resolve_sec_uid(a.get("link", ""), a.get("douyin_id", ""), sess)
        if not sec:
            print("NO_SEC", a.get("row"), a.get("nickname")); continue
        a["sec_uid"] = sec
        # profile
        try:
            d = sess.get(f"{BASE}/api/douyin/web/handler_user_profile",
                         params={"sec_user_id": sec}, timeout=20).json()
            if d.get("code") == 200:
                u = (d.get("data") or {}).get("user") or {}
                cache["profiles"][sec] = {k: u.get(k) for k in
                    ("nickname","signature","follower_count","aweme_count","gender","city")}
        except Exception as e:
            print("PROF_ERR", a.get("row"), e)
        time.sleep(0.4)
        # posts
        try:
            d = sess.get(f"{BASE}/api/douyin/web/fetch_user_post_videos",
                         params={"sec_user_id": sec, "max_cursor": 0, "count": 15}, timeout=25).json()
            if d.get("code") == 200:
                al = (d.get("data") or {}).get("aweme_list") or []
                cache["posts"][sec] = [{"desc": (v.get("desc") or "")[:200],
                                        "digg": (v.get("statistics") or {}).get("digg_count")} for v in al]
        except Exception as e:
            print("POSTS_ERR", a.get("row"), e)
        time.sleep(0.5)
        json.dump(cache, open(f"{prefix}_cache.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("OK", a.get("row"), a.get("nickname"))

    # analysis txt for manual assessment
    def compact(s): return re.sub(r"\s+", "", s)[:90] if s else ""
    lines = []
    for a in accounts:
        sec = a.get("sec_uid"); p = cache["profiles"].get(sec, {}); pl = cache["posts"].get(sec, [])
        lines.append(f"\n### row{a.get('row')} {a.get('nickname')} (fans={p.get('follower_count')}, aweme={p.get('aweme_count')})")
        lines.append(f"签名: {compact(p.get('signature'))}")
        for x in pl[:10]:
            lines.append(f"  - {re.sub(r'\\s+', ' ', x.get('desc','')).strip()[:160]}")
        if not pl: lines.append("  - [无作品]")
    open(f"{prefix}_analysis.txt", "w", encoding="utf-8").write("\n".join(lines))
    print("\nWrote", f"{prefix}_cache.json", "and", f"{prefix}_analysis.txt")

if __name__ == "__main__":
    main()
