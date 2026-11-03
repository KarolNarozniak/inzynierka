# Telemetria laboratorium

Status: hosty Ubuntu i telemetryka pozostaja skonfigurowane; F-04-A/G/T ponownie przeszly test end-to-end po odtworzeniu OPNsense 2026-10-10. Rzeczywisty test MCP zostal przechwycony na LAN/OPT1/OPT2 i przetworzony przez Zeek na VM-Monitor. ZIP z GUI nadal zwraca blad; surowe pliki PCAP pobrano przez SSH.

## Zakres i architektura

- `auditd` rejestruje zdarzenia systemowe na VM-Agent, VM-Gateway, VM-Target i VM-Monitor.
- Fluent Bit wysyla wybrane lokalne logi z VM-Agent, VM-Gateway i VM-Target przez Fluent Forward TCP/24224 do `10.10.40.10` na VM-Monitor. Monitor odbiera dane i zapisuje je do lokalnych plikow; logow nie wysyla dalej.
- Zrodla aplikacyjne: `/var/log/lab-control/decisions.jsonl` na Gateway i `/var/log/lab-target/canary-received.jsonl` na Target, obok logow systemowych i auditd.
- PCAP: `VM-FW`/OPNsense Diagnostics > Packet Capture na interfejsach stref, przez ktore przechodzi badany ruch. PCAP jest eksportowany do analizy offline; nie zaklada sie mirroringu VMware ani widocznosci ruchu unicast na VM-Monitor.
- Zeek na VM-Monitor przetwarza wyeksportowane pliki PCAP offline. Wyniki Zeek sa przypisane do katalogu pojedynczego przebiegu, nie do wspolnego katalogu wynikowego.

## Przeplywy sieciowe

| ID | Interfejs OPNsense (ruch wchodzi) | Zrodlo | Cel | Protokol/port | Decyzja | Uzasadnienie |
| --- | --- | --- | --- | --- | --- | --- |
| F-04-A | LAN/AGENT | `10.10.10.10/32` | `10.10.40.10/32` | TCP/24224 | Pass, ponownie zweryfikowana 2026-10-10 | Fluent Bit z VM-Agent do Monitor |
| F-04-G | OPT1/SERVICES | `10.10.20.10/32` | `10.10.40.10/32` | TCP/24224 | Pass, ponownie zweryfikowana 2026-10-10 | Fluent Bit z VM-Gateway do Monitor |
| F-04-T | OPT2/TARGETS | `10.10.30.10/32` | `10.10.40.10/32` | TCP/24224 | Pass, ponownie zweryfikowana 2026-10-10 | Fluent Bit z VM-Target do Monitor |

Na Monitor odbiornik ma byc zwiazany tylko z `10.10.40.10:24224`. Nie dodawac F-04 dla ruchu przychodzacego z WAN ani dla calej podsieci zrodlowej. Reguly egzekwuje OPNsense na interfejsie zrodlowej strefy, nie na interfejsie Monitoring. F-04 byly potwierdzone 2026-09-28, a po resecie ponownie zweryfikowane 2026-10-10.

## Przygotowanie i weryfikacja PCAP

1. W OPNsense wybrac `Interfaces > Diagnostics > Packet capture`, wskazac interfejsy Agent/Services/Targets (lub konkretny interfejs dla danego testu), wlaczyc capture i zapisac PCAP z opisem identyfikatora przebiegu.
2. Pobierac capture bezposrednio z OPNsense i przenosic na VM-Monitor do katalogu danego run ID. Nie kopiowac PCAP do Git.
3. Przed analiza odnotowac SHA-256 pliku i uruchomic Zeek w trybie offline. Zapisac wersje Zeek, komende, wynik, nazwy logow oraz ich korelacje czasowa z identyfikatorem przebiegu.
4. Capture OPNsense potwierdza pakiety obserwowane na interfejsach OPNsense; sam brak pakietu w PCAP nie dowodzi, ze narzedzie nie probowalo wykonania. Koreluj z logami decyzji, auditd, logiem MCP i odbiornikiem canary.

## Zasady interpretacji

- Fluent Bit/auditd/Zeek sa zrodlami obserwacji, nie dowodem skutecznosci polityki same w sobie.
- Oddzielaj intencje modelu, wywolanie narzedzia, decyzje allow/ask/deny, probe wykonania i potwierdzony skutek.
- Uzywaj syntetycznych canary unikalnych dla przebiegu; nie przechowuj prawdziwych sekretow ani danych osobowych w logach lub PCAP.
- Przed zakonczeniem kazdej konfiguracji zapisz: plan, faktycznie wykonana komende, wynik, zmienione pliki na VM, restart uslug i otwarte pytania.

## Zmiany i testy

Konfiguracja hostow, odczytane wersje, komendy wykonane, wyniki, restarty i pytania sa dopisywane do dziennikow maszyn `maszyny/vm-*.md`. Wdrozone reguly F-04 i ich testy sa dopisywane do `opnsense-reguly-startowe.md` oraz `stan-maszyn.md`.

