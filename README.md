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

## วิธีติดตั้ง (สำหรับทีม)

### ขั้นตอนที่ 1: Clone repos

```bash
# Clone ทั้ง wiki_source และ wiki-mcp ไว้ข้างๆ กัน
git clone https://github.com/Pd011161/wiki-mcp.git
git clone <wiki_source_repo_url> wiki_source
```

โครงสร้างที่ควรได้:
```
your-folder/
├── wiki-mcp/
└── wiki_source/
```

### ขั้นตอนที่ 2: เชื่อมต่อ agent

เลือกตาม agent ที่ใช้:

#### Claude Code (CLI)

```bash
# รันจากใน project ที่ต้องการใช้ wiki
claude mcp add wiki-mcp \
  -e WIKI_SOURCE_DIR=/absolute/path/to/wiki_source \
  -- uv run --directory /absolute/path/to/wiki-mcp wiki-mcp
```

#### Claude Desktop

แก้ไฟล์ `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "wiki-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/wiki-mcp", "wiki-mcp"],
      "env": {
        "WIKI_SOURCE_DIR": "/absolute/path/to/wiki_source"
      }
    }
  }
}
```

#### Cursor / Windsurf / อื่นๆ

เพิ่มใน MCP config ของ editor (ดู docs ของแต่ละตัว) ด้วย format เดียวกับ Claude Desktop

### ขั้นตอนที่ 3: ทดสอบ

พิมพ์ถาม agent ว่า:
> "ช่วยดู wiki index ให้หน่อย"

agent จะเรียก `wiki_index` แล้วแสดงสารบัญ wiki ทั้งหมด

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- ไม่ต้องติดตั้ง Python เอง — uv จัดการให้อัตโนมัติ

## Environment Variables

| ตัวแปร | คำอธิบาย | ค่า default |
|--------|----------|-------------|
| `WIKI_SOURCE_DIR` | path ไปยัง wiki_source directory | `../wiki_source` (relative to wiki-mcp) |
| `WIKI_BRANCH` | branch ที่ทีมใช้ร่วมกัน (pull จากตรงนี้ + PR เข้าตรงนี้) | `use` |
| `WIKI_REVIEWER_EMAIL` | email ของ approver ที่ใส่ลง PR body | `c.predee@gmail.com` |
| `WIKI_REVIEWER` | GitHub *username* ของ reviewer (จะ request review ให้อัตโนมัติ) | `Pd011161` |
| `WIKI_AUTO_PULL` | `git pull` อัตโนมัติตอนเปิด server (`0` = ปิด) | `1` |
