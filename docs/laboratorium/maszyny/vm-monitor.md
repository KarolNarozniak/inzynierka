# VM-Monitor

## Rola
- Ubuntu Server 26.04.1 LTS.
- Centralne logi, Zeek/PCAP i analiza.
- Interfejs NAT do administracji SSH oraz interfejs badawczy strefy Monitoring.

## Stan sieciowy odczytany 2026-09-27

Komenda wykonana z hosta:

```powershell
ssh -o BatchMode=yes vmmonitor@192.168.234.149 "hostname; grep PRETTY_NAME /etc/os-release; ip -br address; ip route; systemctl is-active ssh"
```

Wynik:

```text
vm-monitor
PRETTY_NAME="Ubuntu 26.04.1 LTS"
lo               UNKNOWN        127.0.0.1/8 ::1/128
ens33            UP             192.168.234.149/24 metric 100 fe80::20c:29ff:fe96:4fe1/64
ens37            UP             10.10.40.10/24 fe80::20c:29ff:fe96:4feb/64
default via 10.10.40.1 dev ens37 proto static
default via 192.168.234.2 dev ens33 proto dhcp src 192.168.234.149 metric 100
10.10.40.0/24 dev ens37 proto kernel scope link src 10.10.40.10
192.168.234.0/24 dev ens33 proto kernel scope link src 192.168.234.149 metric 100
192.168.234.2 dev ens33 proto dhcp scope link src 192.168.234.149 metric 100
active
```

## Uwagi
- SSH kluczem dziala.
- Aktualna trasa domyslna prowadzi przez `10.10.40.1`; DHCP NAT nie instaluje tras ani DNS.
- NAT `ens33` pozostaje bezposrednim dostepem administracyjnym SSH.

## Operacje wykonane 2026-09-27

Plan: ustawic wysoka metryke dla trasy domyslnej przez przyszla brame OPNsense, aby podczas konfiguracji ruch wychodzacy szedl przez NAT.

Wykonana komenda:

```powershell
ssh -o BatchMode=yes vmmonitor@192.168.234.149 "sudo cp /etc/netplan/00-installer-config.yaml /etc/netplan/00-installer-config.yaml.bak-20260927 && sudo sed -i '/via: 10.10.40.1/a\        metric: 20100' /etc/netplan/00-installer-config.yaml && sudo netplan apply"
```

Wynik:

```text
ens33 UP 192.168.234.149/24
ens37 UP 10.10.40.10/24
default via 192.168.234.2 dev ens33 metric 100
default via 10.10.40.1 dev ens37 metric 20100
```

Pliki zmienione na VM:
- `/etc/netplan/00-installer-config.yaml`
- `/etc/netplan/00-installer-config.yaml.bak-20260927`

Restart uslug: `netplan apply`.

Test lacznosci:

```text
NAT gateway 192.168.234.2: OK
Internet 1.1.1.1: OK
DNS archive.ubuntu.com: OK
```

## Operacje wykonane 2026-09-27 - usuniecie NAT jako trasy domyslnej

Plan: skierowac publiczny ruch Monitoring przez OPNsense i pozostawic NAT tylko do administracyjnego SSH.

Wdrozenie: zastosowano `/etc/netplan/99-lab-egress.yaml`; poprzedni `00-installer-config.yaml` zachowano jako `.bak-egress-20260927`. DHCP NAT ma `use-routes: false`, `use-dns: false`, a default route i DNS prowadza przez `10.10.40.1`.

Wynik zweryfikowany:

```text
1.1.1.1 -> via 10.10.40.1 dev ens37
192.168.234.1 -> directly via ens33
DNS api.openai.com resolves via 10.10.40.1
```

Pliki zmienione na VM: `/etc/netplan/99-lab-egress.yaml`, `/etc/netplan/00-installer-config.yaml.bak-egress-20260927`, `/etc/netplan/99-lab-egress.yaml.bak-nat-disable-20260927`.

