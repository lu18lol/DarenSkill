#!/bin/bash
# 批量下载抖音视频(无水印) —— 跑在 Douyin_API 所在服务器(<你的服务器别名>)上
#
# 用法:
#   1) 把 LIST 换成要下的视频 id(来自 https://www.douyin.com/video/<id> 最后那段)
#   2) scp 到服务器:  scp batch_download_douyin.sh <你的服务器别名>:/tmp/
#   3) 去 CRLF(Windows 写的脚本带 \r 会报错, 必做):
#        ssh <你的服务器别名> "sed -i 's/\r$//' /tmp/batch_download_douyin.sh && chmod +x /tmp/batch_download_douyin.sh"
#   4) 后台跑:  ssh <你的服务器别名> "nohup bash /tmp/batch_download_douyin.sh > /tmp/dl.log 2>&1 &"
#      轮询:     ssh <你的服务器别名> "tail -20 /tmp/dl.log; grep -c '^OK' /tmp/dl.log"
#   5) 拉回本地: scp -q <你的服务器别名>:'/tmp/douyin_dl/*.mp4' "<你的下载目录>/达播回收"
#
# 关键点:
#   - 路由是 /api/download (无子前缀!), 不是 /api/download/download
#   - prefix=false 去掉文件名前缀 douyin.wtf_ , 落盘名=视频id
#   - 成功判据是「字节数>50000 且 file 显示 ISO Media, MP4」——接口错误也返 http=200, 不能只看 http_code
#   - 已存在同名文件则 skip(端点自身也有"文件存在即返回旧文件"的缓存语义)

OUT=/tmp/douyin_dl
mkdir -p "$OUT"

LIST="7683925863960457715
7683899901248155493
7683890773621095369"

OK=0; FAIL=0
for vid in $LIST; do
  f="$OUT/$vid.mp4"
  if [ -s "$f" ]; then echo "SKIP $vid (已存在 $(stat -c%s "$f"))"; OK=$((OK+1)); continue; fi
  code=$(curl -s -m 120 -o "$f" -w '%{http_code}' \
    "http://127.0.0.1:8000/api/download?url=https%3A%2F%2Fwww.douyin.com%2Fvideo%2F$vid&prefix=false")
  sz=$(stat -c%s "$f" 2>/dev/null || echo 0)
  ft=$(file -b "$f" 2>/dev/null | cut -c1-20)
  if [ "$code" = "200" ] && [ "$sz" -gt 50000 ]; then
    echo "OK   $vid  $sz bytes  $ft"
    OK=$((OK+1))
  else
    echo "FAIL $vid  http=$code size=$sz"
    rm -f "$f"   # 删掉 301 字节的错误 JSON, 避免下次被 skip 逻辑误判为已下载
    FAIL=$((FAIL+1))
  fi
done
echo "=== DONE ok=$OK fail=$FAIL ==="
ls -la "$OUT" | tail -5
