# OPNsense - reguly startowe

Status: interfejsy i adresy VM-FW odtworzono 2026-10-10. Po resecie odtworzono i przetestowano F-01, F-02, F-04-A/G/T, F-06, F-07 oraz DNS z czterech stref; znaczniki Fluent Bit z trzech VM dotarly do Monitora. Wykonano i przeanalizowano Zeekiem rzeczywiste capture'y z LAN, OPT1 i OPT2. Eksport ZIP z GUI nadal zwraca blad; PCAP pobrano przez SSH z VM-FW.

## Cel
- Potwierdzic lacznosc diagnostyczna z bramami stref.
- Zachowac zasade domyslnej odmowy dla ruchu miedzy strefami.
- Dodawac reguly na interfejsie, na ktorym ruch wchodzi do OPNsense.

## Reguly diagnostyczne ICMP

Dodaj w GUI OPNsense: `Firewall > Rules > [interfejs]`.

| ID | Interfejs | Action | Protocol | Source | Destination | Uzasadnienie |
| --- | --- | --- | --- | --- | --- | --- |
| D-AGENT-ICMP-GW | LAN | Pass | ICMP | LAN net | LAN address | Test bramy `10.10.10.1` ze strefy Agent |
| D-SERVICES-ICMP-GW | OPT1 | Pass | ICMP | OPT1 net | OPT1 address | Test bramy `10.10.20.1` ze strefy Uslugi |
| D-TARGETS-ICMP-GW | OPT2 | Pass | ICMP | OPT2 net | OPT2 address | Test bramy `10.10.30.1` ze strefy Cele |
| D-MONITORING-ICMP-GW | OPT3 | Pass | ICMP | OPT3 net | OPT3 address | Test bramy `10.10.40.1` ze strefy Monitoring |

Po dodaniu kliknij `Apply changes` i sprawdz pingi z maszyn Ubuntu.

## Minimalne reguly startowe po diagnostyce

Nie dodawaj szerokiej reguly `any to any` miedzy strefami. Domyslna regule OPNsense `Default allow LAN to any rule` nalezy wylaczyc, gdy tylko istnieja jawne reguly potrzebne do zarzadzania i testow. Inaczej strefa Agent moze inicjowac ruch do wszystkich pozostalych stref.

| ID | Interfejs | Source | Destination | Protocol/port | Decyzja | Uzasadnienie |
| --- | --- | --- | --- | --- | --- | --- |
| F-01 | LAN | `10.10.10.10` | `10.10.20.10` | TCP/docelowy port LiteLLM | Pass | Agent do LiteLLM |
| F-02 | OPT1 | `10.10.20.10` | WAN net / Internet | TCP/443 | Pass | LiteLLM do API modelu |
| F-03 | LAN | `10.10.10.10/32` | `10.10.30.10/32` | TCP/8000 | Disabled | Tymczasowy bezposredni test transportu; wylaczony po uruchomieniu proxy |
| F-04-A | LAN | `10.10.10.10/32` (VM-Agent) | `10.10.40.10/32` (VM-Monitor) | TCP/24224 | Pass | Fluent Bit Forward: Agent do centralnego odbiornika logow |
| F-04-G | OPT1 | `10.10.20.10/32` (VM-Gateway) | `10.10.40.10/32` (VM-Monitor) | TCP/24224 | Pass | Fluent Bit Forward: logi LiteLLM i policy proxy |
| F-04-T | OPT2 | `10.10.30.10/32` (VM-Target) | `10.10.40.10/32` (VM-Monitor) | TCP/24224 | Pass | Fluent Bit Forward: logi MCP i odbiornika canary |

## LAN / Agent — reguly do odtworzenia po resecie

Dodaj jawne reguly na `Firewall > Rules > LAN` z `Quick` wlaczonym, przed wylaczeniem domyslnej reguly LAN allow any:

| ID/opis | Action | IPv4 Protocol | Source | Destination | Destination port | Cel |
| --- | --- | --- | --- | --- | --- | --- |
| D-AGENT-DNS-UDP | Pass | UDP | `10.10.10.10/32` | LAN address (`10.10.10.1`) | `53` | Resolver Unbound dla Agenta |
| D-AGENT-DNS-TCP | Pass | TCP | `10.10.10.10/32` | LAN address (`10.10.10.1`) | `53` | DNS TCP/fallback dla Agenta |
| F-01 | Pass | TCP | `10.10.10.10/32` | `10.10.20.10/32` | `4000` | LiteLLM |
| F-06 | Pass | TCP | `10.10.10.10/32` | `10.10.20.10/32` | `8001` | Policy proxy MCP |
| F-04-A | Pass | TCP | `10.10.10.10/32` | `10.10.40.10/32` | `24224` | Fluent Bit Forward do Monitora |

