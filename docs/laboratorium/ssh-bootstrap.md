# SSH bootstrap

Cel: jednorazowo dodac klucz publiczny hosta do maszyn Ubuntu, aby dalsza konfiguracje wykonywac zdalnie bez wpisywania hasel.

Nie zapisuj hasel w repozytorium. Klucz ponizej jest kluczem publicznym, nie sekretem.

## Klucz publiczny hosta

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOEG5r/hHYbqCGue7kurn9QaKnxR1PRYMrx4p0vmZSuD karon@PHANTEKS
```

## Komenda do wykonania na kazdej VM Ubuntu

Uruchom jako zalogowany uzytkownik danej maszyny: `vmagent`, `vmgateway`, `vmtarget` albo `vmmonitor`.

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
printf '%s\n' 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOEG5r/hHYbqCGue7kurn9QaKnxR1PRYMrx4p0vmZSuD karon@PHANTEKS' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

## Oczekiwany test po stronie hosta

```powershell
ssh vmagent@192.168.234.145 hostname
ssh vmgateway@192.168.234.148 hostname
ssh vmtarget@192.168.234.147 hostname
ssh vmmonitor@192.168.234.149 hostname
```

Po poprawnym tescie mozna rozpoczac zdalne odczytanie stanu maszyn i konfiguracje routingu/laboratorium.
