# jichcha'ni serverga chiqarish

Bu hujjat loyihani birinchi marta serverga joylash va keyin yangilash tartibini tushuntiradi.
Buyruqlar Ubuntu 24.04 / Debian 13 uchun yozilgan.

## 1. Ishga tushirishdan oldin qaror qilinadiganlar

| Masala | Nima qilish kerak |
|---|---|
| **Server qayerda** | "Shaxsga doir maʼlumotlar toʻgʻrisida"gi Qonunga koʻra Oʻzbekiston fuqarolarining shaxsiy maʼlumotlari (email, akkaunt) Oʻzbekistondagi serverlarda saqlanishi talab qilinadi. Hostingni shuni hisobga olib tanlang va yurist bilan tasdiqlang. |
| **Server quvvati** | Kamida 4 vCPU, 8 GB RAM, 80 GB SSD. ClamAV ~1,5 GB, LibreOffice ishlayotganda 1–2 GB xotira oladi. |
| **Domen** | `jichcha.uz` kabi domen va uning DNS'ida serverga qaratilgan `A` (va `AAAA`) yozuv. `www` ham kerak boʻlsa, unga ham yozuv qoʻshing. |
| **Email (SMTP)** | Parolni tiklash xatlari uchun SMTP xizmati (masalan, korporativ pochta yoki tranzaksion email xizmati). |
| **Huquqiy maʼlumot** | Xizmat egasining nomi va aloqa emaili (`VITE_LEGAL_NAME`, `VITE_CONTACT_EMAIL`). Maxfiylik siyosati va shartlar matnini yurist koʻrib chiqsin. |
| **Telegram bot tokeni** | Token chatda yoki boshqa joyda ochiq qolgan boʻlsa, BotFather'da `/revoke` qilib yangisini oling. |

## 2. Serverni tayyorlash

```bash
sudo apt update && sudo apt install -y ca-certificates curl git ufw
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"   # keyin qayta kiring
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 443/udp && sudo ufw enable
```

SSH'ga faqat kalit bilan kirishni yoqing (`PasswordAuthentication no`). Boshqa portlar ochilmaydi: Postgres,
Redis va ichki servislar tashqaridan koʻrinmaydi.

## 3. Sozlamalar

```bash
git clone <repo-url> jichcha && cd jichcha
cp .env.example .env
cp backup.env.example backup.env   # tashqi zaxira uchun (tavsiya)
```

`.env`da toʻldiriladiganlar:

- `DOMAIN` — masalan `jichcha.uz`.
- `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `BOT_API_SECRET`, `TELEGRAM_WEBHOOK_SECRET` — tasodifiy qiymatlar:
  `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`.
- `MAIL_BACKEND=smtp`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `DEFAULT_FROM_EMAIL`.
- `VITE_LEGAL_NAME`, `VITE_CONTACT_EMAIL`.
- Ixtiyoriy: `GOOGLE_CLIENT_ID` + `VITE_GOOGLE_CLIENT_ID`, `TURNSTILE_SECRET_KEY` + `VITE_TURNSTILE_SITE_KEY`,
  `SENTRY_DSN`, `TELEGRAM_BOT_TOKEN`, `ALERT_TELEGRAM_CHAT_ID`.
- `THROTTLE_*` qatorlari boʻlsa — **oʻchiring** (ular faqat lokal testlar uchun).

Tekshiring:

```bash
python3 deploy/check_env.py
```

`OK: ready for production.` chiqmaguncha davom etmang.

## 4. Birinchi ishga tushirish

```bash
docker compose -f compose.yaml -f compose.prod.yaml --profile bot up -d --build --wait
docker compose -f compose.yaml -f compose.prod.yaml exec backend python manage.py createsuperuser
```

- Birinchi start bir necha daqiqa davom etadi: ClamAV virus bazasini yuklaydi, Caddy HTTPS sertifikatini oladi.
- Bot kerak boʻlmasa `--profile bot`ni olib tashlang.
- Admin panel: `https://DOMAIN/uz/admin`. Yaratilgan superuser bilan kiring, keyin:
  1. Akkaunt sahifasida emailni tasdiqlang (xat keladi, SMTP sozlangan boʻlishi kerak).
  2. "Xavfsizlik" boʻlimida ikki bosqichli kirishni yoqing (Google Authenticator, Authy va hokazo).
  Usiz admin panel ochilmaydi (`STAFF_REQUIRE_2FA`).
