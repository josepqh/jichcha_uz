# Vaqtinchalik joylash: sayt Vercel'da, API shu kompyuterda

Server olinmaguncha ishlatiladigan sxema:

```
brauzer ──https──▶ Vercel (sahifalar + /api proksi) ──▶ ngrok tunnel ──▶ shu Mac'dagi Docker stack
```

- Sahifalar (93 ta prerender sahifa, FAQ, dizayn) doim ochiladi: ular Vercel'da turadi.
- Fayl aylantirish, kirish va akkaunt **faqat Mac yoniq va Docker ishlab turganda** ishlaydi.
- ngrok bepul tarifining cheklovlari bor (oyiga trafik va so'rovlar soni). Oz sonli foydalanuvchiga ko'rsatish uchun yetadi, ommaviy ishga tushirish uchun emas.
- Brauzer faqat Vercel domeni bilan gaplashadi, shuning uchun cookie va sessiya oddiy saytdagidek ishlaydi.

## 1. ngrok (bir marta)

1. <https://dashboard.ngrok.com> da ro'yxatdan o'ting.
2. **Your Authtoken** sahifasidan tokenni nusxalab, `.env` faylidagi `NGROK_AUTHTOKEN=` qatoriga qo'ying.
3. **Domains** bo'limida bepul doimiy domenni oling (masalan, `abc-xyz.ngrok-free.app`). Uni `.env` dagi `NGROK_DOMAIN=` ga `https://`siz yozing.

## 2. Vercel (bir marta)

1. <https://vercel.com> ga GitHub akkaunt bilan kiring va **Add New → Project → Import** orqali `jichcha_uz` reposini tanlang.
2. **Root Directory**: `frontend`. Framework: **Other**. Build sozlamalari `frontend/vercel.json` dan olinadi.
3. **Environment Variables**:
   | Nom | Qiymat |
   |---|---|
   | `API_ORIGIN` | `https://<NGROK_DOMAIN>` |
   | `EDGE_SECRET` | `.env` dagi `EDGE_SECRET` bilan bir xil |
   | `SITE_URL` | Vercel bergan manzil, masalan `https://jichcha-uz.vercel.app` |
   | `VITE_LEGAL_NAME`, `VITE_CONTACT_EMAIL`, `VITE_TELEGRAM_BOT_USERNAME` | ixtiyoriy |
4. **Deploy**. Tayyor bo'lgach, manzilni `.env` dagi `VERCEL_ORIGIN=` ga yozing (masalan `https://jichcha-uz.vercel.app`).

`main` branch'ga har bir push saytni avtomatik yangilaydi.

Google bilan kirish yoqilgan bo'lsa, Google Cloud Console'da OAuth client'ning **Authorized JavaScript origins** ro'yxatiga Vercel manzilini qo'shing.

## 3. API'ni ishga tushirish (har safar)

```bash
docker compose -f compose.yaml -f compose.tunnel.yaml up -d --build --wait
```

To'xtatish:

```bash
docker compose -f compose.yaml -f compose.tunnel.yaml down
```

Tekshirish: `https://<vercel-manzil>/api/v1/health/` `{"status":"ok"}` qaytarishi kerak.

## Xavfsizlik eslatmalari

- ngrok manzili ham ochiq, lekin u orqali to'g'ridan-to'g'ri kelgan so'rovlar rad etiladi: backend faqat Vercel qo'shadigan `EDGE_SECRET` header'i bor so'rovlarni qabul qiladi. Shu sabab IP limitlarini aylanib o'tib bo'lmaydi.
- `EDGE_SECRET`, `NGROK_AUTHTOKEN` faqat `.env` va Vercel sozlamalarida turadi, repoga tushmaydi.
- Mac'da Docker stack production sozlamalari bilan ishlaydi: admin panel uchun email tasdiqlash va ikki bosqichli kirish kerak.
- Server olinganda bu sxema kerak bo'lmaydi: `docs/DEPLOY.md` bo'yicha to'liq serverga ko'chiriladi.
