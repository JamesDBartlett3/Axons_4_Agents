# Infrastructure

This document describes the infrastructure components and how they interact.

## Components Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              WINDOWS HOST                                │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  Task Scheduler                                                     │ │
│  │  - Task: "StartWSLUbuntu"                                          │ │
│  │  - Trigger: At system startup                                      │ │
│  │  - Action: wsl -d Ubuntu -- sleep infinity                         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│                                    │ Starts                              │
│                                    ▼                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  WSL2 - Ubuntu                                                      │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │  systemd                                                      │  │ │
│  │  │  - Manages services                                           │  │ │
│  │  │  - Starts memgraph.service on boot                           │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  │                                    │                                │ │
│  │                                    │ Manages                        │ │
│  │                                    ▼                                │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │  Memgraph Database                                            │  │ │
│  │  │  - Port: 7687 (Bolt protocol)                                │  │ │
│  │  │  - Data: /var/lib/memgraph/                                  │  │ │
│  │  │  - Config: /etc/memgraph/memgraph.conf                       │  │ │
│  │  │  - Logs: journalctl -u memgraph                              │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│                        localhost:7687 (Bolt)                            │
│                                    │                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  Python Application                                                 │ │
│  │  - neo4j driver connects to localhost:7687                         │ │
│  │  - memory_client.py provides API                                   │ │
│  │  - Runs on Windows Python                                          │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## WSL2 Configuration

### Location
WSL configuration is stored in `/etc/wsl.conf` inside the Ubuntu distribution.

### Required Settings
```ini
[boot]
systemd=true
```

This enables systemd, which is required for managing the Memgraph service.

### Verifying WSL2
```powershell
wsl --list --verbose
```

Output should show Ubuntu with VERSION = 2:
```
  NAME      STATE           VERSION
* Ubuntu    Running         2
```

## Memgraph Database

### Installation Location
- Binary: `/usr/lib/memgraph/memgraph`
- Data directory: `/var/lib/memgraph/`
- Configuration: `/etc/memgraph/memgraph.conf`
- Service file: `/lib/systemd/system/memgraph.service`

### Service Management

**Check status:**
```bash
sudo systemctl status memgraph
```

**Start service:**
```bash
sudo systemctl start memgraph
```

**Stop service:**
```bash
sudo systemctl stop memgraph
```

**Enable auto-start:**
```bash
sudo systemctl enable memgraph
```

**View logs:**
```bash
sudo journalctl -u memgraph
```

**View recent logs:**
```bash
sudo journalctl -u memgraph -n 50
```

### Default Configuration

Key settings in `/etc/memgraph/memgraph.conf`:

| Setting | Default | Description |
|---------|---------|-------------|
| `--bolt-port` | 7687 | Port for Bolt protocol connections |
| `--data-directory` | /var/lib/memgraph | Where data is persisted |
| `--log-level` | WARNING | Logging verbosity |
| `--memory-limit` | (system dependent) | Maximum RAM usage |

### Memory Usage

- **Idle**: ~100-200 MB
- **With data**: Scales with graph size
- **Recommendation**: Ensure at least 512 MB available for Memgraph

### Persistence

Memgraph is an in-memory database with write-ahead logging (WAL) for persistence:
- Data is stored in RAM for fast access
- Changes are written to WAL for durability
- On restart, data is recovered from WAL
- Data directory: `/var/lib/memgraph/`

## Network Configuration

### Port Mapping

WSL2 uses a virtual network adapter. By default:
- Services in WSL bind to `0.0.0.0`
- Windows can access them via `localhost`

Memgraph listens on port **7687** (Bolt protocol).

### Verifying Connectivity

From Windows PowerShell:
```powershell
Test-NetConnection -ComputerName localhost -Port 7687
```

From WSL:
```bash
nc -zv localhost 7687
```

### Firewall Considerations

Windows Firewall typically allows localhost traffic. If you have issues:
1. Check Windows Firewall isn't blocking port 7687
2. Verify WSL networking is working: `wsl hostname -I`

## Python Environment

### Requirements
- Python 3.10 or higher
- neo4j driver package

### Installation
```bash
pip install neo4j
```

### Connection String
```python
uri = "bolt://localhost:7687"
```

No authentication is required by default (Memgraph ships without auth enabled).

## Windows Task Scheduler

### Task Details

| Property | Value |
|----------|-------|
| Name | StartWSLUbuntu |
| Trigger | At startup |
| Action | `wsl.exe -d Ubuntu -- sleep infinity` |
| Run as | Current user |
| Run level | Highest privileges |

### Why `sleep infinity`?

WSL terminates when all processes exit. Running `sleep infinity` keeps a process alive indefinitely, which:
1. Keeps the WSL instance running
2. Allows systemd to continue managing services
3. Ensures Memgraph stays accessible

### Verifying the Task

**PowerShell:**
```powershell
Get-ScheduledTask -TaskName "StartWSLUbuntu"
```

**Task Scheduler GUI:**
1. Open Task Scheduler (taskschd.msc)
2. Navigate to Task Scheduler Library
3. Find "StartWSLUbuntu"

### Manual Testing

To test without rebooting:
```powershell
Start-ScheduledTask -TaskName "StartWSLUbuntu"
```

## File Locations Summary

| Component | Location |
|-----------|----------|
| WSL config | `/etc/wsl.conf` (in Ubuntu) |
| Memgraph binary | `/usr/lib/memgraph/memgraph` |
| Memgraph data | `/var/lib/memgraph/` |
| Memgraph config | `/etc/memgraph/memgraph.conf` |
| Memgraph service | `/lib/systemd/system/memgraph.service` |
| Python client | `memory_graph/memory_client.py` |
| Directory index | `memory_graph/directory.md` |

## Troubleshooting

### Memgraph won't start

1. Check if already running:
   ```bash
   sudo systemctl status memgraph
   ```

2. Check for port conflicts:
   ```bash
   sudo lsof -i :7687
   ```

3. Check logs:
   ```bash
   sudo journalctl -u memgraph -n 100
   ```

### Can't connect from Windows

1. Verify WSL is running:
   ```powershell
   wsl --list --running
   ```

2. Verify Memgraph is running:
   ```bash
   wsl -d Ubuntu -- sudo systemctl status memgraph
   ```

3. Test port connectivity:
   ```powershell
   Test-NetConnection -ComputerName localhost -Port 7687
   ```

### WSL not starting automatically

1. Verify task exists:
   ```powershell
   Get-ScheduledTask -TaskName "StartWSLUbuntu"
   ```

2. Check task history in Task Scheduler GUI

3. Run task manually to see errors:
   ```powershell
   Start-ScheduledTask -TaskName "StartWSLUbuntu"
   ```

### High memory usage

1. Check Memgraph memory:
   ```bash
   sudo systemctl status memgraph
   ```

2. Consider setting memory limit in `/etc/memgraph/memgraph.conf`:
   ```
   --memory-limit=1024
   ```
   (Value in MB)

3. Restart after config change:
   ```bash
   sudo systemctl restart memgraph
   ```
