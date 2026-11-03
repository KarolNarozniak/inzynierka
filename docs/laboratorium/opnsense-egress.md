# Kontrolowany egress VM-Gateway przez OPNsense

Status historyczny: wdrozone i zweryfikowane na wszystkich Ubuntu VM przed resetem konfiguracji OPNsense 2026-10-10. Biezacy stan reguł egress/DNS i bramy WAN wymaga ponownego wdrozenia oraz weryfikacji.

## Aktualny stan zweryfikowany

- SSH administracyjne: VM-Gateway `192.168.234.148/24` przez `VMnet8` / `ens33`.
- Siec uslug: `10.10.20.10/24` przez `VMnet11` / `ens37`, brama OPNsense `10.10.20.1`.
- Ruch publiczny VM-Gateway preferuje OPNsense `10.10.20.1` przez `ens37` (metric 50); DHCP NAT nie instaluje trasy domyslnej.
- DNS VM-Gateway korzysta z Unbound OPNsense `10.10.20.1`; DHCP NAT nie nadpisuje DNS.
- `VM-Agent`, `VM-Target` i `VM-Monitor` maja domyslna trase przez swoja brame OPNsense, a DHCP NAT nie instaluje tras ani DNS.
- Po wdrozeniu regul DNS testy z `VM-Agent` (`10.10.10.1`), `VM-Target` (`10.10.30.1`) i `VM-Monitor` (`10.10.40.1`) dla `example.com` i `api.openai.com` zwrocily rcode 0, po 2 odpowiedzi.

## Ochrona dostepu SSH

Zmiana tras domyslnych nie usuwa adresow NAT ani tras polaczonych `192.168.234.0/24` przez `ens33`. Polaczenie SSH hosta `192.168.234.1` pozostaje bezposrednie/on-link. Karty NAT nie zapewniaja trasy domyslnej omijajacej zapore.

## OPNsense: ustawienia wymagane przed zmiana trasy

1. `Firewall > NAT > Outbound`: tryb `Automatic` (albo Hybrid z jawna regula NAT dla `10.10.20.10/32` wychodzaca przez WAN).
2. `Services > Unbound DNS > General`: wlaczyc resolver, nasluch na OPT1/Services (`10.10.20.1`) i dopuscic klienta `10.10.20.10/32` w access list, jesli lista jest wymagana.
3. `Firewall > Rules > OPT1`: dodac ponizsze reguly, nad blokadami.

| ID | Zrodlo | Cel | Protokol/port | Decyzja | Uzasadnienie |
| --- | --- | --- | --- | --- | --- |
| E-DNS-UDP | `10.10.20.10/32` | OPT1 address | UDP/53 | Pass | DNS przez resolver OPNsense |
| E-DNS-TCP | `10.10.20.10/32` | OPT1 address | TCP/53 | Pass | DNS fallback/duze odpowiedzi |
| E-HTTPS | `10.10.20.10/32` | any | TCP/443 | Pass | Dostep LiteLLM do dostawcy API |

Nie wlaczac reguly `OPT1 net to any`. Reguly egzekwowane sa na OPT1, bo ruch inicjuje VM-Gateway ze strefy Services.

## Kolejnosc wdrozenia i testy

1. Potwierdzic WAN OPNsense ma Internet i dzialajacy outbound NAT.
2. Wlaczyc Unbound DNS na OPT1 i dodac reguly E-DNS-UDP/E-DNS-TCP/E-HTTPS.
3. Z VM-Gateway sprawdzic DNS przez `10.10.20.1` i HTTPS do dostawcy, zanim zmienimy metryki.
4. Ustawic DNS i default route Netplan przez OPNsense na kazdej Ubuntu VM; na NAT wylaczyc instalowanie tras i DNS z DHCP.
5. Po `netplan apply` potwierdzic SSH przez NAT, `ip route get 1.1.1.1` przez brame OPNsense danej strefy, DNS przez Unbound i brak default route przez `ens33`.

Jesli po zmianie zniknie Internet, SSH nadal powinno byc dostepne po bezposredniej trasie on-link do `192.168.234.1`; ustawic tymczasowo trase domyslna przez NAT jako rollback.

## Test z VM-Gateway po dodaniu regul 2026-09-27

- Zapytanie UDP DNS do `192.168.234.2:53` dla `example.com`: rcode 0, 2 odpowiedzi.
- Zapytania UDP DNS do `10.10.20.1:53` dla `example.com`, `archive.ubuntu.com` i `api.openai.com`: rcode 2 (SERVFAIL), 0 odpowiedzi.
- Trasy VM-Gateway nie zostaly zmienione; domyslny ruch nadal idzie przez NAT.
- Wniosek: reguly OPT1 przepuszczaja zapytanie do resolvera, ale Unbound na OPNsense nie uzyskuje odpowiedzi. Nie zmieniac jeszcze trasy domyslnej VM-Gateway.

## Test po skonfigurowaniu systemowego DNS OPNsense 2026-09-27

- Testy z VM-Gateway do Unbound `10.10.20.1:53` dla `example.com` i `api.openai.com`: rcode 0, po 2 odpowiedzi.
- Default route VM-Gateway nadal idzie przez VMware NAT `192.168.234.2`; zmiana trasy nie zostala jeszcze wykonana.
- `litellm.service` pozostaje active i nasluchuje na `10.10.20.10:4000`.
- Wniosek: DNS przez OPNsense dziala; nastepny krok to preferowanie trasy przez `10.10.20.1` i test egressu przy zachowaniu NAT/SSH.

