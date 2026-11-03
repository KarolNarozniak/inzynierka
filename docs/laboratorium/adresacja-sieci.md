# Adresacja sieci laboratorium

Status: decyzja projektowa do konfiguracji VMware przed uruchomieniem VM.

Uwaga o stanie OPNsense: interfejsy i adresy odtworzono 2026-10-10 po utracie konfiguracji, ale biezace reguly firewall/DNS/egress nie sa jeszcze ponownie zweryfikowane. Szczegoly: `docs/laboratorium/stan-maszyn.md`.

## Zalozenia
- `VMnet8` pozostaje siecia NAT VMware i sluzy jako WAN dla `VM-FW` oraz tymczasowy dostep administracyjny SSH do maszyn Ubuntu.
- Sieci badawcze korzystaja z oddzielnych VMnetow bez DHCP VMware i bez bezposredniego polaczenia z hostem, o ile VMware na to pozwala.
- Bramy stref badawczych znajduja sie na interfejsach `VM-FW` z OPNsense.
- Ruch miedzy strefami ma przechodzic przez `VM-FW`; interfejsy NAT na maszynach Ubuntu sa tymczasowe i nie sa czescia badanej segmentacji.
- Docelowo podczas eksperymentow interfejsy NAT na `VM-Agent`, `VM-Target`, `VM-Monitor` i `VM-Gateway` powinny byc wylaczone albo miec wyzszy priorytet metryki niz trasa przez `VM-FW`.

## Tabela 3.3 - strefy sieciowe laboratorium

| Strefa | Siec VMnet | Podsieć | Brama | Przeznaczenie |
| --- | --- | --- | --- | --- |
| Agent | VMnet10 | 10.10.10.0/24 | 10.10.10.1 | Agentowe IDE, Kilo Code, VS Code, lokalny MCP |
| Uslugi | VMnet11 | 10.10.20.0/24 | 10.10.20.1 | LiteLLM i mechanizm kontroli |
| Cele | VMnet12 | 10.10.30.0/24 | 10.10.30.1 | Zdalny MCP i odbiornik danych-canary |
| Monitoring | VMnet13 | 10.10.40.0/24 | 10.10.40.1 | Centralne logi, analiza, Zeek/PCAP |
| WAN | VMnet8 | 192.168.234.0/24 | 192.168.234.2 | NAT VMware, kontrolowany dostep zewnetrzny i tymczasowy SSH |

## Konfiguracja VMnet w VMware

| VMnet | Typ VMware | DHCP VMware | Polaczenie hosta | Uwagi |
| --- | --- | --- | --- | --- |
| VMnet8 | NAT | Wlaczone | Wlaczone | Rzeczywista podsiec NAT VMware: `192.168.234.0/24`; host VMware widoczny jako `192.168.234.1`, brama NAT zwykle `192.168.234.2`. |
| VMnet10 | Host-only/custom | Wylaczone | Wylaczone | Strefa Agent, adresy statyczne. |
| VMnet11 | Host-only/custom | Wylaczone | Wylaczone | Strefa Uslugi, adresy statyczne. |
| VMnet12 | Host-only/custom | Wylaczone | Wylaczone | Strefa Cele, adresy statyczne. |
| VMnet13 | Host-only/custom | Wylaczone | Wylaczone | Strefa Monitoring, adresy statyczne. |

## Interfejsy VM-FW / OPNsense

| Interfejs logiczny | VMnet | Adres | Maska | Brama upstream | Rola |
| --- | --- | --- | --- | --- | --- |
| WAN | VMnet8 | 192.168.234.10 | /24 | 192.168.234.2 | Wyjscie do NAT VMware |
| AGENT | VMnet10 | 10.10.10.1 | /24 | brak | Brama strefy Agent |
| SERVICES | VMnet11 | 10.10.20.1 | /24 | brak | Brama strefy Uslugi |
| TARGETS | VMnet12 | 10.10.30.1 | /24 | brak | Brama strefy Cele |
| MONITORING | VMnet13 | 10.10.40.1 | /24 | brak | Brama strefy Monitoring |

Kolejnosc kart w `VM-FW` ustaw w VMware tak, aby latwo rozpoznac interfejsy podczas pierwszej konfiguracji OPNsense: `VMnet8`, `VMnet10`, `VMnet11`, `VMnet12`, `VMnet13`.

## Interfejsy maszyn Ubuntu