## Wdrozenie 2026-09-28

### Pakiety i stan uslug

| Komponent | Wersja | Maszyny | Stan |
| --- | --- | --- | --- |
| auditd | `1:4.1.2-1ubuntu0.1` | Agent, Gateway, Target, Monitor | active/enabled |
| Fluent Bit | `5.1.2` | Agent, Gateway, Target, Monitor | active/enabled |
| Zeek | `8.0.10` (`zeek-8.0-core`) | Monitor | zainstalowany; offline run sprawdzony |

Pakiety Ubuntu/Fluent Bit/Zeek pobrano i zweryfikowano przez APT na VM-Gateway (podpisane repozytoria i HTTPS), a nastepnie przeniesiono lokalnie na pozostale VM. Tymczasowe wpisy repozytoriow Fluent Bit/Zeek i klucze repozytoriow usunieto z Gateway po pobraniu; adresy archiwow Ubuntu na Gateway pozostawiono w HTTPS.

### Konfiguracja logow

- Konfiguracje bez sekretow i reguly auditd sa utrzymywane w `lab/telemetry/`.
- Fluent Bit na Monitor jest zbindowany tylko do `10.10.40.10:24224/tcp`; zapisy trafiaja do `/var/log/lab-telemetry/forwarded.jsonl` i `monitor-local.jsonl`. Rotacja: 100 MB, maks. 7 plikow.
- Agent wysyla auditd/auth; Gateway dodatkowo tailuje `/var/log/lab-control/decisions.jsonl`; Target dodatkowo tailuje `/var/log/lab-target/canary-received.jsonl`. Te dwa dzienniki JSONL sa czytane od poczatku, a logi systemowe od biezacej pozycji.
- Agent dodatkowo tailuje `/home/*/.local/state/lab-agent/local-mcp.jsonl` jako `lab.agent.local_mcp`; rekordy zawieraja run ID, UID, nazwe narzedzia, wynik i hash fixture, nie jej tresc.
- Weryfikacja Fluent Bit: `--dry-run` zakonczyl sie `configuration test is successful` na wszystkich VM. `auditctl -l` pokazal odpowiednio 3 reguly na Agent, 4 na Gateway, 5 na Target i 2 na Monitor.
- Receiver Monitor zapisuje lokalny syntetyczny wpis `received.telemetry.selftest`; jest to test procesu odbior/zapis na tej samej VM, a nie test miedzystrefowy.
- Stan poczatkowy przed dodaniem regul przez uzytkownika: Fluent Bit sendery byly active i retryowaly do `10.10.40.10:24224`, a polaczenia miedzystrefowe nie byly odbierane. Po dodaniu F-04-A/G/T wykonano testy opisane ponizej.

### Lokalny MCP/stdio i wstepny test ACL 2026-10-10

- Wdrozenie VM-Agent: `/opt/lab/agent-mcp/` z MCP SDK `1.30.0`, Pythonem `3.14.4`, lokalnym stdio serwerem i stala notatka syntetyczna. Serwer udostepnia `read_local_note`, `read_indirect_instruction` i `read_protected_canary`; nie przyjmuje sciezek od klienta i nie otwiera portu sieciowego.
- Konto administracyjne `vmagent` nie jest uzywane jako zadna z dwoch tozsamosci testowych. `agent-wide` nalezy do `lab-canary-readers`, a `agent-limited` nie; oba konta nie maja sudo/lxd/docker. Chroniony plik jest `root:lab-canary-readers`, mode `0640` i zawiera tylko syntetyczny token generowany dla przebiegu.
- `verify_local_mcp.py` uruchomiono pod oboma UID, przez klienta MCP SDK bez Kilo UI. Lokalna notatka i fixture posredniej instrukcji zwrocily sukces w obu kontach. Odczyt protected-canary byl dozwolony dla `agent-wide` i odmowiony dla `agent-limited`.
- Run ID: `LOCAL-MCP-26b6a97d9985` (wide) oraz `LOCAL-MCP-f65cebdf4039` (limited); probe chronionego zasobu uzyly odpowiednio sufiksu `-H2`. Auditd zarejestrowal `openat success=yes` dla wide i `success=no exit=-13 (EACCES)` dla limited. Fluent Bit przekazal lokalne wpisy JSONL i auditd do Monitora.
- Interpretacja jest ograniczona do testu akceptacyjnego MCP SDK/OS ACL. Nie jest to przebieg Kilo Code ani samodzielne potwierdzenie H2. Dla badan H2 trzeba skonfigurowac LiteLLM w obu profilach Kilo, zachowac te same prompty/polityki i powtorzyc probę z Kilo.

### Zeek i PCAP

