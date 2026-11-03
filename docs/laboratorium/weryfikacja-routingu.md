# Weryfikacja routingu i segmentacji

Status historyczny: zweryfikowano 2026-09-27 po zamknieciu egressu na kartach NAT. Konfiguracja OPNsense utracona/resetowana 2026-10-10; wyniki ponizej opisuja stan sprzed resetu i nie potwierdzaja biezacego firewalla.

## Problem i przyczyna

- Kazda Ubuntu VM ma dwie karty: NAT VMware do administracyjnego SSH oraz karte badawcza danej strefy.
- Poczatkowo DHCP na NAT instalowal trase domyslna i DNS `192.168.234.2`, co pozwalalo ruchowi publicznemu omijac `VM-FW`.
- Na `VM-Agent` renderer NetworkManager dodal do statycznej trasy domyslnej offset metryki (`20050` zamiast wpisanej `50`). Sama zmiana metryki nie byla wiec wystarczajaca do wybrania bramy OPNsense, dopoki istniala trasa DHCP NAT.

## Rozwiazanie

- Na kartach NAT `ens33` ustawiono `dhcp4-overrides.use-routes: false` i `use-dns: false`.
- NAT nadal pobiera adres IPv4 i zachowuje bezposrednia trase do `192.168.234.0/24`, dzieki czemu SSH z hosta `192.168.234.1` pozostaje dostepne.
- Na kartach badawczych `ens37` ustawiono statyczny adres, DNS lokalnego Unbound OPNsense i default route przez brame strefy.
- Konfiguracje zrodlowe Netplan sa w `docs/laboratorium/config/vm-agent/`, `vm-gateway/`, `vm-target/` i `vm-monitor/`.

## Wyniki weryfikacji

| Maszyna | Publiczna trasa | DNS | Trasa do hosta SSH | Wynik |
| --- | --- | --- | --- | --- |
| VM-Agent | `10.10.10.1` | `10.10.10.1` | `192.168.234.1` przez NAT | OK |
| VM-Gateway | `10.10.20.1` | `10.10.20.1` | `192.168.234.1` przez NAT | OK |
| VM-Target | `10.10.30.1` | `10.10.30.1` | `192.168.234.1` przez NAT | OK |
| VM-Monitor | `10.10.40.1` | `10.10.40.1` | `192.168.234.1` przez NAT | OK |

## Wyniki polityki egress

| Zrodlo | Cel | Oczekiwany wynik | Zaobserwowany wynik |
| --- | --- | --- | --- |
| VM-Agent | LiteLLM `10.10.20.10:4000` | Allow | Health HTTP 200 |
| VM-Gateway | OpenAI API TCP/443 | Allow | HTTPS polaczenie potwierdzone, endpoint bez tokenu HTTP 401 |
| VM-Agent | OpenAI API TCP/443 | Deny | Polaczenie nie zostalo nawiazane |
| VM-Target | OpenAI API TCP/443 | Deny | Timeout |
| VM-Monitor | OpenAI API TCP/443 | Deny | Timeout |

Po utworzeniu F-03 z VM-Agent do VM-Target TCP/8000 zweryfikowano MCP Streamable HTTP end-to-end. Narzedzie `submit_canary` zarejestrowalo source IP `10.10.10.10`; port receivera TCP/8080 pozostal niedostepny z Agent, bo nasluchuje tylko na loopback Target.

Testy segmentacji dla TCP/8000:

| Zrodlo | Cel | Wynik |
| --- | --- | --- |
| VM-Agent `10.10.10.10` | VM-Target `10.10.30.10:8000` | Allow; MCP initialize/tool call OK |
| VM-Gateway `10.10.20.10` | VM-Target `10.10.30.10:8000` | Timeout / denied |
| VM-Monitor `10.10.40.10` | VM-Target `10.10.30.10:8000` | Timeout / denied |
| VM-Agent `10.10.10.10` | VM-Target `10.10.30.10:8080` | Timeout; service is loopback-only |

Po wdrozeniu MCP policy proxy:

| Zrodlo | Cel | Wynik |
| --- | --- | --- |
| VM-Agent `10.10.10.10` | VM-Gateway `10.10.20.10:8001` | Allow; proxy health HTTP 200 i MCP test OK |
| VM-Gateway `10.10.20.10` | VM-Target `10.10.30.10:8000` | Allow; backend MCP reachable |
| VM-Agent `10.10.10.10` | VM-Target `10.10.30.10:8000` | Timeout / direct bypass removed |

## Zrodla techniczne

- Netplan: `use-routes: false` ignoruje trasy dostarczone przez DHCP i jest dostepne dla rendererow networkd oraz NetworkManager; `routes` definiuje trasy statyczne. Dokumentacja: <https://netplan.readthedocs.io/en/stable/netplan-yaml/>.
- OPNsense: reguly firewall sa oceniane na interfejsie, na ktorym ruch wchodzi do zapory; automatyczny outbound NAT obejmuje sieci interfejsow wewnetrznych. Dokumentacja: <https://docs.opnsense.org/manual/firewall.html> i <https://docs.opnsense.org/manual/nat.html>.

## Ograniczenia

- Wyniki potwierdzaja aktualna konfiguracje i wskazane testy sieciowe, nie stanowia jeszcze wyniku scenariuszy badawczych pracy.
- NAT VMware pozostaje aktywny jako interfejs administracyjny. Do wlasciwych serii eksperymentalnych nalezy zdecydowac, czy karty NAT maja pozostac podlaczone, ale bez tras i DNS, czy maja byc wylaczane po utworzeniu migawek.