| Maszyna | Interfejs VMware | VMnet | Adres | Maska | Brama domyslna docelowa | Rola |
| --- | --- | --- | --- | --- | --- | --- |
| VM-Agent | NIC 1 | VMnet8 | DHCP | DHCP | nie dotyczy po wylaczeniu NAT | Tymczasowe SSH i konfiguracja |
| VM-Agent | NIC 2 | VMnet10 | 10.10.10.10 | /24 | 10.10.10.1 | Agentowe IDE |
| VM-Gateway | NIC 1 | VMnet8 | DHCP | DHCP | nie dotyczy po wylaczeniu NAT | Tymczasowe SSH i konfiguracja |
| VM-Gateway | NIC 2 | VMnet11 | 10.10.20.10 | /24 | 10.10.20.1 | LiteLLM i kontrola |
| VM-Target | NIC 1 | VMnet8 | DHCP | DHCP | nie dotyczy po wylaczeniu NAT | Tymczasowe SSH i konfiguracja |
| VM-Target | NIC 2 | VMnet12 | 10.10.30.10 | /24 | 10.10.30.1 | Zdalny MCP i odbiornik |
| VM-Monitor | NIC 1 | VMnet8 | DHCP | DHCP | nie dotyczy po wylaczeniu NAT | Tymczasowe SSH i konfiguracja |
| VM-Monitor | NIC 2 | VMnet13 | 10.10.40.10 | /24 | 10.10.40.1 | Logi i analiza |

## Rezerwacje adresow

| Zakres | Przeznaczenie |
| --- | --- |
| 10.10.X.1 | Brama strefy na `VM-FW` |
| 10.10.X.10 | Glowna maszyna w danej strefie |
| 10.10.X.20-10.10.X.49 | Dodatkowe uslugi stale |
| 10.10.X.50-10.10.X.99 | Komponenty testowe i prototypy |
| 10.10.X.100-10.10.X.199 | Zakres opcjonalnego DHCP, jesli pozniej zostanie wlaczone na OPNsense |
| 10.10.X.200-10.10.X.254 | Rezerwa administracyjna |

## Minimalna macierz komunikacji startowej

| ID | Zrodlo | Cel | Protokol/port | Decyzja | Interfejs OPNsense | Uzasadnienie |
| --- | --- | --- | --- | --- | --- | --- |
| F-01 | VM-Agent `10.10.10.10` | VM-Gateway `10.10.20.10` | TCP/4000 lub docelowy port LiteLLM | Zezwol | AGENT | Dostep agenta do bramy modelu |
| F-02 | VM-Gateway `10.10.20.10` | Internet/API modelu | TCP/443 | Zezwol | SERVICES | Wywolanie chmurowego API przez LiteLLM |
| F-03 | VM-Agent `10.10.10.10/32` | VM-Target `10.10.30.10/32` | TCP/8000 | Wylaczona | LAN | Tymczasowy bezposredni test transportu; zastapiony proxy |
| F-06 | VM-Agent `10.10.10.10/32` | VM-Gateway `10.10.20.10/32` | TCP/8001 | Zezwol | LAN | Agent do proxy kontroli MCP |
| F-07 | VM-Gateway `10.10.20.10/32` | VM-Target `10.10.30.10/32` | TCP/8000 | Zezwol | Uslugi/OPT1 | Proxy kontroli do zdalnego MCP |
| F-04-A | VM-Agent `10.10.10.10/32` | VM-Monitor `10.10.40.10/32` | TCP/24224 | Zezwol | AGENT/LAN | Fluent Bit Forward do odbiornika logow |
| F-04-G | VM-Gateway `10.10.20.10/32` | VM-Monitor `10.10.40.10/32` | TCP/24224 | Zezwol | SERVICES/OPT1 | Fluent Bit Forward; logi LiteLLM i policy proxy |
| F-04-T | VM-Target `10.10.30.10/32` | VM-Monitor `10.10.40.10/32` | TCP/24224 | Zezwol | TARGETS/OPT2 | Fluent Bit Forward; logi MCP i canary |
| F-05 | Strefy badawcze | Pozostale cele | Dowolny | Blokuj | Wszystkie interfejsy wewnetrzne | Domyslna odmowa |

F-01, F-06 i F-07 zostaly potwierdzone. F-03 jest wylaczona po wdrozeniu proxy MCP. Uzytkownik wdrozyl F-04-A/G/T; test 2026-09-28 potwierdzil TCP/24224 i odbior unikalnego syntetycznego zdarzenia auditd z kazdej strefy na `VM-Monitor`. Szczegoly i ograniczenia dowodu: `docs/laboratorium/telemetria.md`.

PCAP bedzie przechwytywany na interfejsach OPNsense, przez ktore przechodzi ruch miedzystrefowy, za pomoca Diagnostics > Packet Capture. Pliki PCAP zostana pobrane i analizowane offline przez Zeek na VM-Monitor. Nie zaklada sie, ze interfejs VM-Monitor widzi unicast innych VMnetow, ani nie otwiera sie dodatkowego ruchu miedzystrefowego dla PCAP.

## Uwagi do konfiguracji systemow
- Na maszynach Ubuntu nazwy interfejsow sprawdz komenda `ip link`; nie zakladaj nazw typu `ens33` bez odczytu z VM.
- Podczas instalacji wygodnie zostawic NAT jako trase domyslna, ale przed testami ustaw trase domyslna przez brame strefy albo wylacz NAT.
- Nie ustawiaj bramy domyslnej na interfejsach pasywnych, jesli pozniej dodasz dodatkowe karty do monitoringu ruchu.
- Po ustawieniu adresacji zapisz w dzienniku kazdej maszyny rzeczywiste nazwy interfejsow, adresy MAC, adresy IP, trasy i wynik testu lacznosci do bramy.