- Django'ning oʻz `/admin/` sahifasi productionda oʻchiq: unda ikki bosqichli kirish yoʻq. Kerak boʻlsa,
  `.env`da `DJANGO_ADMIN_URL=admin/<topib boʻlmaydigan-nom>/` qiling va ishingiz tugagach yana boʻshating.

Tekshirish:

```bash
curl -s https://DOMAIN/api/v1/health/          # {"status":"ok",...}
curl -sI https://DOMAIN/uz | head -1            # HTTP/2 200
```

Saytda bitta faylni aylantirib koʻring, botga `/start` yozing.

## 5. Ogohlantirishlar va monitoring

1. Botni jamoa Telegram guruhiga qoʻshing va guruhda `/id` yozing.
2. Chiqqan raqamni `.env`dagi `ALERT_TELEGRAM_CHAT_ID`ga yozing va qayta ishga tushiring
   (`docker compose ... up -d monitor`).
3. Tashqi uptime xizmatini (masalan, UptimeRobot) `https://DOMAIN/api/v1/health/` manziliga ulang:
   server butunlay oʻchib qolsa, ichki monitor xabar yubora olmaydi.

`monitor` har 5 daqiqada DB, Redis, disk, navbatlar, worker'lar, ClamAV va xatolar ulushini tekshiradi.
Muammo boʻlsa bir marta, tuzalganda yana bir marta yozadi.

## 6. Zaxira nusxalar

- Har kuni `pg_dump` qilinadi, serverda 7 kunlik nusxa qoladi.
- `backup.env` toʻldirilsa, har bir nusxa tashqi saqlash joyiga (S3-mos xizmat) shifrlangan holda ham
  koʻchiriladi va 30 kun saqlanadi. Shifrlash parolini parol menejerida saqlang: usiz zaxirani ochib boʻlmaydi.
- Oyiga bir marta tiklashni sinab koʻring:

```bash
docker compose -f compose.yaml -f compose.prod.yaml cp db-backup:/backups/<fayl>.dump .
docker compose -f compose.yaml -f compose.prod.yaml exec -T db pg_restore --clean --if-exists -U jichcha -d jichcha < <fayl>.dump
```

Foydalanuvchi fayllari ataylab zaxiralanmaydi: ular bir necha soatda oʻchadi.

## 7. Yangilash va orqaga qaytish

```bash
git pull
python3 deploy/check_env.py
docker compose -f compose.yaml -f compose.prod.yaml --profile bot up -d --build --wait
```

Migratsiyalar `migrate` servisida avtomatik bajariladi. Muammo chiqsa:

```bash
git checkout <oldingi-commit>
docker compose -f compose.yaml -f compose.prod.yaml --profile bot up -d --build --wait
```

Migratsiya bazani oʻzgartirgan boʻlsa, avval zaxiradan tiklang (6-boʻlim).

## 8. Xavfsizlik roʻyxati

- [ ] `deploy/check_env.py` xatosiz.
- [ ] Faqat 22, 80, 443 portlar ochiq; SSH faqat kalit bilan.
- [ ] Bot tokeni yangilangan (ochiq qolgan boʻlsa).
- [ ] `backup.env` toʻldirilgan, tiklash bir marta sinab koʻrilgan.
- [ ] `ALERT_TELEGRAM_CHAT_ID` va tashqi uptime monitori ulangan.
- [ ] Maxfiylik siyosati va shartlarni yurist koʻrib chiqqan, hosting joylashuvi qonunga mos.
- [ ] Admin akkauntida kuchli parol; xodimlar soni minimal.