## Test tymczasowej trasy domyslnej przez OPNsense 2026-09-27

- Dodano tymczasowa trase `default via 10.10.20.1 dev ens37 metric 50`.
- `ip route get 1.1.1.1` potwierdzil wyjscie przez `10.10.20.1`.
- DNS do `10.10.20.1:53` nadal dzialal.
- HTTPS do `https://api.openai.com/v1/models` timeoutowal.
- Trasa tymczasowa zostala usunieta; obecnie HTTPS dziala ponownie przez NAT i zwraca HTTP 401 bez tokenu (oczekiwane dla endpointu chronionego).
- Trasa do hosta `192.168.234.1` pozostala bezposrednio przez `ens33`, potwierdzajac zachowanie sciezki SSH.
- Nie utrwalac jeszcze zmiany trasy domyslnej. Do sprawdzenia tryb Outbound NAT oraz log blokad OPNsense dla zrodla `10.10.20.10`.

## Ponowny test po potwierdzeniu Automatic Outbound NAT 2026-09-27

- Uzytkownik potwierdzil Automatic outbound NAT; wygenerowana regula obejmuje OPT1 networks.
- Trasa testowa przez `10.10.20.1` nadal nie ma dostepu HTTPS do `1.1.1.1:443` ani `api.openai.com:443`; ICMP do `1.1.1.1` rowniez nie odpowiada.
- Trasa zostala natychmiast cofnieta; NAT bezposredni i SSH nadal dzialaja.
- Kolejny krok diagnostyczny: sprawdzic ping/HTTPS z OPNsense przez WAN oraz Live View dla ruchu z `10.10.20.10`; nie utrwalac trasy do czasu ustalenia przyczyny.

## Tablica routingu OPNsense 2026-09-27

- `System > Routes > Status` pokazuje trasy polaczone dla stref i WAN (`192.168.234.0/24` przez `em0`), ale na widocznych stronach IPv4 nie ma trasy domyslnej `0.0.0.0/0`.
- `System > Gateways > Configuration` pokazuje `WAN_DHCP` (`192.168.234.2`) jako aktywny gateway, ale sam wpis aktywnego gatewaya nie potwierdza obecnosci trasy domyslnej w kernelu.
- Do sprawdzenia edycja gatewaya IPv4 `WAN_DHCP` i ustawienie `Upstream Gateway`; po Apply ponownie sprawdzic Routes Status. Nie dodawac statycznej trasy w `System > Routes > Configuration` dla WAN.

## Egress utrwalony po dodaniu domyslnej trasy WAN 2026-09-27

- Tymczasowy test HTTPS przez WAN OPNsense zaczal dzialac po pojawieniu sie domyslnej trasy WAN; bez tokenu OpenAI odpowiedzialo HTTP 401.
- Na VM-Gateway zapisano default route przez `10.10.20.1` metric 50 oraz DNS `10.10.20.1`; DHCP NAT nie instaluje tras ani DNS.
- Na VM-Agent, VM-Target i VM-Monitor ustawiono analogiczne default routes przez `10.10.10.1`, `10.10.30.1`, `10.10.40.1`, DNS lokalnego Unbound i wylaczono DHCP routes na NAT.
- `ip route get 1.1.1.1` na kazdej VM potwierdza wyjscie przez brame OPNsense jej strefy.
- `ip route get 192.168.234.1` na kazdej VM potwierdza bezposrednia trase on-link przez `ens33`; SSH zostaje zachowane.
- LiteLLM health odpowiada HTTP 200 lokalnie oraz z VM-Agent.
- Pelny Netplan jest zachowany w `docs/laboratorium/config/vm-gateway/00-installer-config.yaml`; na VM zapisano kopie poprzedniej konfiguracji.

## Egress po resecie i czesciowym odtworzeniu OPNsense 2026-10-10

- Z VM-Gateway TCP do `1.1.1.1:443` zwrocil `No route to host`, a DNS do `10.10.20.1` zwrocil `SERVFAIL`.
- Adres WAN DHCP `192.168.234.150/24` jest obecny, lecz aktywnej trasy domyslnej przez `192.168.234.2` nie potwierdzono.
- Sprawdz `WAN_DHCP` jako upstream/default gateway, trasa `0.0.0.0/0`, Outbound NAT `Automatic` oraz Unbound listener/ACL dla sieci wewnetrznych. Do tego czasu nie uznawac egressu ani DNS za odtworzone.

## Aktualizacja po ustawieniu WAN_DHCP i Unbound 2026-10-10

- `WAN_DHCP` jest active, upstream, gateway `192.168.234.2`; tabela routingu pokazuje default route przez `em0`/WAN.
- Outbound NAT: Automatic.
- Z VM-Gateway TCP `1.1.1.1:443` OPEN. Zapytania Unbound przez `10.10.10.1`, `10.10.20.1` i `10.10.30.1` dla `example.com` zwrocily adresy.
- VM-Monitor korzysta z `10.10.40.1`, ale nie otrzymal odpowiedzi DNS; TCP/53 do OPT3 address nie byl OPEN. Do sprawdzenia konfiguracja interfejsu Unbound/ACL oraz aktywnosc listenera na OPT3.

## Ponowna walidacja DNS na Monitor 2026-10-10

- VM-Monitor przez `10.10.40.1` rozwiazal `example.com` do `104.20.23.154` i `172.66.147.243`; TCP/53 do OPT3 address OPEN.
- DNS z Agent, Gateway i Target rowniez odpowiadal; WAN_DHCP/default route i Outbound NAT zostaly zweryfikowane jako aktywne.