Opcjonalnie dodaj D-AGENT-ICMP-GW z tabeli wyzej dla testu bramy. Nie dodawaj `Agent net -> any`. Po dodaniu wymaganych reguł wyłącz `Default allow LAN to any` oraz `Default allow LAN IPv6 to any`, jeśli IPv6 nie jest elementem laboratorium. Nie potrzeba osobnej reguły GUI/SSH, o ile automatyczna reguła anti-lockout jest włączona (`Firewall > Settings > Advanced > Disable anti-lockout` pozostaje odznaczone); OPNsense dopuszcza wtedy zarządzanie przez LAN niezależnie od reguł użytkownika. Jeśli anti-lockout jest wyłączony, dodaj przed blokadami wąskie reguły Agent `/32` → LAN address TCP/443 oraz tymczasowo TCP/22.

## OPT1/OPT2/OPT3 i WAN — reguly do odtworzenia po resecie

Reguly sa oceniane na interfejsie zrodlowym ruchu. Ustaw Protocol `IPv4`, Destination port wskazany ponizej, Source jako pojedynczy host `/32`:

| ID/opis | Interfejs | Action | Protocol | Source | Destination | Destination port | Cel |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| D-SERVICES-DNS-UDP | OPT1 | Pass | UDP | `10.10.20.10/32` | OPT1 address (`10.10.20.1`) | 53 | Gateway do Unbound |
| D-SERVICES-DNS-TCP | OPT1 | Pass | TCP | `10.10.20.10/32` | OPT1 address (`10.10.20.1`) | 53 | DNS TCP/fallback |
| F-02 | OPT1 | Pass | TCP | `10.10.20.10/32` | any | 443 | Jedyny dozwolony egress HTTPS/API |
| F-07 | OPT1 | Pass | TCP | `10.10.20.10/32` | `10.10.30.10/32` | 8000 | Policy proxy Gateway do MCP Target |
| F-04-G | OPT1 | Pass | TCP | `10.10.20.10/32` | `10.10.40.10/32` | 24224 | Fluent Bit Gateway do Monitor |
| D-TARGETS-DNS-UDP | OPT2 | Pass | UDP | `10.10.30.10/32` | OPT2 address (`10.10.30.1`) | 53 | Target do Unbound |
| D-TARGETS-DNS-TCP | OPT2 | Pass | TCP | `10.10.30.10/32` | OPT2 address (`10.10.30.1`) | 53 | DNS TCP/fallback |
| F-04-T | OPT2 | Pass | TCP | `10.10.30.10/32` | `10.10.40.10/32` | 24224 | Fluent Bit Target do Monitor |
| D-MONITORING-DNS-UDP | OPT3 | Pass | UDP | `10.10.40.10/32` | OPT3 address (`10.10.40.1`) | 53 | Monitor do Unbound |
| D-MONITORING-DNS-TCP | OPT3 | Pass | TCP | `10.10.40.10/32` | OPT3 address (`10.10.40.1`) | 53 | DNS TCP/fallback |

Na OPT1/OPT2/OPT3 nie dodawaj `net -> any`; poza tymi wyjatkami pozostaw domyslna blokade miedzystrefowa. Na WAN ustaw IPv4 DHCP z VMware VMnet8 i `WAN_DHCP` jako brame domyslna; Outbound NAT ustaw `Automatic`. Nie dodawaj przychodzacej reguly WAN dla SSH — zarzadzanie odbywa sie z LAN przez anti-lockout.

W `Services > Unbound DNS` wlacz resolver, nasluchuj na LAN i OPT1-OPT3 (nie WAN), oraz dodaj ACL dla `10.10.10.0/24`, `10.10.20.0/24`, `10.10.30.0/24` i `10.10.40.0/24`. Dodaj reguly DNS powyzej dla kazdego hosta korzystajacego z lokalnego resolvera.

F-03 byla tymczasowo dodana i przetestowana end-to-end z VM-Agent przed wdrozeniem kontroli; po uruchomieniu proxy zostala wylaczona. F-04-A/G/T dodano na interfejsach zrodlowych po wdrozeniu odbiornika Fluent Bit zwiazanego wylacznie z `10.10.40.10:24224`.