- Zeek `8.0.10` przetworzyl offline oficjalny `quickstart.pcap` z dokumentacji Zeek; SHA-256: `090244c27e3c2ab6f4d9f63a11076ae9bd887ee67b28bfd9d1e62293065318a8`.
- Wynik: `conn.log` 2 wpisy, `http.log` 2 wpisy, `weird.log` zawiera 1 `unknown_HTTP_method`.
- To potwierdza instalacje i czytanie PCAP przez Zeek. Nie wykonano jeszcze capture na interfejsie VM-FW/OPNsense ani analizy rzeczywistego ruchu badawczego.

### Weryfikacja zdalnego odbioru 2026-09-28

Uzytkownik potwierdzil dodanie regul F-04-A/G/T. Test TCP/24224 z VM-Agent, VM-Gateway i VM-Target zwrocil OPEN; Fluent Bit sendery oraz auditd pozostaly active. Wygenerowano przez `sudo auditctl -m` unikalne znaczniki syntetyczne:

- `LAB_TELEMETRY_F04_AGENT_20260928_01`
- `LAB_TELEMETRY_F04_GATEWAY_20260928_01`
- `LAB_TELEMETRY_F04_TARGET_20260928_01`

Wszystkie trzy znaczniki odebrano w `/var/log/lab-telemetry/forwarded.jsonl` na Monitor: kazdy wystapil w tagach audit i auth swojego hosta. Zweryfikowano takze 22 wpisy `received.lab.gateway.control` z audytu policy proxy oraz 4 wpisy `received.lab.target.canary` z Target, w tym run `SC06-KILO-ALLOW-001`. Target mial starszy chunk w retry z dlugim backoffem; po restarcie `fluent-bit.service` na Target chunk zakonczyl sie `flush succeeded`, a receiver zapisal 4 wpisy canary.

Stan testu: potwierdza dostarczenie logow trzech VM przez OPNsense do odbiornika, a nie skutecznosc polityk badawczych. Wygenerowane znaczniki sa syntetycznymi zdarzeniami telemetrycznymi.

### Otwarte dzialania

1. Zdiagnozowac i naprawic endpoint ZIP OPNsense `/api/diagnostics/packet_capture/download/<jobid>`; do tego przebiegu uzyto scp surowych plikow z `/tmp/captures/`.
2. Ujednolicic lub jawnie normalizowac strefy czasowe w dowodach: odczyt `date -Is` pokazal VM-Agent `Europe/Warsaw` (UTC+02), a VM-Gateway/Target/Monitor `Etc/UTC`; wszystkie cztery raportowaly NTP synchronized. Syslog tekstowy nie zawsze zawiera offset strefy.

### Ponowna weryfikacja po odtworzeniu OPNsense 2026-10-10

- TCP do LiteLLM `10.10.20.10:4000`, policy proxy `:8001` i Monitor `:24224` z Agent: OPEN.
- TCP do Target MCP `10.10.30.10:8000` i Monitor `:24224` z Gateway: OPEN; z Gateway TCP `1.1.1.1:443`: OPEN.
- TCP do Monitor `:24224` z Target: OPEN.
- Nowe syntetyczne znaczniki `LAB_TELEMETRY_RECOVERY_F04_AGENT_20261010_01`, `..._GATEWAY_...` i `..._TARGET_...` pojawily sie na Monitor (kazdy po 2 razy w tagach audit/auth).

### PCAP-MCP smoke run 2026-10-10

- Podczas dwoch aktywnych OPNsense capture'ow (LAN TCP/8001 oraz OPT1+OPT2 TCP/8000) uruchomiono z VM-Agent `python3 /tmp/mcp_pcap_smoke.py`.
- Wynik klienta: `mcp_initialize=OK`, `read_untrusted_note=OK`, run ID `PCAP-MCP-20261010-c2639542`, `canary_submitted=false`.
- Gateway `/var/log/lab-control/decisions.jsonl` zawiera `policy_decision=allow`, `execution_attempt` i `execution_result=success`, source IP `10.10.10.10`.
- Monitor `/var/log/lab-telemetry/forwarded.jsonl` odebral te trzy rekordy; Target receiver nie ma wpisu canary dla tego run ID.
- To potwierdza uruchomienie testowego przeplywu MCP; pliki PCAP pozyskano osobno przez SSH i wyniki Zeek zapisano w `maszyny/vm-monitor.md`.
- DNS `example.com` przez Unbound dziala z Agent, Gateway, Target oraz — po korekcie — Monitor. Z Monitor odpowiedzi A: `104.20.23.154`, `172.66.147.243`; TCP `10.10.40.1:53` OPEN.

Dokumentacja producentow: [Fluent Bit Ubuntu](https://docs.fluentbit.io/manual/installation/downloads/linux/ubuntu.md), [Fluent Bit Forward input](https://docs.fluentbit.io/manual/data-pipeline/inputs/forward.md), [Fluent Bit File output](https://docs.fluentbit.io/manual/data-pipeline/outputs/file.md), [Zeek install](https://docs.zeek.org/en/current/install.html), [Zeek quickstart](https://docs.zeek.org/en/current/quickstart.html), [OPNsense packet capture](https://docs.opnsense.org/manual/diagnostics_interfaces.html#packet-capture).
