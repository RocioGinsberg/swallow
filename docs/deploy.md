## 最终拓扑

```
┌─ 课题组 Ubuntu 工作站（Tailscale: 100.x.x.10）──┐
│                                                    │
│  swl CLI                                          │
│    └─ Swallow Runtime                             │
│        ├─ RouteRegistry                           │
│        ├─ Dialect Adapters                        │
│        └─ 自建遥测层（token usage / route health）│
│           │                                        │
│           └─ HTTP → localhost:3000 (new-api)      │
│                                                    │
│  Docker Compose Stack:                            │
│  ┌──────────────────────────────────────────┐    │
│  │ new-api    :3000  渠道管理 + 格式互转    │    │
│  │   ├─ HTTPS_PROXY=http://vps-wg-ip:8888   │    │
│  │   └─ 上游: OpenAI/Anthropic/OR/AIHubMix  │    │
│  │                                           │    │
│  │ Open WebUI :3002  对话面板                │    │
│  │   └─ OPENAI_API_BASE=http://new-api:3000 │    │
│  │ Caddy      :443   本地 HTTPS + 反代      │    │
│  └──────────────────────────────────────────┘    │
│                                                    │
│  Tailscale 客户端                                  │
│  WireGuard 客户端 → VPS:51820                     │
└────────────────────┬───────────────────────────────┘
                     │
         ┌───────────┴────────────┐
         │                        │
   Tailscale 内网           WireGuard 隧道
   (跨设备访问业务)          (API 出口流量)
         │                        │
         │                        ▼
         │              ┌─ VPS 新加坡 1C 512M ─┐
         │              │                        │
         │              │ WireGuard Server       │
         │              │   :51820 (UDP)         │
         │              │                        │
         │              │ Tinyproxy              │
         │              │   10.8.0.1:8888        │
         │              │   (仅绑 WG 内网)       │
         │              │                        │
         │              └──────────┬─────────────┘
         │                         │
         │                         ▼
         │               OpenAI / Anthropic / ...
         │
         ▼
   手机 / iPad / 笔记本
   (Tailscale 内任意设备
    → http://100.x.x.10:3002
    访问 Open WebUI)
```

## 三条数据通路的分工

这是整个架构的核心，务必理清楚：

**1. 本地访问（零延迟主路径）**
swl CLI 和本地浏览器直接访问 `localhost:3000` / `localhost:3002`，不经过任何隧道，延迟为零。

**2. 出口流量（WireGuard，单向）**
new-api 向 OpenAI/Anthropic 等上游发请求时，通过 `HTTPS_PROXY` 环境变量走 VPS 上的 Tinyproxy 出去。外部 API 厂商只看到 VPS 的 IP，看不到你课题组的 IP。

**3. 跨设备访问（Tailscale，按需)**
在手机、iPad、笔记本上装 Tailscale 客户端，加入同一个 Tailnet 后直接访问工作站的 `100.x.x.10:3002` 就能用 Open WebUI。不需要端口映射、不需要公网暴露、不需要 Cloudflare。

**为什么不用 Tailscale 也跑出口流量**：
Tailscale 的 exit node 功能可以让工作站的所有流量走 VPS 出去，看起来能替代 WG+Tinyproxy。但有两个问题——exit node 是设备级全局设置（会影响 apt、git 等所有流量，不只 AI 调用），且 Tailscale 依赖自己的控制平面，你不完全掌控。所以专业的事交给专业组件：Tailscale 管跨设备访问，WG+Tinyproxy 管出口代理。

## VPS 端配置

### 规格

1C 512M RAM 就够，搬瓦工 / RackNerd / Vultr 新加坡最便宜档位。WireGuard 内核态几乎不吃资源，Tinyproxy 本身不到 10MB 内存。

### WireGuard Server

```ini
# /etc/wireguard/wg0.conf
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = <vps-private-key>
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
# 课题组工作站
PublicKey = <workstation-public-key>
AllowedIPs = 10.8.0.2/32
```

开启 IP 转发：

```bash
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
sudo systemctl enable --now wg-quick@wg0
```

### Tinyproxy

关键是**只绑 WireGuard 内网接口**，绝不能暴露公网：

```conf
# /etc/tinyproxy/tinyproxy.conf
Port 8888
Listen 10.8.0.1
Timeout 600
Allow 10.8.0.0/24
DisableViaHeader Yes
```

`Listen 10.8.0.1` 是安全关键——监听在 WG 内网 IP 上，公网扫描永远扫不到这个端口。配合 `Allow 10.8.0.0/24` 双重保险。

### 防火墙

```bash
sudo ufw allow 22/tcp        # SSH
sudo ufw allow 51820/udp     # WireGuard
sudo ufw default deny incoming
sudo ufw enable
# 故意不开 8888——Tinyproxy 只从 WG 接口进
```

## 工作站端配置

### WireGuard Client

```ini
# /etc/wireguard/wg0.conf
[Interface]
Address = 10.8.0.2/24
PrivateKey = <workstation-private-key>

[Peer]
PublicKey = <vps-public-key>
Endpoint = vps-public-ip:51820
# 关键：只路由到 VPS 内网，不做 full tunnel
AllowedIPs = 10.8.0.1/32
PersistentKeepalive = 25
```

`AllowedIPs = 10.8.0.1/32` 很关键——**只路由到 VPS 的 WG 内网 IP**，不影响工作站其他流量。如果设成 `0.0.0.0/0` 就变成全局代理了，那你的 apt、ssh、所有流量都要绕 VPS，完全不是你想要的。

启用：

```bash
sudo systemctl enable --now wg-quick@wg0
# 验证
ping 10.8.0.1
curl -x http://10.8.0.1:8888 https://api.openai.com/v1/models -H "Authorization: Bearer xxx"
```

