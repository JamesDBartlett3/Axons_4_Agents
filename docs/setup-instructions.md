# Setup Instructions

This guide walks you through setting up the Claude Memory Graph System from scratch. Follow each step in order.

## Prerequisites

Before starting, ensure you have:

- **Windows 10 (version 2004+) or Windows 11**
- **Administrator access** to your machine
- **~2GB free disk space** for WSL and Memgraph
- **Internet connection** for downloading packages

## Step 1: Install WSL2 with Ubuntu

If you don't already have WSL2 with Ubuntu installed:

### 1.1 Enable WSL

Open **PowerShell as Administrator** and run:

```powershell
wsl --install -d Ubuntu
```

This will:
- Enable WSL feature
- Enable Virtual Machine Platform
- Download and install Ubuntu

**You may need to restart your computer.**

### 1.2 Complete Ubuntu Setup

After restart, Ubuntu will launch automatically. If not, search for "Ubuntu" in the Start menu.

1. Wait for installation to complete
2. Create a username when prompted (this is your Linux username)
3. Create a password when prompted (you'll need this for `sudo` commands)

### 1.3 Verify WSL2

Open PowerShell and run:

```powershell
wsl --list --verbose
```

You should see:
```
  NAME      STATE           VERSION
* Ubuntu    Running         2
```

If VERSION shows 1, upgrade it:
```powershell
wsl --set-version Ubuntu 2
```

## Step 2: Enable systemd in WSL

Systemd is required for managing the Memgraph service.

### 2.1 Open Ubuntu Terminal

Search for "Ubuntu" in the Start menu and open it.

### 2.2 Edit WSL Configuration

Run:
```bash
sudo nano /etc/wsl.conf
```

Enter your password when prompted.

### 2.3 Add systemd Configuration

Add the following lines to the file:
```ini
[boot]
systemd=true
```

### 2.4 Save and Exit

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### 2.5 Restart WSL

In PowerShell (not Ubuntu), run:
```powershell
wsl --shutdown
```

Then reopen Ubuntu from the Start menu.

### 2.6 Verify systemd

In Ubuntu, run:
```bash
systemctl --version
```

You should see version information (not an error).

## Step 3: Install Memgraph

### 3.1 Download Memgraph

In Ubuntu terminal, run:

```bash
wget https://download.memgraph.com/memgraph/v3.7.0/ubuntu-24.04/memgraph_3.7.0-1_amd64.deb -O /tmp/memgraph.deb
```

**Note:** If you have a different Ubuntu version, check [Memgraph Downloads](https://memgraph.com/docs/getting-started/install-memgraph/direct-download-links) for the correct package URL. To check your version:
```bash
cat /etc/os-release | grep VERSION_ID
```

### 3.2 Install the Package

```bash
sudo dpkg -i /tmp/memgraph.deb
```

If you see dependency errors, run:
```bash
sudo apt-get install -f -y
```

Then retry the dpkg command.

### 3.3 Start Memgraph

```bash
sudo systemctl start memgraph
```

### 3.4 Verify Installation

```bash
sudo systemctl status memgraph
```

You should see `Active: active (running)`.

### 3.5 Enable Auto-Start

```bash
sudo systemctl enable memgraph
```

This makes Memgraph start automatically when Ubuntu starts.

## Step 4: Configure Windows Auto-Start

To make WSL (and thus Memgraph) start when Windows boots:

### 4.1 Open PowerShell as Administrator

Right-click the Start button → "Windows Terminal (Admin)" or "PowerShell (Admin)"

### 4.2 Create Scheduled Task

Copy and paste this entire block:

```powershell
$action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d Ubuntu -- sleep infinity"
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest
Register-ScheduledTask -TaskName "StartWSLUbuntu" -Action $action -Trigger $trigger -Settings $settings -Principal $principal
```

### 4.3 Verify Task Creation

```powershell
Get-ScheduledTask -TaskName "StartWSLUbuntu"
```

You should see the task listed with status "Ready".

### 4.4 Test the Task (Optional)

To test without rebooting:
```powershell
Start-ScheduledTask -TaskName "StartWSLUbuntu"
```

## Step 5: Install Python Dependencies

### 5.1 Verify Python Installation

In PowerShell (regular, not Admin):
```powershell
python --version
```

You need Python 3.10 or higher. If not installed, download from [python.org](https://www.python.org/downloads/).

### 5.2 Install neo4j Driver

```powershell
pip install neo4j
```

## Step 6: Set Up the Memory System Files

### 6.1 Create Directory

Choose where you want the memory system files. For example:

```powershell
mkdir C:\Users\$env:USERNAME\memory_graph
```

### 6.2 Copy Source Files

Copy the following files from the `src/` directory of this documentation to your chosen location:

- `schema.cypher` - Database schema
- `memory_client.py` - Python client library
- `test_memory_system.py` - Test suite
- `directory.md` - Node directory template

### 6.3 Verify File Structure

Your directory should look like:
```
memory_graph/
├── schema.cypher
├── memory_client.py
├── test_memory_system.py
└── directory.md
```

## Step 7: Initialize and Test

### 7.1 Verify Memgraph is Running

In PowerShell:
```powershell
Test-NetConnection -ComputerName localhost -Port 7687
```

`TcpTestSucceeded` should be `True`.

### 7.2 Run Tests

Navigate to your memory_graph directory and run:
```powershell
cd C:\Users\$env:USERNAME\memory_graph
python test_memory_system.py
```

You should see:
```
============================================================
Memory Graph System Test Suite
============================================================
Testing connection to Memgraph...
  Connection successful!

Initializing schema...
  Schema initialized!

Testing memory creation...
  Created memory: [uuid]
  Retrieved memory: User preference for Memgraph database

Testing relationships...
  Created memory relationship
  Found X related memories
  Found X memories with 'architecture' concept

Testing goals and questions...
  Created goal: [uuid]
  Created question: [uuid]
  Found X active goals
  Found X open questions

Testing directory export...
  Generated directory markdown:
  ...
  Saved to [path]\directory.md

============================================================
Test Results Summary
============================================================
  connection: PASS
  schema: PASS
  memory: PASS
  relationships: PASS
  goals_questions: PASS
  directory: PASS

All tests passed!
```

### 7.3 Clear Test Data (Optional)

If you want to start fresh after testing, uncomment the cleanup line in `test_memory_system.py` or run in Python:

```python
from memory_client import MemoryGraphClient

with MemoryGraphClient() as client:
    client._run_write("MATCH (n) DETACH DELETE n")
```

## Step 8: Verify Auto-Start (Optional)

To fully verify the auto-start setup:

1. **Restart your computer**

2. **Wait 30 seconds** after login for services to start

3. **Open PowerShell** and run:
   ```powershell
   wsl --list --running
   ```
   Ubuntu should be listed.

4. **Test Memgraph connection**:
   ```powershell
   Test-NetConnection -ComputerName localhost -Port 7687
   ```
   Should succeed.

## Troubleshooting

### "Cannot connect to Memgraph"

1. Check if WSL is running:
   ```powershell
   wsl --list --running
   ```
   If Ubuntu isn't listed, start it:
   ```powershell
   wsl -d Ubuntu
   ```

2. Check if Memgraph is running (in Ubuntu):
   ```bash
   sudo systemctl status memgraph
   ```
   If not running:
   ```bash
   sudo systemctl start memgraph
   ```

### "WSL not starting automatically"

1. Verify the scheduled task exists:
   ```powershell
   Get-ScheduledTask -TaskName "StartWSLUbuntu"
   ```

2. Check Task Scheduler for errors:
   - Open Task Scheduler (taskschd.msc)
   - Find "StartWSLUbuntu" in Task Scheduler Library
   - Check the History tab for errors

3. Try recreating the task (delete first if exists):
   ```powershell
   Unregister-ScheduledTask -TaskName "StartWSLUbuntu" -Confirm:$false
   ```
   Then repeat Step 4.

### "Permission denied" errors in WSL

Make sure you're using `sudo` for system commands:
```bash
sudo systemctl start memgraph
```

### "Package not found" when installing Memgraph

Your Ubuntu version may differ. Check your version:
```bash
cat /etc/os-release | grep VERSION_ID
```

Then find the matching package at [Memgraph Downloads](https://memgraph.com/docs/getting-started/install-memgraph/direct-download-links).

### Tests fail with import errors

Make sure the neo4j package is installed:
```powershell
pip install neo4j
```

And that you're in the correct directory when running tests.

## Summary

After completing this setup, you have:

1. **WSL2 with Ubuntu** running systemd
2. **Memgraph** installed and running as a service
3. **Auto-start** configured so everything starts on Windows boot
4. **Python client** ready for storing and querying memories
5. **Test suite** passing, confirming everything works

The memory system is now ready for use. See [Usage Guide](./usage-guide.md) for how to use it.
