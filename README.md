# Personal Happ Routing

Собственный профиль раздельной маршрутизации для [Happ](https://happ.su): российские сервисы идут напрямую, заблокированные и остальные ресурсы — через зарубежный VPN. Базы `geosite.dat` и `geoip.dat` обновляются автоматически.

## Как работает профиль

| Маршрут | Что туда попадает |
| --- | --- |
| DIRECT | Российские домены и CIDR из opencck, `category-ru`, `whitelist`, private/LAN, Apple, Microsoft, Steam, Epic, Riot, Tarkov, Faceit, Twitch и Pinterest |
| PROXY | YouTube, Telegram, GitHub, Google Play, Twitch Ads и весь остальной трафик |
| BLOCK | Реклама и телеметрия Windows |

Профиль рассчитан на сценарий «пользователь в РФ + VPS за рубежом» и использует `GlobalProxy: true`. DIRECT-запросы разрешаются через Яндекс DoH, PROXY-запросы — через Google DoH.

## Первый запуск

1. Закоммитьте и запушьте файлы в ветку `main`:

   ```bash
   git add .
   git commit -m "Add personal Happ routing"
   git push origin main
   ```

2. На GitHub откройте **Settings → Actions → General → Workflow permissions**, выберите **Read and write permissions** и сохраните.
3. Откройте **Actions → Build geo-files and Happ routing → Run workflow → Run workflow**. Обычно сборка занимает несколько минут. Push из первого шага тоже автоматически запустит workflow.
4. После успешной сборки появятся:

   - `HAPP/ROUTING.DEEPLINK` — ручное добавление профиля;
   - `HAPP/ROUTING.ONADD.DEEPLINK` — добавление и активация, в том числе для 3x-ui;
   - `HAPP/ROUTING.QR.png` — QR-код для Happ;
   - `release/geosite.dat` и `release/geoip.dat` — геобазы.

## Подключение к 3x-ui

Откройте `HAPP/ROUTING.ONADD.DEEPLINK` в репозитории, скопируйте всю строку и вставьте её в:

**Настройки панели → Подписка → Правила маршрутизации Happ** (`Global routing rules for the VPN client (Happ only)`).

Сохраните настройки и перезапустите панель. При добавлении или обновлении подписки Happ получит профиль в HTTP-заголовке `routing`.

Без 3x-ui можно открыть `ROUTING.DEEPLINK` на устройстве, вставить ссылку из буфера в Happ или отсканировать QR-код.

## Настройка

- Правила DIRECT/PROXY/BLOCK и DNS: `config/routing-template.json`.
- Свои DIRECT-домены: `custom/domains-extra.txt`, по одному на строку.
- Свои DIRECT-IP/CIDR: `custom/cidr-extra.txt`, по одному на строку.

После push workflow пересоберёт базы. По расписанию он запускается ежедневно в 04:20 UTC (07:20 МСК). Стабильные URL геофайлов:

- `https://cdn.jsdelivr.net/gh/ArtemOtr/happ-routing@main/release/geosite.dat`
- `https://cdn.jsdelivr.net/gh/ArtemOtr/happ-routing@main/release/geoip.dat`

jsDelivr работает только с публичными GitHub-репозиториями. Этот репозиторий уже публичный.

## Источники данных

- [opencck iplist](https://russia.iplist.opencck.org/) — российские домены и сети;
- [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) — базовые geosite-категории;
- [hydraponique/roscomvpn-geosite](https://github.com/hydraponique/roscomvpn-geosite) — дополнительные geosite-категории;
- [hydraponique/roscomvpn-geoip](https://github.com/hydraponique/roscomvpn-geoip) — базовый `geoip.dat`;
- [v2fly/geoip](https://github.com/v2fly/geoip) — сборщик GeoIP.