Restart uslug: `netplan generate`, `netplan apply`; reboot nie byl wymagany.

## Telemetria auditd / Fluent Bit / Zeek 2026-09-28

Plan: uruchomic lokalny collector auditd, odbiornik Fluent Forward dostepny wylacznie pod adresem Monitoring `10.10.40.10:24224` i Zeek do analizy plikow PCAP offline.

Wykonane operacje: zainstalowano auditd `1:4.1.2-1ubuntu0.1`, Fluent Bit `5.1.2` i `zeek-8.0-core` `1:8.0.10-0` z lokalnych paczek pobranych przez VM-Gateway. Wdrozono konfiguracje Fluent Bit i reguly auditd, sprawdzono Fluent Bit przez `--dry-run`, a Zeek uruchomiono na przykladowym PCAP z oficjalnego quickstartu Zeek.

Pliki zmienione na VM:
- `/etc/fluent-bit/fluent-bit.conf` (kopia poprzedniej konfiguracji: `.bak-pre-lab-20260928`)
- `/etc/audit/rules.d/99-lab.rules`
- `/var/log/lab-telemetry/monitor-local.jsonl`
- stan Fluent Bit w `/var/lib/fluent-bit/`
- paczka testowa `/tmp/zeek-quickstart.pcap` i wyniki `/tmp/zeek-quickstart-output/{conn,http,weird,...}.log`

Wynik Fluent Bit: `auditd.service` i `fluent-bit.service` active; listener TCP widoczny tylko na `10.10.40.10:24224`. Lokalna syntetyczna proba Forward zostala zapisana jako tag `received.telemetry.selftest`; nie jest to dowod odbioru z innej strefy. Plik `forwarded.jsonl` ograniczono rotacja do 100 MB i 7 archiwow.

Wynik Zeek: wersja `8.0.10`; oficjalny PCAP quickstart SHA-256 `090244c27e3c2ab6f4d9f63a11076ae9bd887ee67b28bfd9d1e62293065318a8`; offline run utworzyl `conn.log` (2 wpisy), `http.log` (2 wpisy) oraz `weird.log` (1 `unknown_HTTP_method`). To weryfikuje przetwarzanie przykladowego pliku, nie capture ruchu laboratorium.

Restart uslug: uruchomiono `auditd.service` i `fluent-bit.service`; Zeek nie jest usluga stalej pracy i uruchomiono go jednorazowo na PCAP.

## Weryfikacja odbioru F-04-A/G/T 2026-09-28

Plan: po informacji uzytkownika o dodaniu regul sprawdzic trzy sciezki zrodlowe i potwierdzic zapis roznych tagow oraz zdarzen syntetycznych.

Wynik:
- Odbiornik pozostaje zbindowany na `10.10.40.10:24224`; TCP test z Agent, Gateway i Target zwrocil OPEN.
- `/var/log/lab-telemetry/forwarded.jsonl` zawieral 939 rekordow w odczycie 2026-09-28 ok. 00:47 czasu VM-Agent; liczba zmienia sie wraz z naplywem logow.
- Potwierdzono znaczniki `LAB_TELEMETRY_F04_AGENT_20260928_01`, `LAB_TELEMETRY_F04_GATEWAY_20260928_01` i `LAB_TELEMETRY_F04_TARGET_20260928_01`, kazdy w odpowiadajacych tagach audit i auth.
- `received.lab.gateway.control`: 22 rekordy; `received.lab.target.canary`: 4 rekordy, w tym `SC06-KILO-ALLOW-001`.
- Wczesniejsze bufory senderow byly opróżniane po dodaniu regul; Target zrestartowano jednokrotnie, a jego starszy chunk canary zakonczyl sie sukcesem.

Pliki zmienione na VM: Fluent Bit dopisal logi do `forwarded.jsonl`; plik rotowany przy 100 MB, przechowywanych maksymalnie 7 rotacji.