### Docker Compose

```yaml
# ~/ai-stack/docker-compose.yml
services:
  new-api:
    image: calciumion/new-api:latest
    ports:
      - "127.0.0.1:3000:3000"   # 只绑 localhost
    environment:
      # 不设 SQL_DSN，new-api 默认使用 SQLite（零外部依赖）
      # 关键：上游请求走 VPS Tinyproxy
      HTTPS_PROXY: http://10.8.0.1:8888
      HTTP_PROXY: http://10.8.0.1:8888
      NO_PROXY: localhost,127.0.0.1,openwebui
    volumes:
      - ./data/new-api:/data   # SQLite 数据持久化
    restart: unless-stopped

  openwebui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "0.0.0.0:3002:8080"     # Tailscale 可访问
    environment:
      # 不设 DATABASE_URL，Open WebUI 默认使用 SQLite
      OPENAI_API_BASE_URL: http://new-api:3000/v1
      OPENAI_API_KEY: ${SWL_API_KEY}
      WEBUI_SECRET_KEY: ${WEBUI_SECRET}
      ENABLE_SIGNUP: "false"
    volumes:
      - ./data/openwebui:/app/backend/data
    depends_on:
      - new-api
    restart: unless-stopped

  caddy:
    image: caddy:2
    ports:
      - "127.0.0.1:443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./data/caddy:/data
    restart: unless-stopped
```

**端口绑定的设计**：

* `127.0.0.1:3000` (new-api)：只本机访问，Swallow Runtime 直连
* `0.0.0.0:3002` (Open WebUI)：Tailscale 内网可访问（Tailscale 会自动让 100.x.x.x 这个接口上的 0.0.0.0 绑定可达）
* `127.0.0.1:443` (Caddy)：可选，如果你想在 Tailscale 里用 HTTPS 访问

> **遥测说明**：推理遥测（token usage、route health、latency）由 Swallow 自建层承担——HTTPExecutor 从每次 API 响应的 `usage` 字段捕获真实 token 数据，写入 event log，由 Meta-Optimizer 消费。不依赖 TensorZero 或 PostgreSQL。

如果想统一走 HTTPS，把 Open WebUI 改成 `127.0.0.1:3002`，Caddy 反代到它，然后 Caddy 绑 `0.0.0.0:443`。Tailscale 配合 MagicDNS 可以直接给你签证书（`tailscale cert`）。

> **未来扩展**：如需引入 TensorZero（A/B 实验框架）或 PostgreSQL（pgvector 向量检索），在对应 phase 时单独添加 service 即可，不影响当前最小栈。

## Swallow Runtime 配置

```yaml
# ~/.swallow/config.yaml
api_base: http://localhost:3000/v1
api_key: <new-api-generated-key>

routes:
  - pattern: "code|编程|debug"
    channel: claude-sonnet
  - pattern: "中文|翻译|长文"
    channel: deepseek
  - pattern: "快分类|抽取"
    channel: gpt-4o-mini
  - pattern: "embedding"
    channel: voyage-3
  - pattern: "rerank"
    channel: cohere-rerank
  # 本地分支预留，现阶段 fallback 到远程
  - pattern: "sensitive|隐私"
    channel: claude-sonnet  # TODO: Mac 阶段改为 localhost-qwen
```

## 验证清单

部署完按这个顺序验证：

1. `ping 10.8.0.1` → WG 通了
2. `curl -x http://10.8.0.1:8888 https://ifconfig.me` → 返回 VPS 的 IP（证明出口生效）
3. `docker compose up -d` + `docker compose logs -f new-api` → 看到 new-api 启动
4. 在 new-api 面板（`localhost:3000`）配一个 OpenAI 渠道，点"测试" → 通过
5. 在工作站浏览器打开 `localhost:3002` → Open WebUI 能用
6. 手机装 Tailscale，加入 Tailnet → 手机浏览器打开 `http://100.x.x.10:3002` → 能用
7. `swl ask "test"` → 看到回复，`swl doctor` 报告 new-api 端点状态正常

## 几个容易踩的坑

**1. 课题组网络 UDP 被封**

少数严格的校园网/所内网会封 UDP 出站。先测：

```bash
nc -u -v vps-ip 51820
```

如果不通，WireGuard 用不了。备选：用 `wstunnel` 或 `udp2raw` 把 WG 的 UDP 包裹在 TCP 里，再不行就换 shadowsocks/v2ray 这类 TCP-native 的代理方案。

**2. new-api 容器出不去**

Docker 容器里的 `10.8.0.1` 能不能到达取决于网络模式。默认 bridge 模式下，容器访问宿主的 `10.8.0.1` 一般没问题，如果不通可以：

* 方案 A：`network_mode: host`（简单粗暴，容器直接用宿主网络栈）
* 方案 B：把 WG 接口加到 Docker 的默认桥接里

实测走一遍，有问题再调。

**3. Tailscale 和 WireGuard 路由冲突**

都是 WG 协议，但走不同接口（`tailscale0` vs `wg0`）和不同网段（`100.x.x.x` vs `10.8.x.x`），正常情况下不冲突。如果出现奇怪的路由问题，`ip route show` 看下路由表。

**4. Open WebUI 首次访问要创建管理员**

第一次打开 `3002` 端口，会让你注册第一个账号——**这个账号是管理员**。注册完立刻在 .env 里设 `ENABLE_SIGNUP=false` 或 `DEFAULT_USER_ROLE=pending`，防止别人扫到后注册。

**5. ~~pgvector 扩展手动开启~~**

> 已移除 PostgreSQL 依赖，此步骤不再需要。new-api 和 Open WebUI 均使用 SQLite。如未来引入 PostgreSQL（如 TensorZero 或向量检索），届时再配置。

---
