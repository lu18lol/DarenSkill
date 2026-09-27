# DarenSkill — 抖音达人筛选评估

一套给内容/投放团队用的达人筛选工具：**装好后自动引导你接上自己的飞书和抖音解析服务，然后就能批量筛选达人账号。**

---

## 这个包里有啥

```
DarenSkill/
├── README.md              ← 你正在看的文件
├── skill/                 ← 达人筛选 Skill（装进 Hermes/Claude 等 Agent 即用）
│   ├── SKILL.md
│   ├── references/
│   │   ├── 本地部署引导.md            ← 装完自动引导搭环境
│   │   └── pdf-version-convergence.md
│   └── scripts/
│       ├── fetch_douyin_accounts.py   ← 批量拉达人数据
│       ├── scan_todo_rows.py          ← 扫表找待审行
│       └── batch_download_douyin.sh   ← 批量下载抖音视频
```

---

## 它能干什么

- **读飞书表格/文档**：电子表格、多维表格、独立文档(docx)、Drive 上传的 PDF 课件
- **批量筛选抖音达人**：拉达人资料 + 作品 → 出「标签 / 账号评估 / 是否合适」三段结论 → 写回飞书表
- **扫待审行**：找出"表里有人但还没评审"的行
- **批量下载抖音视频**：元素材回收
- **达人主页链接解析**：sec_uid 提取、短链重定向、抖音号兜底

---

## 怎么用（三步）

### 第 1 步：装 Skill
把 `skill/` 整个文件夹丢进你的 Agent 技能目录：
- Hermes：`~/.hermes/skills/DarenSkill/`
- 其他 Agent：放进对应的 skills 目录

装完后跟 Agent 说一句「**装好了，帮我开始**」，它会自动引导你走完下面两步。

### 第 2 步：接上飞书（lark-cli）
```
npm install -g @larksuite/cli
lark-cli auth login
```
用你自己的飞书账号授权。详见 `skill/references/本地部署引导.md`。

### 第 3 步：部署抖音解析 API
推荐用开源项目自部署：**Douyin_TikTok_Download_API**（作者 Evil0ctal，Apache-2.0）
https://github.com/Evil0ctal/Douyin_TikTok_Download_API

```bash
git clone https://github.com/Evil0ctal/Douyin_TikTok_Download_API.git
cd Douyin_TikTok_Download_API
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python start.py
```

**然后必须填你自己的抖音 Cookie**（不填拉不到数据）：
Chrome 打开 douyin.com 登录 → F12 → Network → 任意请求 → Request Headers 里复制 `Cookie:` 整行 → 粘进 `crawlers/douyin/web/config.yaml`。

---

## 关于 Cookie / 密钥（重要）

- 本包**不含任何他人密钥、Cookie、服务器地址**，全部留空，等你填自己的。
- **Cookie = 你的账号登录凭证**。只放本地/自己服务器，别发给任何人、别提交到 git。
- 抖音解析服务建议只跑在 `127.0.0.1`（本机）或用 SSH 隧道访问，不要暴露公网。

---

## 环境要求

- Python 3.10+
- Node.js（装 lark-cli 用）
- 一个能正常访问抖音的网络环境
- 你自己的飞书账号

---

## 开源署名 / Credits

达人数据依赖的解析服务基于开源项目 **Douyin_TikTok_Download_API**（作者 Evil0ctal），
采用 Apache License 2.0 授权。本 Skill 不包含该项目代码，仅说明如何部署它。
原项目地址：https://github.com/Evil0ctal/Douyin_TikTok_Download_API

使用相关工具时请遵守原项目许可证及平台相关规定，仅将抓取内容用于学习与创作参考，
不得原样搬运他人作品。

---

## 常见问题

**Q: lark-cli 报 "hermes context detected but not bound"？**
A: Agent 环境里要剥离 `HERMES_` 前缀的环境变量再调用，详见 `本地部署引导.md` 第 1.3 节。

**Q: 抖音 API 起了但拉不到数据？**
A: 九成是 Cookie 没填或过期。抖音 Cookie 有效期有限，失效了重新抓一次。

**Q: 表格里读到的列和预期不一样？**
A: 表可能被重建过，列字母会变。每次动表前先读表头核对，别硬编码列号。

**Q: SSH 隧道老是断？**
A: 加保活参数 `-o ServerAliveInterval=30 -o ServerAliveCountMax=3`。