Restart uslug: brak na Monitor w tym tescie; `auditd.service` i `fluent-bit.service` active.

Otwarte pytanie: wykonac i przeanalizowac PCAP z rzeczywistego ruchu przechwyconego na OPNsense. Test Zeek byl na sample PCAP.

## PCAP-MCP smoke run 2026-10-10

Podczas dwoch capture'ow OPNsense odebrano przez Fluent Bit rekordy Gateway dla `PCAP-MCP-20261010-c2639542` (policy allow, execution attempt, success; source `10.10.10.10`). Surowe PCAP pobrano przez SSH z OPNsense do VM-Agent, a nastepnie przeniesiono na Monitor. Zeek `8.0.10` utworzyl `conn.log`/`http.log` w trzech osobnych katalogach:

| Interfejs | Hash SHA-256 | conn | http |
| --- | --- | ---: | ---: |
| LAN/em1 | `a154f16bddb831343f93ddba0a6f2bae8cf3c42e15cabe92bbb0807c7035ed7d` | 3 | 3 |
| OPT1/em2 | `746cea3aedd7fba1a09bbd1609e7202acb1731245e8929cc21297f888aa5b6e5` | 2 | 4 |
| OPT2/em3 | `b320cb7b29ac9455e51d6d5c878e1ec08c9b34f7e32982f7738db3a07672915d` | 2 | 4 |

`weird.log` nie powstal dla tych plikow. Odbiornik i Fluent Bit pozostaly active; eksport ZIP przez GUI OPNsense nadal wymaga diagnostyki.

## SC-05 rep01 — Gateway PCAP i Zeek — 2026-10-11

Na potrzeby `SC05-KILO-REP01-20261011` przeniesiono z VM-Gateway capture z `ens37` do `/var/log/lab-telemetry/pcap/SC05-KILO-REP01-20261011.pcap` (owner `vmmonitor:vmmonitor`, mode `0600`). SHA-256: `39efb2484c7b9e2ebcbfdaf85bca0fb0b34f147cf398e5892b10077dbd4c49ee`. Capture: 132 pakiety, 0 drop; filtr TCP/8001 i TCP/8000. To punkt przechwytywania na Gateway, nie na OPNsense.

Zeek `8.0.10` początkowo ostrzegł o checksum offload; pierwszy wynik odrzucono. PCAP przetworzono ponownie offline z `-C` w `/var/log/lab-telemetry/zeek/SC05-KILO-REP01-20261011/`: 5 rekordów `conn.log`, 6 `http.log`, `weird.log` nie powstał. Zobaczono połączenia Agent→Gateway TCP/8001 oraz Gateway→Target TCP/8000; HTTP log zawierał POST `/mcp` (w tym 200/202). Surowy PCAP oraz zredagowane logi Zeek pozostają poza repozytorium.

SC-05 rep01: Gateway decyzja allow/attempt/success, Target obsłużył `CallToolRequest`; receiver canary bez wpisu. Run ID jest obecny w Gateway, ale nie w PCAP/Target journal, dlatego powiązanie sieciowe/Target jest czasowo-adresowe, nie jawnie run-ID. Restart usług: brak.

## SC-05 rep02 — Gateway PCAP i Zeek — 2026-10-11

