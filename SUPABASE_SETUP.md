# Supabase 账户数据上云 · 配置步骤

> 目标：让「部署版网站」和「本地管理后台」共享同一份账户数据，后台随时管理部署版注册的账户。
> 原理：账户服务已改成双模式——配了 `SUPABASE_DB_URL` 就用 Supabase/Postgres，没配就用本地 SQLite（部署版自动降级访客模式）。

---

## 一、注册 Supabase 并创建项目（约 3 分钟）

1. 打开 **https://supabase.com**，用 GitHub / 邮箱注册；
2. 点 **New project**，选 **Free** 档，填项目名（如 `studyhack`），设置**数据库密码**（记牢）；
3. 等 1~2 分钟项目初始化完成。

## 二、获取连接串（关键）

1. 进项目 Dashboard → 顶部 **Connect** 按钮（或 Settings → Database）；
2. 选 **Transaction pooler**（适合 Serverless，Streamlit 必用这个）；
3. 复制连接串，形如：
   ```
   postgresql://postgres.<项目ID>:<数据库密码>@aws-0-<区域>.pooler.supabase.com:6543/postgres
   ```
   把 `<数据库密码>` 替换成你在创建项目时设的密码。

> ⚠️ 连接串里含密码，**绝不能提交到 GitHub**。下面两种配置方式都不会进版本库。

## 三、建表（可选，代码会自动建）

代码首次运行会自动建 `accounts` 表。如想手动建，在 **SQL Editor** 执行：

```sql
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    account TEXT NOT NULL UNIQUE,
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);
```

## 四、配置连接串

### 本地（网站 + 管理后台）

设置环境变量（Windows PowerShell）：

```powershell
setx SUPABASE_DB_URL "postgresql://postgres.xxx:密码@aws-0-xx.pooler.supabase.com:6543/postgres"
```

或临时生效（当前终端）：

```powershell
$env:SUPABASE_DB_URL = "postgresql://postgres.xxx:密码@aws-0-xx.pooler.supabase.com:6543/postgres"
```

### 部署版（Streamlit Cloud）

1. 打开你的 Streamlit Cloud 应用 → **Settings → Secrets**；
2. 添加：

```toml
SUPABASE_DB_URL = "postgresql://postgres.xxx:密码@aws-0-xx.pooler.supabase.com:6543/postgres"
```

3. 保存后 Streamlit 自动重启。

> Streamlit Secrets 存在平台侧，**不会进入 GitHub**，是部署版安全存放连接串的正确位置。

## 五、验证

1. 本地启动网站 `streamlit run app.py` → 侧边栏注册一个账号；
2. 本地启动后台 `streamlit run admin_app.py --server.port 8502` → 登录后应能看到刚注册的账号；
3. 打开部署版网站 → 注册一个账号 → 回到本地后台，应能看到两个账号（本地 + 部署版），说明已共享同一份云端数据。

---

## 常见问题

- **连不上 / 连接超时**：确认用的是 Transaction pooler（6543 端口）而非 Direct connection；确认数据库密码正确。
- **本地没配连接串时**：自动用本地 SQLite，功能照常，只是数据不共享、部署版为访客模式。
- **想切回纯本地**：删除 `SUPABASE_DB_URL` 环境变量 / Secrets 即可。
