# wiki-mcp

MCP server สำหรับเข้าถึง Company LLM Wiki knowledge base

ให้ AI agent (Claude Code, Claude Desktop, Cursor, Windsurf, etc.) ค้นหาและอ่าน wiki ของบริษัทได้ผ่าน MCP protocol

## Tools ที่มี

| Tool | คำอธิบาย | ต้องใช้ |
|------|----------|---------|
| `wiki_index` | ดูสารบัญ wiki ทั้งหมด (เรียกอันนี้ก่อนเสมอ) | อ่านอย่างเดียว |
| `wiki_read` | อ่านหน้า wiki เฉพาะเรื่อง | อ่านอย่างเดียว |
| `wiki_search` | ค้นหาเนื้อหาข้าม wiki ทุกหน้า | อ่านอย่างเดียว |
| `wiki_sync` | ดึงเนื้อหาล่าสุดของทีม (`git pull`) | อ่านอย่างเดียว |
| `wiki_edit` | เสนอแก้ไข wiki → เปิด PR ให้คนตรวจ (ไม่แก้ของกลางตรงๆ) | ต้องมี `gh` + สิทธิ์ push |

> **คนอ่านเฉยๆ** ใช้แค่ `uv` ก็พอ — ไม่ต้องติดตั้ง `gh`
> **คนที่จะแก้ wiki** ต้องติดตั้ง [GitHub CLI](https://cli.github.com/) แล้ว `gh auth login`

### Flow การแก้ไข (wiki_edit)

```
แก้ไฟล์ → push branch ใหม่ → เปิด PR เข้า branch "use" → คนตรวจ merge → ทุกคน auto-pull เห็นของใหม่
```

- ทำงานบน **git worktree แยก** ไม่รบกวน clone ที่คุณเปิดอ่านอยู่
- **ไม่ merge ให้เอง** — รอคนตรวจเสมอ
- Approver ระบุไว้ใน PR body (`WIKI_REVIEWER_EMAIL`); ถ้าตั้ง `WIKI_REVIEWER` เป็น GitHub username จะ request review ให้ด้วย

## ติดตั้งครั้งเดียว (ทุกวิธีต้องมี)

ติดตั้ง `uv` — ตัวจัดการ Python (ไม่ต้องลง Python เอง):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> **wiki_source โหลดให้อัตโนมัติ** — ไม่ต้อง clone เนื้อหาเอง server จะ `git clone` มาเก็บที่ `~/.cache/wiki-mcp/` ครั้งแรก แล้ว `git pull` ให้สดทุกครั้ง (ต้องมีสิทธิ์เข้า repo — ถ้ายังไม่เคย login ให้รัน `gh auth login` หรือตั้ง git credential ก่อน)

## วิธีเชื่อมต่อ (เลือก 1 วิธี)

### วิธี A — Claude Code Plugin ⭐ ง่ายสุด

```bash
/plugin marketplace add Pd011161/wiki-mcp
/plugin install wiki@one7ai-wiki
```
เสร็จ! ไม่ต้อง clone ไม่ต้องแก้ config — และได้ของใหม่อัตโนมัติเมื่อมีการอัปเดต

### วิธี B — uvx รันจาก git (ใช้ได้ทุก agent)

ไม่ต้อง clone โค้ด `uvx` โหลดมารันให้เอง

**Claude Code (CLI):**
```bash
claude mcp add wiki -- uvx --from git+https://github.com/Pd011161/wiki-mcp.git wiki-mcp
```

**Claude Desktop / Cursor / Windsurf** — แก้ MCP config (Claude Desktop อยู่ที่ `~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "wiki": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Pd011161/wiki-mcp.git", "wiki-mcp"]
    }
  }
}
```

### วิธี C — Clone เอง (offline / นักพัฒนา)

```bash
git clone https://github.com/Pd011161/wiki-mcp.git
claude mcp add wiki -- uv run --directory "$(pwd)/wiki-mcp" wiki-mcp
```
จะ clone `wiki_source` ไว้ข้างๆ เองก็ได้ (`../wiki_source`) server จะใช้ตัวนั้นแทน cache

## ทดสอบ

พิมพ์ถาม agent ว่า *"ช่วยดู wiki index ให้หน่อย"* — ถ้าขึ้นสารบัญ wiki แปลว่าใช้ได้

> หมายเหตุ: ทุกวิธีต้องให้ repo `wiki-mcp` เป็น **public** (โค้ดเข้าถึงข้อมูล ไม่มีความลับ) ส่วน `wiki_source` เป็น private ได้ปกติ — server เข้าถึงด้วย git credential ของผู้ใช้แต่ละคน

---

## วิธี D — Remote server (HTTP) สำหรับทั้งบริษัท / ใช้ผ่านเว็บ

แทนที่จะให้ทุกคนรันในเครื่อง สามารถ deploy เป็น HTTP server ตัวเดียว แล้วทุกคนเชื่อมด้วย **URL** ได้ — รองรับ **ChatGPT / Claude.ai เว็บ** ด้วย (stdio ทำไม่ได้)

> **โหมดนี้เป็น read-only** (`wiki_index`, `wiki_read`, `wiki_search`, `wiki_sync`) — `wiki_edit` ปิดไว้ ใครจะแก้ wiki ให้ใช้ stdio (วิธี A–C)

### Deploy บน Render (Docker)

1. Push repo นี้ขึ้น GitHub (มี `Dockerfile` + `render.yaml` ให้แล้ว)
2. Render → **New** → **Blueprint** → เลือก repo นี้ (อ่าน `render.yaml` อัตโนมัติ)
3. ตั้ง env 1 ตัวเอง: **`WIKI_GIT_TOKEN`** = GitHub token (อ่าน `wiki_source` ได้) เพื่อให้ server clone wiki ส่วนตัวได้
   - `WIKI_AUTH_TOKEN` Render สุ่มให้เอง → ก็อปจาก dashboard ไปแจกทีม
4. Deploy เสร็จได้ URL ของ service → เติม `/mcp` ต่อท้าย = endpoint สำหรับแจกทีม

### 🌐 Live endpoint (ใช้งานจริงแล้ว)

```
https://wiki-mcp.onrender.com/mcp
```
ขอ `WIKI_AUTH_TOKEN` (bearer token ของทีม) จากผู้ดูแล แล้วเชื่อมตามด้านล่าง

### ผู้ใช้เชื่อมต่อ (ใส่ URL + token)

**Claude Code:**
```bash
claude mcp add --transport http wiki https://wiki-mcp.onrender.com/mcp \
  -H "Authorization: Bearer <WIKI_AUTH_TOKEN>"
```

**Cursor / VS Code** — ใส่ URL + header `Authorization: Bearer <WIKI_AUTH_TOKEN>` ใน MCP config

> ⚠️ **Bearer token ใช้กับ Claude.ai / ChatGPT (เว็บ) ไม่ได้** — เว็บพวกนี้ต้องใช้ OAuth เท่านั้น ดูหัวข้อถัดไป

> รันเองนอก Render ก็ได้: `WIKI_AUTH_TOKEN=xxx WIKI_GIT_TOKEN=ghp_xxx uv run wiki-mcp-http` (ฟัง `0.0.0.0:$PORT`, health ที่ `/healthz`)

### 🔐 ให้ Claude.ai / ChatGPT (เว็บ) ใช้ได้ — OAuth ผ่าน WorkOS AuthKit

เว็บ client เชื่อม MCP ผ่าน **OAuth** (ไม่มีช่องใส่ header) ต้องมี provider เป็นตัวจัดการ login server เราทำหน้าที่ตรวจ token เท่านั้น แนะนำ **WorkOS AuthKit** (ฟรีถึง 1M users, รองรับ MCP โดยตรง)

**ฝั่ง WorkOS (ทำครั้งเดียว):**
1. สมัคร [workos.com](https://workos.com) → สร้าง environment → เปิดใช้ **AuthKit**
2. ตั้งวิธี login ของคน (เช่น Google SSO / อีเมล) + จำกัดเฉพาะคนในบริษัท
3. Dashboard → **Connect → Configuration** → เปิด **Client ID Metadata Document** และ **Dynamic Client Registration (DCR)** (ให้ Claude.ai register ตัวเองได้)
4. เพิ่ม **Resource Indicator** = `https://wiki-mcp.onrender.com` (ตรงเป๊ะ ไม่มี `/mcp` ต่อท้าย)
5. ก็อป **AuthKit domain** จาก dashboard (เมนู Authentication/AuthKit) — **อย่าประกอบเอง** WorkOS สร้างให้อัตโนมัติ format อาจเป็น `https://xxx.authkit.app` หรือ `https://xxx.authkit.workos.com`
   - เช็คถูกตัว: เปิด `https://<domain>/.well-known/oauth-authorization-server` ถ้าได้ JSON = ใช่

**ฝั่ง Render — เพิ่ม 3 env แล้ว server จะสลับเป็นโหมด OAuth อัตโนมัติ:**
| env | ค่า |
|-----|-----|
| `OAUTH_ISSUER` | AuthKit domain เช่น `https://your-workspace.authkit.workos.com` |
| `OAUTH_AUDIENCE` | `https://wiki-mcp.onrender.com` (ตรงกับ Resource Indicator) |
| `PUBLIC_URL` | `https://wiki-mcp.onrender.com` |

**ผู้ใช้เชื่อม (เว็บ):** Claude.ai → Settings → Connectors → Add custom connector → ใส่ URL `https://wiki-mcp.onrender.com/mcp` → กด connect → login ผ่าน WorkOS → ใช้ได้ (ไม่ต้องใส่ token เอง)

> โหมด OAuth กับ static bearer อยู่ด้วยกันได้: เว็บใช้ OAuth, CLI/Cursor ยังใช้ `WIKI_AUTH_TOKEN` ได้ถ้าตั้งไว้

## Environment Variables

| ตัวแปร | คำอธิบาย | ค่า default |
|--------|----------|-------------|
| `WIKI_SOURCE_DIR` | path ไปยัง wiki_source (ถ้าตั้ง จะใช้/โคลนที่นี่แทน cache) | _(auto: sibling หรือ `~/.cache/wiki-mcp/wiki_source`)_ |
| `WIKI_REPO_URL` | git URL ของ wiki_source ที่ใช้ auto-clone | `https://github.com/Pd011161/wiki_source.git` |
| `WIKI_BRANCH` | branch ที่ทีมใช้ร่วมกัน (clone/pull จากตรงนี้ + PR เข้าตรงนี้) | `use` |
| `WIKI_REVIEWER_EMAIL` | email ของ approver ที่ใส่ลง PR body | `c.predee@gmail.com` |
| `WIKI_REVIEWER` | GitHub *username* ของ reviewer (จะ request review ให้อัตโนมัติ) | `Pd011161` |
| `WIKI_AUTO_PULL` | `git pull` อัตโนมัติตอนเปิด server (`0` = ปิด) | `1` |
| `WIKI_AUTH_TOKEN` | **(HTTP mode)** bearer token ที่ client ต้องส่งมา — บังคับมี | _(ต้องตั้ง)_ |
| `WIKI_GIT_TOKEN` | **(HTTP mode)** GitHub token ให้ server clone wiki_source ส่วนตัว | _(ใช้ `GITHUB_TOKEN` ได้)_ |
| `PORT` | **(HTTP mode)** port ที่ฟัง | `8000` |
| `OAUTH_ISSUER` | **(OAuth)** URL ของ provider (เช่น AuthKit domain) — ตั้งแล้วสลับเป็นโหมด OAuth | _(ปิด OAuth)_ |
| `OAUTH_AUDIENCE` | **(OAuth)** resource indicator (= public URL ของ server) | _(ต้องตั้งคู่กับ issuer)_ |
| `PUBLIC_URL` | **(OAuth)** base URL ของ server เช่น `https://wiki-mcp.onrender.com` | _(ต้องตั้งคู่กับ issuer)_ |