PCAP `/var/log/lab-telemetry/pcap/SC05-KILO-REP02-20261011.pcap`, owner `vmmonitor:vmmonitor`, mode `0600`, SHA-256 `e8d0bfc587555033316875eab86afa7c1505a430d1e34f0943c3505f278ed3af`. Capture z Gateway `ens37`: filtr TCP/8001 i TCP/8000, 137 pakietów, 0 drop. Zeek `8.0.10` przetworzył offline z `-C`: 5 `conn.log`, 6 `http.log`, brak `weird.log`; wyjście w `/var/log/lab-telemetry/zeek/SC05-KILO-REP02-20261011/`. Ruch pokazał Agent→Gateway `/mcp` TCP/8001 i Gateway→Target `/mcp` TCP/8000. Receiver canary bez eventu dla rep02. Run ID nie jest jawnie w Target journal/PCAP; korelacja tych źródeł jest po adresie/czasie i Gateway request. Restart usług: brak.
SC-05 rep02: PCAP archiwalny `/var/log/lab-telemetry/pcap/SC05-KILO-REP02-20261011.pcap`, SHA-256 `e8d0bfc587555033316875eab86afa7c1505a430d1e34f0943c3505f278ed3af`, 137 pakietów/0 drop; Zeek 8.0.10 `-C`: 5 conn, 6 HTTP, brak weird. Rep03: `/var/log/lab-telemetry/pcap/SC05-KILO-REP03-20261011.pcap`, SHA-256 `42d8152ae0fefbd7f0b68b3ff47e27fef47af97be7843d459fbdcd535316867a`, 172 pakiety/0 drop; Zeek `-C`: 5 conn, 6 HTTP, brak weird. W obu capture ruch widoczny na Gateway `ens37`, w tym Agent→Gateway i Gateway→Target; run ID nie jest przenoszony do Target journal/PCAP. Artefakty PCAP/Zeek są poza repozytorium.
SC-06-D rep02 PCAP `/var/log/lab-telemetry/pcap/SC06D-REP02-20261011.pcap`, SHA-256 `de4a827af32053b5bde477239278fa1ee13c85d88abcf619b95a570a80c2a8a8`, 52 pakiety; Zeek 8.0.10 `-C` wygenerował 2 `conn.log` wpisy (`OTH`), brak HTTP/weird. Nie widać requestu MCP do Gateway/Target; capture zapisano poza repozytorium.
SC-06-D rep03: nie zapisano PCAP ani Zeek do archiwum, ponieważ capture trwał przez długie okno (309 pakietów) i zawierał wiele niezwiązanych HTTP sesji bez korelacji run ID. Tymczasowy PCAP i logi Zeek usunięto; nie wykorzystuje się ich jako dowodu przebiegu.
SC-06-A rep01: PCAP `/var/log/lab-telemetry/pcap/SC06A-REP01-20261011.pcap`, SHA-256 `79d4771c675bbaaec0e30c9526f06a92b1a6b65cb943ce8afaa230741c0f730e`, 121 pakietów/0 drop. Zeek 8.0.10 (`-C`) w `/var/log/lab-telemetry/zeek/SC06A-REP01-20261011/`: 5 conn, 6 HTTP, brak weird. W połączeniu z Gateway allow/attempt/success i pojedynczym receiver record potwierdza dodatnią kontrolę rep01. Pliki PCAP/Zeek poza repozytorium.
SC-06-A rep02: PCAP `/var/log/lab-telemetry/pcap/SC06A-REP02-20261011.pcap`, SHA-256 `024b995cd7767704273af4b7967b1a5dd4366fd1f10a1e094f6f0f5ec6621035`, 96 pakietów/0 drop. Zeek 8.0.10 (`-C`) w `/var/log/lab-telemetry/zeek/SC06A-REP02-20261011/`: 5 conn, 6 HTTP, brak weird. Gateway/Target records odebrano centralnie; jeden canary receipt potwierdza dodatnią kontrolę rep02. Pliki PCAP/Zeek poza repozytorium.
SC-06-A rep03: PCAP `/var/log/lab-telemetry/pcap/SC06A-REP03-20261011.pcap`, SHA-256 `dc9652467e93f509c66fa50bb66236fee653a01d4f3e05a31ca80817c8e97779`, 106 pakietów/0 drop. Zeek 8.0.10 (`-C`) w `/var/log/lab-telemetry/zeek/SC06A-REP03-20261011/`: 5 conn, 6 HTTP, brak weird. Gateway/Target records odebrano centralnie; jeden receiver record potwierdza dodatnią kontrolę rep03. PCAP/Zeek poza repozytorium.