Uzytkownik potwierdzil dodanie F-04-A/G/T 2026-09-28. Testy z VM-Agent, VM-Gateway i VM-Target otworzyly TCP/24224, a unikalne syntetyczne znaczniki auditd z kazdej maszyny dotarly na Monitor.

Uwaga architektoniczna: aktywna F-03 dawała VM-Agent bezpośredni dostęp do VM-Target i omijała mechanizm allow/ask/deny. Była to reguła tymczasowego testu transportu, nie docelowa ścieżka badań ochronnych. Po uruchomieniu proxy została wyłączona.

Docelowe przeplywy po wdrozeniu proxy na VM-Gateway:

| ID | Interfejs OPNsense | Zrodlo | Cel | Protokol/port | Decyzja | Uzasadnienie |
| --- | --- | --- | --- | --- | --- | --- |
| F-06 | LAN | `10.10.10.10/32` | `10.10.20.10/32` | TCP/8001 | Pass | Agent do bramy kontroli MCP |
| F-07 | OPT1 | `10.10.20.10/32` | `10.10.30.10/32` | TCP/8000 | Pass | Brama kontroli do zdalnego MCP |
| F-03 | LAN | `10.10.10.10/32` | `10.10.30.10/32` | TCP/8000 | Disabled | Bezposrednie obejscie warstwy kontroli wylaczone |

Nie otwierac portu receivera `8080`; na VM-Target jest on dostepny tylko przez loopback.

Status 2026-09-27: F-06 i F-07 sa wdrozone, F-03 bezposrednia zostala wylaczona. Agent nie laczy sie bezposrednio z Target TCP/8000, ale laczy sie z proxy na Gateway TCP/8001.

## Telemetria Fluent Bit — F-04 (wdrozone i zweryfikowane przed resetem)

Odbiornik na VM-Monitor nasluchuje na `10.10.40.10:24224/tcp`. Reguly dodano w `Firewall > Rules` na interfejsach zrodlowych:

| ID | Interfejs | Action | Protocol | Source | Destination | Destination port | Uzasadnienie |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F-04-A | LAN/AGENT | Pass | TCP | `10.10.10.10/32` | `10.10.40.10/32` | `24224` | Fluent Bit Forward z VM-Agent |
| F-04-G | OPT1/SERVICES | Pass | TCP | `10.10.20.10/32` | `10.10.40.10/32` | `24224` | Fluent Bit Forward z VM-Gateway |
| F-04-T | OPT2/TARGETS | Pass | TCP | `10.10.30.10/32` | `10.10.40.10/32` | `24224` | Fluent Bit Forward z VM-Target |

Reguly ograniczaja ruch do trzech hostow zrodlowych, Monitor `/32` i TCP/24224; nie dodano dostepu z WAN ani calej podsieci. Test 2026-09-28: TCP/24224 OPEN z Agent, Gateway i Target. Na Monitor odebrano znaczniki `LAB_TELEMETRY_F04_AGENT_20260928_01`, `LAB_TELEMETRY_F04_GATEWAY_20260928_01` i `LAB_TELEMETRY_F04_TARGET_20260928_01` jako zdarzenia `received.lab.{agent,gateway,target}.audit` oraz odpowiadajace im wpisy auth. Odebrano tez wszystkie 4 historyczne syntetyczne wpisy canary Target (w tym `SC06-KILO-ALLOW-001`) oraz 22 wpisy `lab.gateway.control` w stanie weryfikacji. Po zastosowaniu regul bufory Fluent Bit senderow byly oprozniane; Target zrestartowano raz, aby wznowic starszy chunk z dlugim backoffem, ktory nastepnie zakonczyl sie `flush succeeded`.

## Korekta domyslnych regul LAN

Na `Firewall > Rules > LAN`:

1. Dodaj jawne reguly potrzebne do labu, np. `F-01` dla LiteLLM.
2. Upewnij sie, ze `Source` i `Destination` dla hostow sa pojedynczymi adresami, np. `10.10.10.10/32` i `10.10.20.10/32`, a nie cala podsiecia.
3. Wylacz `Default allow LAN to any rule` dla IPv4.
4. Wylacz `Default allow LAN IPv6 to any rule`, jesli IPv6 nie jest elementem badan.
5. Kliknij `Apply changes`.

Po wylaczeniu reguly domyslnej oczekiwany wynik testu to: `VM-Agent` nie moze pingowac `VM-Gateway`, `VM-Target` ani `VM-Monitor`, ale docelowo moze laczyc sie z `VM-Gateway:4000` po uruchomieniu LiteLLM i regule F-01.
