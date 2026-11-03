# LiteLLM - aktywacja na VM-Gateway

Status: LiteLLM `1.102.1` jest zainstalowany w `/opt/lab/litellm/venv`, ale usluga nie jest jeszcze uruchomiona.

## Pliki na VM-Gateway

| Sciezka | Cel | Sekrety |
| --- | --- | --- |
| `/opt/lab/litellm/venv/` | Srodowisko Python LiteLLM | Nie |
| `/opt/lab/litellm/configure-litellm-local.sh` | Lokalny kreator `.env` i `config.yaml` | Nie |
| `/opt/lab/litellm/.env` | Zmienne srodowiskowe z sekretami | Tak, tylko na VM |
| `/opt/lab/litellm/config.yaml` | Aktywna konfiguracja proxy | Nie powinien zawierac jawnych kluczy |
| `/etc/systemd/system/litellm.service` | Definicja uslugi systemd | Nie |

## Jednorazowa konfiguracja lokalna

Uruchom na `VM-Gateway` jako uzytkownik `vmgateway`:

```bash
/opt/lab/litellm/configure-litellm-local.sh
```

Skrypt zapyta o:
- identyfikator modelu, domyslnie `openai/gpt-4.1-mini`;
- `OPENAI_API_KEY`, wpisywany bez wyswietlania;
- `LITELLM_MASTER_KEY`, opcjonalnie generowany automatycznie.

Przy ponownym uruchomieniu pozostawienie pola `LITELLM_MASTER_KEY` pustego zachowuje juz ustawiony klucz klienta. Przy pierwszej konfiguracji pusty wpis wygeneruje nowy klucz i pokaże go raz w lokalnej konsoli.

Nie wklejaj prawdziwych kluczy API do repozytorium, czatu, draftu pracy ani logow.

## Uruchomienie uslugi

Po utworzeniu `.env` i `config.yaml`:

```bash
sudo systemctl enable --now litellm.service
sudo systemctl status litellm.service --no-pager
```

## Test z VM-Agent

Po uruchomieniu uslugi test techniczny portu:

```bash
python3 - <<'PY'
import socket
s=socket.create_connection(('10.10.20.10', 4000), 5)
print('connected')
s.close()
PY
```

Test API wymaga klucza klienta `LITELLM_MASTER_KEY` i nie powinien byc zapisywany w repozytorium.

## Status ostatniego testu

- Pierwszy test `OPENAI_API_KEY` zwrocil HTTP 401 `invalid_api_key`; po tym wyniku proxy zostalo zatrzymane i autostart wylaczony.
- Po ponownym wpisaniu klucza test `GET https://api.openai.com/v1/models` zwrocil HTTP 200.
- Uzytkownik uruchomil ponownie `litellm.service`; stan: active/running, bind `10.10.20.10:4000`.
- Test z `VM-Agent` do `/health/liveliness` zwrocil HTTP 200 i `I'm alive!`.
- Test `/v1/models` z autoryzacja `LITELLM_MASTER_KEY` zwrocil HTTP 200 i alias `laboratory-model`.
- Nie wykonano generujacego wywolania modelu.

## Ponowna kontrola klucza klienta 2026-10-10

Plan: sprawdzic lokalnie, czy aktualny `LITELLM_MASTER_KEY` z pliku `.env` autoryzuje `/v1/models`, bez wyswietlania wartosci klucza.

Wykonano z repozytorium przez SSH do `vmgateway@192.168.234.148`: skrypt Python wczytal klucz przez `dotenv_values` i wykonal GET z naglowkiem Bearer. Pierwsza proba na `127.0.0.1:4000` zwrocila `Connection refused`, poniewaz proxy nie nasluchiwalo na loopback. Ponowiono na `10.10.20.10:4000`.

Wynik: HTTP 200; odpowiedz `/v1/models` zawierala alias `laboratory-model`, `owned_by=openai`, `mode=chat`. Wartość klucza nie zostala wypisana. Test potwierdza aktualny klucz z `.env` i endpoint proxy na interfejsie Usługi; nie potwierdza, że Kilo wysyła ten sam klucz. Błąd Kilo `No connected db.` wymaga ponownego wprowadzenia/zweryfikowania klucza w profilu Kilo przed dalszą diagnostyką.

## Restart po rotacji master key 2026-10-10

Diagnostyka wykazała, że aktywny proces LiteLLM (PID `1372`, start `14:26:07 UTC`) miał `LITELLM_MASTER_KEY` różny od wartości w `.env`. `/v1/models` używając klucza z pliku zwracało HTTP 400 `No connected db.`. Zrestartowano usługę przez SSH: `sudo systemctl restart litellm.service`; stan `active`, nowy PID `4875`, start `18:46:37 UTC`. Porównanie środowiska procesu z `.env` potwierdziło zgodność bez wypisywania klucza; ponowny GET `/v1/models` z kluczem z `.env` zwrócił HTTP 200 i alias `laboratory-model`. Wartość klucza nie została zapisana w repozytorium ani logu.
