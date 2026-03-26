# SSH Setup — Access from Second Laptop

## 1. Enable OpenSSH Server on This Machine (Windows 11)

```powershell
# Run as Administrator
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# Start and enable the service
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
```

## 2. Allow SSH Through Firewall

```powershell
# Run as Administrator
New-NetFirewallRule -Name "OpenSSH-Server" -DisplayName "OpenSSH Server (sshd)" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

## 3. Generate SSH Key on Second Laptop

On the second laptop, open a terminal:

```bash
ssh-keygen -t ed25519 -C "second-laptop"
# Press Enter for default path, set a passphrase if desired
```

## 4. Copy Public Key to This Machine

From the second laptop:

```bash
# Replace <THIS_PC_IP> with this machine's local IP (run ipconfig on this PC)
ssh-copy-id Shaaban@<THIS_PC_IP>

# Or manually: copy the content of ~/.ssh/id_ed25519.pub
# and append it to C:\Users\Shaaban\.ssh\authorized_keys on this machine
```

## 5. Connect from Second Laptop

```bash
# SSH into this machine
ssh Shaaban@<THIS_PC_IP>

# Forward PostgreSQL port (access DB from second laptop)
ssh -L 5432:localhost:5432 Shaaban@<THIS_PC_IP>
# Now the second laptop can connect to PostgreSQL at localhost:5432
```

## 6. Find This Machine's IP

```powershell
# Run on this machine
ipconfig | findstr "IPv4"
# Use the local network IP (e.g., 192.168.x.x)
```

## 7. VS Code Remote (Optional)

Install "Remote - SSH" extension in VS Code on the second laptop:
1. Ctrl+Shift+P > "Remote-SSH: Connect to Host"
2. Enter: `Shaaban@<THIS_PC_IP>`
3. Opens the full project remotely with all extensions
