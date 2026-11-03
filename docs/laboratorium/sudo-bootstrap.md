# Sudo bootstrap

Cel: tymczasowo wlaczyc bezhaslowe `sudo` dla uzytkownikow laboratoryjnych, aby mozna bylo wykonac zdalna konfiguracje systemu przez SSH.

Status: do wykonania recznie na kazdej VM, poniewaz obecnie `sudo` wymaga interaktywnego hasla.

## VM-Agent

```bash
echo 'vmagent ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/90-lab-vmagent-nopasswd
sudo chmod 440 /etc/sudoers.d/90-lab-vmagent-nopasswd
sudo visudo -cf /etc/sudoers.d/90-lab-vmagent-nopasswd
```

## VM-Gateway

```bash
echo 'vmgateway ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/90-lab-vmgateway-nopasswd
sudo chmod 440 /etc/sudoers.d/90-lab-vmgateway-nopasswd
sudo visudo -cf /etc/sudoers.d/90-lab-vmgateway-nopasswd
```

## VM-Target

```bash
echo 'vmtarget ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/90-lab-vmtarget-nopasswd
sudo chmod 440 /etc/sudoers.d/90-lab-vmtarget-nopasswd
sudo visudo -cf /etc/sudoers.d/90-lab-vmtarget-nopasswd
```

## VM-Monitor

```bash
echo 'vmmonitor ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/90-lab-vmmonitor-nopasswd
sudo chmod 440 /etc/sudoers.d/90-lab-vmmonitor-nopasswd
sudo visudo -cf /etc/sudoers.d/90-lab-vmmonitor-nopasswd
```

## Test z hosta po wykonaniu

```powershell
ssh vmagent@192.168.234.145 "sudo -n true && echo OK"
ssh vmgateway@192.168.234.148 "sudo -n true && echo OK"
ssh vmtarget@192.168.234.147 "sudo -n true && echo OK"
ssh vmmonitor@192.168.234.149 "sudo -n true && echo OK"
```

## Usuniecie po zakonczeniu konfiguracji

```bash
sudo rm -f /etc/sudoers.d/90-lab-*-nopasswd
```

Po usunieciu sprawdzic, ze `sudo -n true` zwraca blad wymagania uwierzytelnienia.
