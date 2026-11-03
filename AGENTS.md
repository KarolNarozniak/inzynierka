# AGENTS.md

## Cel repozytorium
- To repozytorium sluzy do pracy inzynierskiej o bezpieczenstwie agentowych IDE oraz do budowy laboratorium VM dla badan.
- Glowne zrodlo aktualnego tekstu pracy: `draft_praca/Narozniak_praca_inzynierska_format_WCYv2.pdf`; pliki `.docx` sa dokumentami roboczymi, a nie latwymi do automatycznego diffowania.
- `przykladowe_prace/` zawiera materialy referencyjne; nie traktuj ich jako faktow o tej pracy ani konfiguracji laboratorium.

## Aktualny etap
- Praca jest na etapie projektowania i przygotowania maszyn w VMware Workstation Pro 25H2 Version 25.0.0.24995812.
- Priorytetem jest struktura dokumentacji laboratorium oraz docelowa adresacja i segmentacja sieci przed uruchomieniem VM.
- W drafcie pracy wiele tabel i listingow ma placeholdery, komentarze `DO UZUPELNIENIA` albo przykladowe wartosci; nie wolno ich opisywac jako wynikow wykonanych badan.

## Maszyny laboratoryjne
- `VM-Agent`: Ubuntu Desktop 26.04.01, agentowe IDE, Kilo Code/VS Code, lokalny MCP, karty NAT do konfiguracji SSH oraz VMnet strefy Agent.
- `VM-Target`: Ubuntu Server 26.04.01, zdalny MCP i odbiornik danych-canary, karty NAT do konfiguracji SSH oraz VMnet strefy Cele.
- `VM-Monitor`: Ubuntu Server 26.04.01, logi, Zeek/PCAP i analiza, karty NAT do konfiguracji SSH oraz VMnet strefy Monitoring.
- `VM-Gateway`: Ubuntu Server 26.04.01, LiteLLM i mechanizm kontroli, karty NAT do konfiguracji SSH oraz VMnet strefy Uslugi.
- `VM-FW`: OPNsense 24.7, routing i filtrowanie miedzy strefami; docelowo bramy stref powinny byc na interfejsach tej VM.

## Dokumentowanie zmian w VM
- Dla kazdej maszyny utrzymuj oddzielny, aktualny plik konfiguracji i dziennik operacji; jesli struktura nie istnieje, zaproponuj lub utworz ja przed dluzsza konfiguracja.
- Kazdy wpis operacyjny powinien rozrozniac: plan, wykonana komende, wynik, pliki zmienione na VM, restart uslug i otwarte pytania.
- Nie mieszaj komend faktycznie wykonanych z komendami proponowanymi; oznaczaj je jednoznacznie.
- Zapisuj wersje komponentow odczytane z maszyn, a nie przepisane z projektu lub draftu.

## Siec i adresacja
- Aktualna decyzja projektowa dla VMnetow, podsieci i adresow VM jest w `docs/laboratorium/adresacja-sieci.md`; nie zmieniaj jej bez aktualizacji tego pliku.
- Tymczasowa karta NAT sluzy do SSH i konfiguracji; nie traktuj jej jako czesci badanej segmentacji, chyba ze zostanie to jawnie zdecydowane.
- Tabela 3.3 pracy ma odzwierciedlac rzeczywiste VMnety, podsieci i bramy dla stref: Agent, Uslugi, Cele, Monitoring, WAN.
- Nie zakladaj numerow VMnet ani podsieci bez zapisania decyzji projektowej; najpierw aktualizuj dokumentacje, potem konfiguruj VM.
- Ruch miedzy strefami powinien przechodzic przez OPNsense; unikaj bezposrednich polaczen VMnet, ktore omijaja `VM-FW`.
- Przy regule sieciowej zapisuj zrodlo, cel, protokol/port, decyzje, uzasadnienie i interfejs OPNsense, na ktorym egzekwowana jest regula.

## Zasady bezpieczenstwa laboratorium
- Nie zapisuj prawdziwych kluczy API, hasel, tokenow ani danych osobowych w repozytorium, draftach, listingach, promptach ani logach.
- Dane-canary maja byc syntetyczne i unikalne dla przebiegu; nie moga przypominac prawdziwych sekretow.
- Nie deklaruj PASS, skutecznosci zabezpieczenia ani realizacji hipotezy bez dowodu z logow, stanu zasobu, PCAP/Zeek albo odbiornika.
- Rozrozniaj zamiar modelu, zadanie narzedzia, decyzje allow/ask/deny, probe wykonania i potwierdzony skutek.

## Praca z dokumentem inzynierskim
- Gdy aktualizujesz tresc pracy, zachowuj roznice miedzy projektem, stanem faktycznym i wynikami badan.
- Komentarze w PDF wskazuja miejsca wymagajace weryfikacji; nie usuwaj ich sensu bez potwierdzenia rzeczywista konfiguracja albo wynikami.
- Szczegolnie uwazaj na niespojnosci z draftu: powtarzajace sie identyfikatory WF/F/TK/TM, niedokonczone zdanie w sekcji 4.10 oraz hipotezy rozne miedzy rozdzialem 1 i tabela 5.2.
