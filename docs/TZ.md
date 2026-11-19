# Texnik topshiriq (TZ): Fayl konvertor va tahrirlash platformasi

> Versiya: 0.2 (qoralama) · Sana: 2026-11-10 · Holat: buyurtmachi tomonidan tasdiqlangan (2026-11-10)
> Oʻzgarish (2026-11-17, buyurtmachi qarori): e-kitob konvertatsiyasi (F-29) va matn muharriri (F-53) loyiha doirasidan chiqarildi; ular bilan birga Calibre ham olib tashlandi.
>
> Qoʻshildi (2026-11-18): FAQ sahifasi (F-78), siqishdan oldin/keyin taqqoslash slayderi (F-33), email tasdiqlash, akkauntda parolni oʻzgartirish, ikki bosqichli kirish (TOTP; admin panel uchun majburiy), PWA manifest. Django `/admin/` productionda sukut boʻyicha oʻchiq.
>
> Oʻzgarish (2026-11-19, buyurtmachi qarori): platforma nomi **jichcha**. Yangi dizayn: header ostida boʻlimlar paneli (PDF, Word, Excel, PowerPoint, Suratlar, Arxivlar), har bir boʻlim alohida sahifada faqat oʻz vositalarini koʻrsatadi; bosh sahifada faylni tashlab, mos vositani tanlash.
> 6-qism (2026-11-17): admin panel (F-70–F-75), SEO prerender va sitemap (F-76), surat muharriri (F-47–F-49), matn muharriri (F-53), natijadan keyingi amal, parolli PDF va arxivlar (F-30), Telegram'ga ogohlantirishlar, Turnstile, tashqi zaxira, accessibility auditi, yuklama sinovi va ishga tushirish yoʻriqnomasi (docs/DEPLOY.md).
> 5-qism (2026-11-17): Telegram bot ishlab chiqildi (F-65, F-66, F-68, F-69): fayl yuborilsa saytdagi boʻlimlarga mos amallar tugmalari, suratlar albomi → PDF, PDF albomi → birlashtirish, uch til, 20 MB dan katta faylga sayt havolasi. Har bir Telegram foydalanuvchisi alohida limit va vazifalarga ega. Botni web akkauntga ulash (F-67) 2-bosqichda.
> 4-qism (2026-11-16): arxivlar (F-26–F-28: ochish, ZIP/7Z yaratish, formatni almashtirish; parolli arxiv F-30 hali yoʻq) va e-kitoblar (F-29, qoʻshimcha FB2) ishlab chiqildi. Ishga tushirishga tayyorgarlik: ClamAV tekshiruvi, kunlik DB zaxirasi, health check, Sentry (ixtiyoriy), CI, worker konteynerlarini cheklash, maxfiylik siyosati va foydalanish shartlari sahifalari.
> 3-qism (2026-11-12): Office → PDF, PDF birlashtirish/boʻlish/tartiblash/siqish va PDF → surat ishlab chiqildi (F-18–F-20, F-22, F-35, F-37–F-39). PDF → Word (F-21) AGPL litsenziya masalasi hal boʻlguncha qoldirildi.
> Tuzatishlar (2026-11-16): Google orqali kirgan (parolsiz) akkauntni oʻchirish uchun soʻnggi 10 daqiqadagi Google tasdigʻi talab qilinadi; konvertatsiya limiti endi akkaunt yoki mehmon brauzeri boʻyicha, IP boʻyicha esa faqat mehmonlar uchun umumiy chegara (CGNAT ortidagi foydalanuvchilar bir-birini toʻsmaydi); Docker image'lari (LibreOffice'li `worker-office` bilan) qayta yigʻildi.
> 2-qism (2026-11-10): akkauntlar ishlab chiqildi (F-57, F-59, F-60, F-64; Google kirish `GOOGLE_CLIENT_ID` bilan yoqiladi).
> 1-qism (2026-11-10): surat vositalari ishlab chiqildi; rejadan farqlar 9 va 11-bo'limlarda belgilangan.
> 0.2 o'zgarishi: platforma ishga tushganda to'liq bepul bo'ladi; Pro tarif va to'lovlar alohida "Pro bosqichi"ga ko'chirildi.
> Ishchi nomi: **jichcha** **[Taxmin]**: papka nomidan olindi, yakuniy brend nomi ochiq savol.

---

## 1. Loyiha haqida qisqacha

| | |
|---|---|
| **Ta'rif** | Istalgan fayl formatini boshqasiga o'zgartirish, suratlarni siqish va PDF, surat va hujjatlarni brauzerning o'zida tahrirlash imkonini beruvchi uch tilli web platforma va Telegram bot. |
| **Muammo** | O'zbekistondagi foydalanuvchilar fayl bilan oddiy ish uchun (PNG → PDF, Word → PDF, suratni siqish) xorijiy saytlarga murojaat qiladi: ular o'zbek tilida emas, bepul limiti tez tugaydi, obuna narxi dollarda va mahalliy kartalar (Uzcard, Humo) bilan to'lab bo'lmaydi. |
| **Maqsad** | Bitta joyda, o'zbek tilida, ro'yxatdan o'tmasdan va bepul ishlaydigan fayl vositalari to'plamini yaratish va auditoriya to'plash. |
| **Daromad modeli** | **Hozircha yo'q: platforma to'liq bepul.** Barcha vositalar hamma uchun bepul, limitlar faqat serverni suiiste'moldan himoya qilish uchun. Keyinchalik Pro tarif (Click/Payme) qo'shiladi (15-bo'lim, "Pro bosqichi"). |

---

## 2. Biznes maqsadlar va KPI

Barcha raqamlar **[Taxmin]**: buyurtmachi bilan aniqlashtiriladi.

| # | Ko'rsatkich | Maqsad (ishga tushgandan 6 oy ichida) |
|---|---|---|
| K-1 | Oylik faol foydalanuvchilar (MAU, web + bot) | 20 000 |
| K-2 | Oyiga muvaffaqiyatli konvertatsiyalar | 150 000 |
| K-3 | Konvertatsiya muvaffaqiyat darajasi | ≥ 97% |
| K-4 | Ro'yxatdan o'tgan foydalanuvchilar ulushi (MAU ichida) | ≥ 15% |
| K-5 | 30 kunlik qaytish (retention): bir oy ichida yana foydalanganlar | ≥ 25% |
| K-6 | O'rtacha konvertatsiya vaqti (10 MB gacha fayl) | ≤ 10 s |
| K-7 | Organik (SEO) trafik ulushi | ≥ 50% |
| K-8 | Telegram bot foydalanuvchilari | 5 000 |

Pro bosqichi KPI'lari (Pro'ga o'tish foizi, obunachilar soni, daromad) o'sha bosqich boshlanishida belgilanadi.

---

## 3. Maqsadli auditoriya va personalar

### Persona 1: Dilnoza, talaba (20 yosh, Toshkent)
- **Ehtiyoj:** referat va kurs ishlarini Word → PDF qilish, telefondagi suratlarni (HEIC/JPG) bitta PDF'ga yig'ish, katta faylni Telegram yoki portal limitiga sig'dirish uchun siqish.
- **Og'riq:** xorijiy saytlar ingliz tilida, reklama ko'p, ro'yxatdan o'tishni talab qiladi. Asosan telefondan ishlaydi.
- **Kanal:** telefon brauzeri, Telegram bot.

### Persona 2: Rustam, buxgalter / ofis xodimi (38 yosh, Samarqand)
- **Ehtiyoj:** PDF hujjatlarni birlashtirish, sahifa ajratish, skan hujjatni Word'ga o'tkazish, Excel → PDF, hujjatga imzo yoki muhr surati qo'yish.
- **Og'riq:** maxfiy hujjatlarni noma'lum saytga yuklashdan qo'rqadi, kuniga o'nlab fayl bilan ishlaydi, bepul limit yetmaydi.
- **Kanal:** kompyuter. Kelajakdagi Pro tarifning asosiy nomzodi (Click/Payme orqali to'lashga tayyor).

### Persona 3: Aziz, SMM mutaxassis / frilanser (26 yosh)
- **Ehtiyoj:** suratlarni WEBP'ga o'tkazish, siqish, o'lchamini o'zgartirish, kesish, fonni olib tashlash; bir vaqtda 50+ surat bilan ishlash (batch).
- **Og'riq:** har bir vosita alohida saytda, ommaviy (batch) ishlash pullik.
- **Kanal:** kompyuter. Kelajakdagi Pro tarifning nomzodi.

### Persona 4: Admin (platforma jamoasi)
- **Ehtiyoj:** foydalanuvchilar, xatolik bergan vazifalar va server yuklamasini kuzatish, limitlarni sozlash.

---

## 4. Raqobatchilar tahlili

Faqat umumma'lum xalqaro xizmatlar keltirildi. O'zbekiston bozoridagi mahalliy raqobatchilar (sayt va Telegram botlar) alohida tadqiq qilinishi kerak **[Taxmin: mahalliy yirik web raqobatchi yo'q deb faraz qilindi, tekshirilmagan]**.

| Raqobatchi | Kuchli tomoni | Zaif tomoni (biz uchun imkoniyat) | Biz nimasi bilan farq qilamiz |
|---|---|---|---|
| iLovePDF | PDF vositalari to'liq, qulay UI | O'zbek tili yo'q, mahalliy to'lov yo'q | O'zbek tili, to'liq bepul, Telegram bot |
| Smallpdf | Sodda dizayn, kuchli brend | Bepul limit juda kichik | To'liq bepul, ro'yxatdan o'tmasdan ishlash |
| Convertio / CloudConvert | Yuzlab format | Interfeys texnik, narx dollarda | Asosiy formatlarga e'tibor, bepul; keyinchalik so'mdagi Pro tarif |
| TinyPNG / Squoosh | Surat siqishda eng yaxshi natija | Faqat bitta vazifa | Siqish + konvertatsiya + tahrir bitta joyda |
| Telegram konvertor botlar | Telegram ichida, tez | Ishonchsiz, reklama ko'p, tahrir yo'q | Web + bot bitta akkaunt, bitta limit, maxfiylik kafolati |

**Asosiy farqlovchi qiymat:** "Fayl bilan har qanday ish, o'zbek tilida, telefondan ham, Telegram'dan ham, bepul."

---

## 5. Foydalanuvchi rollari va ruxsatlar

Platforma to'liq bepul: barcha vositalar hamma uchun ochiq. Limitlar pul uchun emas, serverni botlar va suiiste'moldan himoya qilish uchun qo'yiladi. Ro'yxatdan o'tish ixtiyoriy, uning foydasi kattaroq limit va vazifalar tarixi.

| Imkoniyat | Mehmon (ro'yxatdan o'tmagan) | Ro'yxatdan o'tgan foydalanuvchi | Admin |
|---|---|---|---|
| Barcha vositalar (konvertatsiya, siqish, tahrir) | ✅ bepul | ✅ bepul | ✅ |
| Maksimal fayl hajmi | 50 MB | 200 MB | — |
| Kunlik vazifalar soni | 20 | 100 | — |
| Batch (bir vaqtda fayllar) | 10 | 30 | — |
| Fayllar serverda saqlanishi | 1 soat | 6 soat | — |
| Vazifalar tarixi | ❌ | ✅ 30 kun | ✅ |
| OCR (skandan matn, 2-bosqichdan) | 5 sahifa/kun | 50 sahifa/kun | ✅ |
| Reklama | ❌ | ❌ | — |
| Telegram botni akkauntga ulash | ❌ | ✅ | — |
| Admin panel | ❌ | ❌ | ✅ |

Barcha limit raqamlari **[Taxmin]** va admin paneldan sozlanadi. Telegram bot orqali fayl hajmi Telegram Bot API cheklovi bilan 20 MB. Pro bosqichida jadvalga "Pro foydalanuvchi" ustuni qo'shiladi.

---

## 6. Funksional talablar

Ustuvorlik: **M** = Must (MVP), **S** = Should, **C** = Could, **W** = Won't (bu loyihada emas).

### 6.1. Fayl yuklash va umumiy oqim

| ID | Tavsif | Ust. |
|---|---|---|
| F-01 | Faylni drag & drop, "Fayl tanlash" tugmasi va telefon galereyasidan yuklash | M |
| F-02 | Bir nechta faylni bir vaqtda yuklash (batch), progress bar bilan | M |
| F-03 | Faylni URL orqali yuklash | S |
| F-04 | Google Drive / Dropbox'dan yuklash | C |
| F-05 | Format faylning ichki tarkibi (magic bytes) orqali aniqlanadi, faqat kengaytmaga ishonilmaydi | M |
| F-06 | Yuklangan fayl antivirus (ClamAV) orqali tekshiriladi | M |
| F-07 | Natijani yuklab olish, bir nechta natija bo'lsa ZIP sifatida | M |
| F-08 | Natijani Telegram'ga yuborish (ulangan akkaunt uchun) | S |
| F-09 | Fayllar belgilangan muddatdan keyin avtomatik va qaytarib bo'lmas holda o'chiriladi; foydalanuvchi "Hozir o'chirish" tugmasini bosishi mumkin | M |
| F-10 | Vazifa holati real vaqtda ko'rsatiladi (navbatda / ishlanmoqda / tayyor / xato) | M |

### 6.2. Konvertatsiya: suratlar

| ID | Tavsif | Ust. |
|---|---|---|
| F-11 | PNG, JPG/JPEG, WEBP, GIF, BMP, TIFF o'zaro konvertatsiya | M |
| F-12 | HEIC/HEIF (iPhone) → JPG/PNG/WEBP/PDF | M |
| F-13 | Surat(lar) → PDF: bir nechta suratdan bitta PDF, tartibni sudrab o'zgartirish, sahifa o'lchami (A4/Letter/surat o'lchamida), yo'nalish va chekka (margin) tanlash | M |
| F-14 | SVG → PNG/JPG/PDF | S |
| F-15 | Surat → ICO (favicon) | C |
| F-16 | AVIF o'qish va yozish | S |
| F-17 | RAW formatlar (CR2, NEF, ARW) | W |

### 6.3. Konvertatsiya: hujjatlar

| ID | Tavsif | Ust. |
|---|---|---|
| F-18 | Word (DOC, DOCX, ODT, RTF) → PDF | M |
| F-19 | Excel (XLS, XLSX, ODS, CSV) → PDF | M |
| F-20 | PowerPoint (PPT, PPTX, ODP) → PDF | M |
| F-21 | PDF → Word (DOCX), matnli PDF uchun | M |
| F-22 | PDF → JPG/PNG (har bir sahifa alohida surat yoki ZIP) | M |
| F-23 | PDF → Excel, PDF → PowerPoint | S |
| F-24 | TXT, HTML, Markdown ↔ PDF/DOCX | S |
| F-25 | OCR: skanerlangan PDF/surat → tahrirlanadigan Word yoki qidiriladigan PDF (o'zbek lotin, kirill, rus, ingliz tillari) | S |

### 6.4. Konvertatsiya: arxiv va e-kitob

| ID | Tavsif | Ust. |
|---|---|---|
| F-26 | Arxivdan chiqarish: ZIP, RAR, 7Z, TAR, GZ; ichidagi fayllar ro'yxati va alohida yuklab olish | M |
| F-27 | Fayllarni ZIP yoki 7Z arxivga yig'ish | M |
| F-28 | Arxiv formatini o'zgartirish (RAR → ZIP va h.k.) | S |
| F-29 | E-kitob: EPUB ↔ MOBI/AZW3, EPUB/MOBI → PDF, PDF/DOCX → EPUB | M |
| F-30 | Parol bilan himoyalangan arxivni ochish (foydalanuvchi parolni kiritadi) | C |

### 6.5. Siqish (hajmni kichraytirish)

| ID | Tavsif | Ust. |
|---|---|---|
| F-31 | Surat siqish: "Kuchli / O'rtacha / Sifatli" rejimlari va qo'lda sifat foizi (slider) | M |
| F-32 | Maqsadli hajm bo'yicha siqish ("500 KB dan oshmasin") | S |
| F-33 | Siqishdan oldin va keyin taqqoslash (slider bilan), hajm qancha kamaygani foizda | M |
| F-34 | EXIF metama'lumotlarni (GPS, kamera) olib tashlash: standart holatda yoqilgan | M |
| F-35 | PDF siqish (3 daraja) | M |
| F-36 | Video siqish | W (keyingi loyiha) |

### 6.6. PDF amallari

| ID | Tavsif | Ust. |
|---|---|---|
| F-37 | PDF birlashtirish (merge), fayllar tartibini sudrab o'zgartirish | M |
| F-38 | PDF bo'lish (split): diapazon bo'yicha, har bir sahifa alohida | M |
| F-39 | Sahifalarni o'chirish, aylantirish, tartibini o'zgartirish (sahifa miniatyuralari orqali) | M |
| F-40 | Sahifa raqamlarini qo'shish | S |
| F-41 | Suv belgisi (matn yoki surat) | S |
| F-42 | PDF ustiga matn, surat, shakl qo'shish (annotatsiya) | S |
| F-43 | Imzo: chizish, yozish yoki surat sifatida yuklash va joylash | S |
| F-44 | PDF'ga parol qo'yish va parolni olib tashlash (parol ma'lum bo'lsa) | S |
| F-45 | PDF formalarini to'ldirish | C |
| F-46 | Elektron raqamli imzo (ERI / E-IMZO) | W **[Taxmin: keyingi bosqichda ko'rib chiqiladi]** |

### 6.7. Surat tahriri

| ID | Tavsif | Ust. |
|---|---|---|
| F-47 | Kesish (crop): erkin va tayyor nisbatlar (1:1, 4:5, 16:9, 3×4 hujjat surati) | M |
| F-48 | O'lchamni o'zgartirish: piksel yoki foizda, nisbatni saqlash bilan; batch uchun ham | M |
| F-49 | Aylantirish va oyna aksi (flip) | M |
| F-50 | Fonni olib tashlash (AI) | S |
| F-51 | Yorqinlik, kontrast, to'yinganlik, oq-qora filtr | S |
| F-52 | Suratga matn va suv belgisi qo'shish | C |

### 6.8. Hujjat matni tahriri

| ID | Tavsif | Ust. |
|---|---|---|
| F-53 | TXT va Markdown fayllarni brauzerda tahrirlash va istalgan formatda saqlash | M |
| F-54 | DOCX faylni brauzerda oddiy tahrirlash (matn, sarlavha, qalin/kursiv, ro'yxat, jadval) va DOCX/PDF sifatida saqlash. Murakkab formatlash (makros, ko'p ustunli maket) saqlanishi kafolatlanmaydi; bu foydalanuvchiga ogohlantirish bilan ko'rsatiladi | S |
| F-55 | DOCX/XLSX/PPTX'ni to'liq ofis muharririda tahrirlash (ONLYOFFICE yoki Collabora integratsiyasi) | C (3-bosqich, litsenziya tekshiriladi) |
| F-56 | PDF ichidagi mavjud matnni to'g'ridan-to'g'ri tahrirlash | C |

### 6.9. Akkaunt

| ID | Tavsif | Ust. |
|---|---|---|
| F-57 | Ro'yxatdan o'tish va kirish: email + parol, Google orqali (ixtiyoriy, kattaroq limit uchun) | M |
| F-58 | Telegram orqali kirish (Telegram Login Widget) | S |
| F-59 | Parolni tiklash (email orqali) | M |
| F-60 | Shaxsiy kabinet: vazifalar tarixi, limitlar qoldig'i, til va mavzu sozlamalari | M |
| F-64 | Akkauntni o'chirish (barcha ma'lumotlari bilan) | M |

F-61–F-63 (to'lovlar) 6.13-bo'limga ko'chirildi.

### 6.10. Telegram bot

| ID | Tavsif | Ust. |
|---|---|---|
| F-65 | Botga fayl yuborish → bot mumkin bo'lgan amallarni inline tugmalar bilan taklif qiladi → natijani qaytaradi | M |
| F-66 | Bir nechta suratni yuborib "PDF qilish" | M |
| F-67 | Botni web akkauntga ulash (bitta limit va tarix) | S |
| F-68 | Bot uch tilda (uz / ru / en) | M |
| F-69 | Telegram Bot API limiti tufayli botga 20 MB dan katta fayl yuborilsa, web sahifaga havola beriladi | M |

### 6.11. Admin panel

| ID | Tavsif | Ust. |
|---|---|---|
| F-70 | Dashboard: kunlik vazifalar, xatolar, faol foydalanuvchilar, eng ko'p ishlatilgan vositalar | M |
| F-71 | Foydalanuvchilar ro'yxati, qidiruv, bloklash | M |
| F-72 | Server yuklamasi: navbat uzunligi, worker holati, xotira (storage) bandligi | M |
| F-73 | Xato bergan vazifalar jurnali (fayl mazmunisiz, faqat metama'lumot) | M |
| F-74 | Limitlarni rol bo'yicha sozlash (mehmon / ro'yxatdan o'tgan) | M |
| F-75 | Formatlar/vositalarni yoqish-o'chirish | S |

### 6.12. Kontent va SEO

| ID | Tavsif | Ust. |
|---|---|---|
| F-76 | Har bir vosita uchun alohida SEO sahifa ("PNG dan PDF ga", "Word dan PDF ga") 3 tilda | M |
| F-77 | Bosh sahifada vositalar katalogi va qidiruv ("png pdf" yozsa vosita topiladi) | M |
| F-78 | Maxfiylik siyosati, foydalanish shartlari, FAQ | M |
| F-79 | Blog / qo'llanmalar | C |

### 6.13. Pro tarif (keyingi bosqich, hozirgi relizlarda yo'q)

Bu funksiyalar MVP va 2–3-bosqichlarga kirmaydi. Ular 15-bo'limdagi "Pro bosqichi"da bajariladi.

| ID | Tavsif | Ust. |
|---|---|---|
| F-61 | Pro obuna: oylik va yillik tariflar, Click va Payme orqali to'lov | Pro bosqichi |
| F-62 | Obuna avtomatik uzaytirilmaydi; muddat tugashidan 3 kun oldin email va Telegram eslatma | Pro bosqichi |
| F-63 | Uzum Bank / Uzum Nasiya orqali to'lov | Pro bosqichi (C) |
| F-80 | Tariflar sahifasi (/pricing) va limit tugaganda Pro taklifi | Pro bosqichi |
| F-81 | Admin: tariflar, obunalar va to'lovlar ro'yxati, foydalanuvchiga Pro berish | Pro bosqichi |

Pro tarif bepul imkoniyatlarni olib qo'ymaydi: hozir bepul bo'lgan vositalar bepul qoladi, Pro faqat kattaroq limit va qo'shimcha qulayliklar beradi **[Taxmin]**.

---

## 7. User stories (asosiy)

**US-01 (Mehmon, surat → PDF)**
Men talaba sifatida bir nechta suratni bitta PDF qilishni xohlayman, chunki o'qituvchiga bitta fayl yuborishim kerak.
- *Given* men ro'yxatdan o'tmaganman va "JPG → PDF" sahifasidaman, *when* 5 ta JPG yuklab, tartibini o'zgartirib, "PDF qilish"ni bossam, *then* 15 soniya ichida tanlangan tartibdagi 5 sahifali PDF yuklab olishga tayyor bo'ladi.
- *Given* men HEIC surat yuklasam, *then* u avtomatik qabul qilinadi va PDF'ga qo'shiladi.
- *Given* men 50 MB dan katta fayl yuklasam, *then* yuklash boshlanishidan oldin limit haqida xabar va ro'yxatdan o'tish taklifi (200 MB gacha) ko'rsatiladi.

**US-02 (Surat siqish)**
Men SMM mutaxassis sifatida 30 ta suratni birdaniga siqishni xohlayman, chunki sayt tez yuklanishi kerak.
- *Given* men ro'yxatdan o'tganman, *when* 30 ta PNG yuklab "O'rtacha" rejimni tanlasam, *then* hammasi bepul siqiladi, har biri uchun hajm farqi ko'rsatiladi va bitta ZIP yuklab olinadi.
- *Given* men mehmonman va 30 ta fayl tanlasam, *then* birinchi 10 tasi qabul qilinadi va qolganlari uchun ro'yxatdan o'tish taklif qilinadi.
- *Given* siqish yakunlandi, *then* natijada EXIF GPS ma'lumoti yo'q.

**US-03 (PDF birlashtirish)**
Men buxgalter sifatida bir nechta PDF'ni birlashtirishni xohlayman, chunki hisobotni bitta fayl qilib topshiraman.
- *Given* 4 ta PDF yukladim, *when* tartibini o'zgartirib "Birlashtirish"ni bossam, *then* sahifalar aynan shu tartibda bitta faylga yig'iladi.
- *Given* fayllardan biri parol bilan himoyalangan, *then* tizim o'sha fayl uchun parol so'raydi.

**US-04 (Word → PDF)**
Men talaba sifatida DOCX referatimni PDF qilishni xohlayman.
- *Given* o'zbek kirill va lotin harflari (o', g', ʻ, ҳ, қ) bor DOCX, *when* konvertatsiya qilsam, *then* PDF'da barcha harflar to'g'ri ko'rinadi va sahifalar soni asl hujjatdagidan ±1 dan farq qilmaydi.

**US-05 (Hujjat tahriri)**
Men ofis xodimi sifatida kompyuterimda Word bo'lmasa ham DOCX fayldagi matnni tuzatishni xohlayman.
- *Given* DOCX yukladim, *when* "Tahrirlash"ni tanlasam, *then* hujjat brauzer muharririda ochiladi, matnni o'zgartirib DOCX yoki PDF sifatida saqlay olaman.
- *Given* hujjatda qo'llab-quvvatlanmaydigan elementlar bor, *then* ochishdan oldin "ba'zi formatlash yo'qolishi mumkin" ogohlantirishi chiqadi.

**US-06 (Telegram bot)**
Men foydalanuvchi sifatida Telegram'dan chiqmasdan surat yuborib PDF olishni xohlayman.
- *Given* botga 3 ta surat yubordim, *when* "📄 PDF qilish" tugmasini bossam, *then* bot 3 sahifali PDF'ni qaytaradi.
- *Given* 20 MB dan katta fayl yubordim, *then* bot web sahifaga havola beradi.

**US-07 (Pro obuna, Pro bosqichida bajariladi)**
Men foydalanuvchi sifatida Pro'ni Click orqali sotib olishni xohlayman, chunki chet el kartam yo'q.
- *Given* men akkauntga kirganman, *when* "Pro oylik"ni tanlab Click orqali to'lasam, *then* to'lov tasdiqlangandan keyin 1 daqiqa ichida limitlarim Pro'ga o'zgaradi va email/Telegram'ga chek keladi.
- *Given* to'lov bekor qilindi, *then* obuna faollashmaydi va pul yechilmagani haqida xabar chiqadi.

**US-08 (Maxfiylik)**
Men buxgalter sifatida fayllarim serverda qolmasligini xohlayman, chunki ular maxfiy.
- *Given* vazifa tugadi, *when* "Hozir o'chirish"ni bossam, *then* asl fayl ham, natija ham darhol o'chiriladi va havola 404 qaytaradi.
- *Given* men hech narsa bosmadim, *then* fayllar rolimga belgilangan muddatdan keyin avtomatik o'chiriladi.

**US-09 (Admin)**
Men admin sifatida xato bergan vazifalarni ko'rishni xohlayman, chunki qaysi format muammoli ekanini bilishim kerak.
- *Given* oxirgi 24 soatda 40 ta xato bo'lgan, *when* "Xatolar" bo'limini ochsam, *then* ular vosita, format va xato turi bo'yicha guruhlangan holda ko'rinadi; fayl mazmuni ko'rinmaydi.

---

## 8. Sahifalar xaritasi va asosiy oqimlar

```
/ (Bosh sahifa: qidiruv + vositalar katalogi kategoriyalar bo'yicha)
├── /convert/{from}-to-{to}        (masalan /convert/png-to-pdf, har biri SEO sahifa)
├── /compress/image, /compress/pdf
├── /pdf/merge, /pdf/split, /pdf/organize, /pdf/sign, /pdf/watermark, /pdf/protect, /pdf/unlock
├── /image/crop, /image/resize, /image/rotate, /image/remove-bg
├── /edit/document                 (DOCX/TXT/MD muharriri)
├── /archive/extract, /archive/create
├── /ebook/{from}-to-{to}
├── /auth/login, /auth/register, /auth/reset
├── /account                       (tarix, limitlar, sozlamalar, Telegram ulash)
├── /task/{id}                     (natija sahifasi: yuklab olish, o'chirish, keyingi amal)
├── /privacy, /terms, /faq
└── /admin/*                       (admin panel)
```

Har bir sahifa `/uz/`, `/ru/`, `/en/` prefiksi bilan **[Taxmin: standart til o'zbek]**.

**Asosiy oqim (vosita sahifasi):**
1. Foydalanuvchi vositani tanlaydi (katalog, qidiruv yoki Google'dan to'g'ridan-to'g'ri).
2. Fayl(lar)ni yuklaydi → format va hajm tekshiriladi.
3. Sozlamalarni tanlaydi (sifat, sahifa o'lchami, tartib).
4. "Boshlash" → vazifa navbatga qo'yiladi → real vaqtda progress.
5. Natija sahifasi: yuklab olish, "Hozir o'chirish", "Keyingi amal" (masalan, PDF yaratildi → "Siqish"), Telegram'ga yuborish.

**To'lov oqimi (Pro bosqichida qo'shiladi, `/pricing` sahifasi bilan birga):** /pricing → tarif tanlash → (kirish yoki ro'yxatdan o'tish) → Click/Payme sahifasi → callback → obuna faollashadi → /account.

---

## 9. Dizayn yo'nalishi

- **Uslub:** toza, "asbob-uskuna" (utility) uslubi: oq/neytral fon, katta yuklash zonasi markazda, ortiqcha bezaksiz. Har bir vosita kategoriyasi o'z rangidagi ikonka bilan (PDF: qizil, surat: ko'k, hujjat: binafsha, arxiv: sariq, e-kitob: yashil).
- **Rang palitrasi (`ui-ux-pro-max` tavsiyasi, 1-qism ishlab chiqishda tanlandi):** Swiss minimal uslub; asosiy rang to'q apelsin (yorug' rejimda `#C2410C`, oq matn 5.2:1; qorong'i rejimda `#FB923C`, to'q matn 7.9:1), neytral "stone" kulrang shkala, muvaffaqiyat yashil va xato qizil. Tokenlar `frontend/src/index.css`da.
- **Shriftlar:** interfeys uchun Inter yoki Manrope (o'zbek lotin `oʻ`, `gʻ` va kirill harflarini to'liq qo'llab-quvvatlaydi). Raqamlar uchun tabular figures.
- **Ikonkalar:** lucide-react.
- **Mobile-first:** asosiy auditoriya telefondan kiradi. Yuklash zonasi telefonda galereya/kamera ochadi, tugmalar ≥ 44×44 px.
- **Ochiq va qorong'i rejim:** tizim sozlamasiga ergashadi, qo'lda almashtirish tugmasi bor.
- **Accessibility:** WCAG 2.2 AA; klaviatura bilan to'liq boshqaruv (drag & drop o'rniga tugmalar bilan tartiblash alternativasi), progress va holatlar `aria-live` orqali e'lon qilinadi, `prefers-reduced-motion` hisobga olinadi.
- **Reklama:** MVP'da yo'q. Keyinchalik qo'shilsa, yuklash zonasi va natija tugmasiga xalaqit bermaydigan joyda bo'ladi (18-bo'lim, ochiq savol).

---

## 10. Ma'lumotlar modeli

Fayl mazmuni ma'lumotlar bazasida saqlanmaydi; u obyekt xotirada (S3/MinIO) vaqtincha turadi.

```mermaid
erDiagram
    USER ||--o{ TASK : yaratadi
    USER ||--o| TELEGRAM_LINK : ulangan
    TASK ||--o{ TASK_FILE : o'z_ichiga_oladi
    TOOL ||--o{ TASK : bajaradi
    USER ||--o{ USAGE_COUNTER : hisoblanadi

    USER {
        uuid id PK
        string email UK
        string password_hash
        string language
        string auth_provider
        bool is_active
        timestamptz created_at
    }
    TELEGRAM_LINK {
        uuid id PK
        uuid user_id FK
        bigint telegram_id UK
        string username
    }
    LIMIT_POLICY {
        uuid id PK
        string role UK "guest | registered"
        int max_file_mb
        int daily_tasks
        int max_batch
        int retention_hours
        int daily_ocr_pages
    }
    TOOL {
        uuid id PK
        string slug UK
        string category
        string input_formats
        string output_formats
        bool is_enabled
    }
    TASK {
        uuid id PK
        uuid user_id FK "null = mehmon"
        string guest_session_id
        uuid tool_id FK
        string source "web | telegram"
        jsonb options
        string status
        string error_code
        int duration_ms
        timestamptz expires_at
        timestamptz created_at
    }
    TASK_FILE {
        uuid id PK
        uuid task_id FK
        string role "input | output"
        string storage_key
        string original_name
        string mime_type
        bigint size_bytes
        bool is_deleted
    }
    USAGE_COUNTER {
        uuid id PK
        uuid user_id FK
        string guest_key
        date day
        int tasks_count
        bigint bytes_processed
    }
```

Muhim indekslar: `TASK(user_id, created_at DESC)`, `TASK(expires_at)` (tozalash uchun), `TASK(status)` qisman indeks (faqat `failed`), `USAGE_COUNTER(user_id, day)` unikal.

Pro bosqichida `PLAN`, `SUBSCRIPTION` va `PAYMENT` jadvallari (`PAYMENT(provider, provider_txn_id)` unikal indeksi bilan) qo'shiladi, `LIMIT_POLICY`ga esa `pro` roli. Hozirgi tuzilma ularni oddiy migratsiya bilan qo'shishga tayyor.

---

## 11. API reja (REST, `/api/v1/`)

| Metod | Yo'l | Vazifa | Kim |
|---|---|---|---|
| GET | `/tools/` | Vositalar va formatlar katalogi | Hamma |
| POST | `/uploads/` | Yuklash uchun presigned URL olish (hajm va tur oldindan tekshiriladi). **1-qismda hali yo'q:** fayllar hozircha to'g'ridan-to'g'ri `/tasks/`ga multipart orqali yuklanadi | Hamma (limit bilan) |
| POST | `/tasks/` | Vazifa yaratish (tool, fayllar, sozlamalar), 202 qaytaradi | Hamma (limit bilan) |
| GET | `/tasks/{id}/` | Vazifa holati | Egasi |
| GET | `/tasks/{id}/events/` | Holat oqimi (SSE). **1-qismda hali yo'q:** frontend har soniyada `/tasks/{id}/` so'rovini yuboradi (polling) | Egasi |
| GET | `/tasks/{id}/download/` | Natijani yuklab olish uchun qisqa muddatli imzolangan havola | Egasi |
| DELETE | `/tasks/{id}/` | Fayllarni darhol o'chirish | Egasi |
| GET | `/tasks/` | Vazifalar tarixi (pagination) | Ro'yxatdan o'tgan foydalanuvchi |
| POST | `/auth/register/`, `/auth/login/`, `/auth/refresh/`, `/auth/logout/` | JWT autentifikatsiya | Hamma |
| POST | `/auth/google/`, `/auth/telegram/` | OAuth / Telegram Login | Hamma |
| POST | `/auth/password/reset/`, `/auth/password/confirm/` | Parol tiklash | Hamma |
| GET/PATCH/DELETE | `/me/` | Profil, til, akkauntni o'chirish | Foydalanuvchi |
| GET | `/me/usage/` | Limitlar qoldig'i | Hamma (mehmon uchun sessiya bo'yicha) |
| POST | `/telegram/link/` | Botni akkauntga ulash kodi | Foydalanuvchi |
| GET/PATCH | `/admin/...` | Foydalanuvchilar, vazifalar, limitlar, yuklama | Admin |

Pro bosqichida qo'shiladigan endpointlar: `GET /plans/`, `POST /payments/checkout/`, Click callback'lari (`/payments/click/prepare/`, `/payments/click/complete/`, imzo tekshiruvi bilan) va Payme JSON-RPC (`/payments/payme/`, Basic auth + IP tekshiruvi bilan).

"Egasi" mehmon uchun imzolangan `guest_session_id` cookie orqali aniqlanadi. Boshqa foydalanuvchining vazifasiga murojaat 404 qaytaradi (IDOR himoyasi).

---

## 12. Integratsiyalar

| Xizmat | Maqsad | Bosqich |
|---|---|---|
| Click | Pro obuna to'lovi | Pro bosqichi |
| Payme | Pro obuna to'lovi | Pro bosqichi |
| Uzum Bank | Qo'shimcha to'lov usuli | Pro bosqichi |
| **Telegram Bot API** (aiogram v3) | Bot | MVP |
| Telegram Login Widget | Telegram orqali kirish | 2-bosqich |
| **Google OAuth** | Google orqali kirish | MVP |
| Email (SMTP yoki tranzaksion email xizmati) | Parol tiklash, xabarnomalar | MVP |
| Reklama tarmog'i | Daromad (agar qaror qilinsa) | Hal qilinmagan (ochiq savol) |
| Google Drive / Dropbox | Fayl manbasi | 3-bosqich |

**Konvertatsiya dvigatellari (server tomonida):**

| Vazifa | Vosita | Litsenziya eslatmasi |
|---|---|---|
| Suratlar | libvips (pyvips) va Pillow, pillow-heif, cairosvg | LGPL / MIT tipidagi, muammosiz |
| Surat siqish | MozJPEG, oxipng/pngquant, libwebp | pngquant GPL: alohida jarayon sifatida chaqiriladi |
| Office → PDF | LibreOffice (headless) | MPL, muammosiz |
| PDF → DOCX | pdf2docx | Litsenziyasi ishga tushirishdan oldin tekshiriladi |
| PDF amallari | pypdf, pikepdf (qpdf) | BSD / MPL |
| PDF siqish va renderlash | Ghostscript yoki MuPDF | **AGPL**: tijoriy foydalanishdan oldin yuridik tekshiruv yoki tijoriy litsenziya kerak |
| OCR | Tesseract (uzb, uzb_cyrl, rus, eng) + OCRmyPDF | Apache / MPL |
| Arxivlar | 7-Zip (7zz), libarchive | LGPL; RAR yaratish mumkin emas, faqat ochish |
| E-kitoblar | Calibre `ebook-convert` | GPL: alohida jarayon sifatida |
| Fonni olib tashlash | rembg (U²-Net modeli) | MIT |
| DOCX muharriri | Brauzerda TipTap/ProseMirror + server tomonda DOCX ↔ HTML (mammoth, python-docx) | MIT |

---

## 13. Nofunksional talablar

**Tezlik**
- Bosh sahifa va vosita sahifalari: LCP < 2,0 s (4G mobil), Lighthouse Performance ≥ 90.
- 10 MB gacha surat konvertatsiyasi/siqish: ≤ 5 s; 20 sahifali DOCX → PDF: ≤ 15 s (navbatsiz holatda).
- Natija tayyor bo'lgach holat yangilanishi ≤ 1 s ichida ko'rinadi (SSE).

**Yuklama [Taxmin]**
- MVP: bir vaqtda 50 ta parallel vazifa, kuniga 10 000 vazifa.
- Worker'lar vazifa turi bo'yicha alohida navbatlarda (yengil: surat; og'ir: office, OCR, e-kitob), gorizontal kengaytiriladi.

**Xavfsizlik**
- JWT (access 15 daqiqa, refresh 7 kun, rotation va blacklist), refresh token httpOnly + Secure + SameSite cookie'da.
- Fayllar: MIME/magic-bytes tekshiruvi, ClamAV, hajm limiti yuklashdan oldin va keyin, arxiv bombalariga qarshi (ochilgan hajm va fayllar soni limiti, ichma-ich arxiv chuqurligi ≤ 3, path traversal'ga qarshi nomlarni tozalash).
- Konvertatsiya jarayonlari izolyatsiya qilingan konteynerlarda: non-root, tarmoqqa chiqishsiz, CPU/RAM/vaqt limiti bilan (LibreOffice makroslari o'chirilgan).
- SVG va HTML kiruvchi fayllarda tashqi resurs yuklash o'chirilgan (SSRF/XXE himoyasi).
- Natijani yuklab olish faqat qisqa muddatli imzolangan havola orqali; fayl nomlari UUID.
- Rate limiting: IP va foydalanuvchi bo'yicha (yuklash, login, parol tiklash).
- Bepul xizmatni suiiste'moldan himoya: IP va qurilma bo'yicha limitlar, shubhali faollikda bot tekshiruvi (masalan, Cloudflare Turnstile) **[Taxmin]**.
- Pro bosqichida: to'lov callback'lari imzo/autentifikatsiya va idempotentlik bilan tekshiriladi.
- OWASP Top 10 bo'yicha tekshiruv; IDOR testlari.

**Maxfiylik**
- Fayllar mazmuni loglanmaydi va tahlil uchun ishlatilmaydi.
- Avtomatik o'chirish (5-bo'limdagi muddatlar), tozalash ishi har 10 daqiqada ishlaydi.
- Shaxsiy ma'lumotlar O'zbekiston "Shaxsga doir ma'lumotlar to'g'risida"gi qonun talablariga muvofiq, jumladan O'zbekiston fuqarolarining shaxsiy ma'lumotlarini mahalliylashtirish talabi **[Taxmin: hosting joyi yurist bilan aniqlashtiriladi]**.

**Tillar va SEO**
- uz (lotin) / ru / en; standart til o'zbek. Kirill o'zbek interfeysi: 3-bosqich **[Taxmin]**.
- Har bir vosita sahifasi uchun server tomonda render qilingan (prerender) HTML, `hreflang`, sitemap.xml, structured data (`SoftwareApplication`, `FAQPage`).

**Ishonchlilik**
- Uptime ≥ 99,5%.
- PostgreSQL kunlik zaxira nusxasi, 14 kun saqlanadi; tiklash har oy sinab ko'riladi.
- Monitoring: xatolar (Sentry), metrikalar (navbat uzunligi, vazifa vaqti, xato foizi), alertlar Telegram'ga.

**Brauzerlar:** Chrome, Safari (iOS 15+), Firefox, Edge: oxirgi 2 versiya.

---

## 14. Texnologik stek

| Qatlam | Texnologiya |
|---|---|
| Frontend | React + TypeScript + Vite, Tailwind CSS, Zustand, TanStack Query, lucide-react, GSAP (minimal animatsiya), react-i18next. SEO uchun vosita sahifalari build vaqtida prerender qilinadi **[Taxmin: yoki Next.js'ga o'tish ko'rib chiqiladi]** |
| Brauzerdagi muharrirlar | TipTap (hujjat), pdf.js + pdf-lib (PDF sahifalari va annotatsiya), Cropper.js yoki shunga o'xshash (surat kesish) |
| Backend | Python, Django + Django REST Framework, djangorestframework-simplejwt |
| Fon vazifalari | Celery + Redis (navbatlar: `light`, `office`, `ocr`, `ebook`), Celery Beat (tozalash, eslatmalar) |
| Ma'lumotlar bazasi | PostgreSQL |
| Fayl xotira | S3-mos obyekt xotira (MinIO yoki bulut S3), lifecycle qoidasi bilan |
| Telegram bot | aiogram v3 (webhook rejimi), backend bilan ichki API orqali |
| DevOps | Docker (multi-stage, non-root), docker-compose, Nginx, GitHub Actions (test, lint, build, deploy) |
| Monitoring | Sentry, Prometheus + Grafana **[Taxmin]** |
| Test | pytest + pytest-django + factory_boy; Playwright (E2E) |

---

## 15. MVP doirasi va bosqichlar

Muddatlar 2 dasturchi (1 backend, 1 frontend) + 1 QA (yarim stavka) + dizayner (1-bosqich boshida) uchun **[Taxmin]**.

### 1-bosqich: MVP, to'liq bepul (9–11 hafta)
- Fayl yuklash, navbat, natija, avtomatik o'chirish (F-01, F-02, F-05–F-07, F-09, F-10)
- Suratlar: asosiy formatlar, HEIC, surat → PDF (F-11–F-13)
- Hujjatlar: Office → PDF, PDF → DOCX, PDF → surat (F-18–F-22)
- Arxivlar: chiqarish va ZIP yaratish (F-26, F-27); e-kitob konvertatsiyasi (F-29)
- Siqish: surat va PDF (F-31, F-33–F-35)
- PDF: birlashtirish, bo'lish, sahifalarni boshqarish (F-37–F-39)
- Surat tahriri: kesish, o'lcham, aylantirish (F-47–F-49)
- Matn tahriri: TXT/Markdown (F-53)
- Ixtiyoriy akkaunt va Google orqali kirish (F-57, F-59, F-60, F-64)
- Telegram bot: asosiy amallar (F-65, F-66, F-68, F-69)
- Admin panel: asosiy (F-70–F-74); SEO sahifalar 3 tilda (F-76–F-78)

### 2-bosqich (6–8 hafta)
- DOCX brauzer muharriri (F-54), OCR (F-25)
- PDF: suv belgisi, raqamlash, annotatsiya, imzo, parol (F-40–F-44)
- Surat: fonni olib tashlash, filtrlar (F-50, F-51); SVG, AVIF (F-14, F-16)
- PDF → Excel/PPT, TXT/HTML/MD konvertatsiyalari (F-23, F-24)
- Maqsadli hajm bo'yicha siqish (F-32), URL orqali yuklash (F-03)
- Botni akkauntga ulash, Telegram Login, natijani Telegramga yuborish (F-08, F-58, F-67)

### 3-bosqich (6–8 hafta)
- To'liq ofis muharriri (F-55, litsenziya qaroridan keyin), PDF matnini tahrirlash (F-56)
- Google Drive / Dropbox (F-04)
- PDF formalari (F-45), arxiv paroli (F-30), favicon (F-15), suratga matn (F-52)
- Blog (F-79), kirill o'zbek interfeysi, ochiq API (B2B) **[Taxmin]**

### Pro bosqichi: pullik tarif (3–4 hafta, boshlanish vaqti keyin belgilanadi)
Boshlash sharti **[Taxmin]**: MAU 20 000 ga yetganda yoki oylik server xarajatlari belgilangan byudjetdan oshganda. 2- yoki 3-bosqichdan keyin istalgan vaqtda boshlash mumkin.
- Tariflar va Click + Payme orqali to'lov (F-61, F-62), keyinroq Uzum (F-63)
- `/pricing` sahifasi va limit tugaganda Pro taklifi (F-80)
- Admin: tariflar, obunalar, to'lovlar (F-81)
- `PLAN`, `SUBSCRIPTION`, `PAYMENT` jadvallari, `LIMIT_POLICY`ga `pro` roli
- Foydalanish shartlari va ommaviy oferta yangilanadi
- Oldindan tayyorgarlik (bosqichdan 1–2 oy oldin): yuridik shaxs/YaTT va Click, Payme merchant shartnomalari

**Won't (bu loyihada emas):** video/audio konvertatsiya va siqish, RAW suratlar, ERI/E-IMZO, mobil ilova (web PWA yetarli deb hisoblanadi).

---

## 16. QA rejasi

**Test turlari**
- **Unit / integratsiya (pytest):** har bir konvertor uchun "oltin fayllar" to'plami (har formatdan 5–10 ta real namunaviy fayl: o'zbek lotin va kirill matnli, katta, buzilgan, parolli).
- **API testlar:** autentifikatsiya, limitlar, rate limiting, IDOR (boshqa foydalanuvchining vazifasi 404). Pro bosqichida to'lov callback'lari (to'g'ri/noto'g'ri imzo, takroriy so'rov) qo'shiladi.
- **E2E (Playwright):** asosiy oqimlar mobil (375 px) va desktop viewport'da, ochiq va qorong'i rejimda.
- **Xavfsizlik:** zararli fayllar (EICAR), arxiv bombasi, path traversal'li arxiv, XXE'li SVG/DOCX, makrosli Office fayllar, kengaytmasi almashtirilgan fayllar.
- **Yuklama:** 50 parallel vazifa, navbat to'lganida xatti-harakat.
- **Accessibility:** axe-core avtomatik tekshiruv + klaviatura bilan qo'lda test.
- **Lokalizatsiya:** uz/ru/en barcha sahifalarda tarjima yo'qligi yoki matn sig'masligi.

**Asosiy test ssenariylari**

| ID | Ssenariy | Kutilgan natija |
|---|---|---|
| T-01 | 5 ta JPG + 1 ta HEIC → bitta PDF, tartib o'zgartirilgan | 6 sahifali PDF, tanlangan tartibda |
| T-02 | Kirill va lotin o'zbek matnli DOCX → PDF | Barcha harflar to'g'ri, shrift almashuvi yo'q |
| T-03 | 60 MB fayl mehmon sifatida | Yuklashdan oldin limit xabari va ro'yxatdan o'tish taklifi |
| T-04 | Mehmon 21-vazifani bajaradi | Kunlik limit xabari va ro'yxatdan o'tish taklifi |
| T-05 | Surat "O'rtacha" siqish | Hajm kamayadi, EXIF GPS yo'q |
| T-06 | Buzilgan PDF yuklash | Tushunarli xato xabari, vazifa `failed`, server ishlashda davom etadi |
| T-07 | Arxiv bombasi (42.zip) | Rad etiladi, worker xotirasi limitdan oshmaydi |
| T-08 | Boshqa foydalanuvchining vazifa ID'si bilan yuklab olish | 404 |
| T-09 | Ro'yxatdan o'tgan foydalanuvchi 150 MB fayl yuklaydi | Qabul qilinadi va bepul ishlanadi |
| T-10 | Bitta IP'dan 1 daqiqada 100 ta yuklash so'rovi | 429 (rate limit), xizmat boshqa foydalanuvchilar uchun ishlashda davom etadi |
| T-11 | Muddati o'tgan vazifa havolasi | 404, faylning o'zi xotirada yo'q |
| T-12 | Botga 3 ta surat → "PDF qilish" | 3 sahifali PDF bot orqali qaytadi |
| T-13 | Botga 25 MB fayl | Web sahifaga havola beriladi |
| T-14 | RAR → ZIP | Ichidagi barcha fayllar va papka tuzilishi saqlanadi |
| T-15 | EPUB → PDF | Bob sarlavhalari va rasmlar saqlanadi |

**Definition of Done**
- Funksiyaning qabul mezonlari bajarilgan va QA tomonidan tasdiqlangan.
- Unit va integratsiya testlari yozilgan, CI'da yashil; backend qamrovi ≥ 80%.
- Tegishli E2E test bor (asosiy oqimlar uchun).
- Mobil va desktop, ochiq va qorong'i rejimda tekshirilgan; axe-core'da jiddiy xato yo'q.
- uz/ru/en tarjimalar to'liq.
- Security review o'tkazilgan (fayl yuklash va autentifikatsiya bilan bog'liq funksiyalar uchun, Pro bosqichida to'lovlar uchun ham majburiy).

---

## 17. Xavflar va taxminlar

| Xavf | Ehtimollik | Ta'sir | Choralar |
|---|---|---|---|
| Office/PDF konvertatsiya sifati (maket buzilishi) | Yuqori | Yuqori | Oltin fayllar bilan regressiya testlari, o'zbek shriftlarini serverga o'rnatish, foydalanuvchiga ogohlantirish |
| Daromadsiz davrda server xarajatlari (CPU-og'ir vazifalar, OCR) | Yuqori | Yuqori | Oylik byudjet chegarasi va alert, alohida navbatlar, limitlar, og'ir vositalarda (OCR) kattaroq limit faqat ro'yxatdan o'tganlarga, kerak bo'lsa Pro bosqichini oldinroq boshlash |
| Bepul xizmatni botlar va skriptlar orqali suiiste'mol qilish | O'rta | Yuqori | Rate limiting, shubhali faollikda bot tekshiruvi, admin tomonidan bloklash |
| Zararli fayllar orqali serverga hujum | O'rta | Juda yuqori | Izolyatsiya, ClamAV, resurs limitlari, tarmoqsiz worker'lar |
| AGPL/GPL litsenziyali vositalar | O'rta | Yuqori | Ishga tushirishdan oldin yuridik tekshiruv; alternativlar yoki tijoriy litsenziya |
| Mualliflik huquqi bilan himoyalangan kontentni konvertatsiya qilish (e-kitoblar, DRM) | O'rta | O'rta | DRM'li fayllar qo'llab-quvvatlanmaydi, foydalanish shartlarida mas'uliyat |
| Pro bosqichida Click/Payme merchant shartnomasi kechikishi | O'rta | O'rta | Shartnoma jarayonini Pro bosqichidan 1–2 oy oldin boshlash |
| Uzoq bepul davrdan keyin pullik tarifni foydalanuvchilar salbiy qabul qilishi | O'rta | O'rta | Bepul imkoniyatlar olib qo'yilmaydi, Pro faqat qo'shimcha beradi; o'zgarish oldindan e'lon qilinadi |
| Raqobat (yirik xalqaro xizmatlar) | Yuqori | O'rta | O'zbek tili, Telegram, to'liq bepul, SEO o'zbek so'rovlari bo'yicha |
| Maxfiylikka ishonchsizlik | O'rta | O'rta | Ochiq maxfiylik siyosati, "Hozir o'chirish", fayllar muddati ko'rinib turadi |

**Barcha [Taxmin]lar ro'yxati**
1. Ishchi nomi "jichcha".
2. Bo'lim 2'dagi barcha KPI raqamlari.
3. Bo'lim 5'dagi limitlar (hajm, vazifalar soni, saqlash muddati).
4. O'zbekistonda yirik mahalliy web raqobatchi yo'qligi (tekshirilmagan).
5. Standart til o'zbek (lotin); kirill interfeys 3-bosqichda.
6. Yuklama: 50 parallel vazifa, kuniga 10 000 vazifa.
7. Jamoa tarkibi va bosqich muddatlari.
8. Rang palitrasi (dizayn bosqichida yakunlanadi).
9. MVP'da reklama yo'q; keyinchalik qo'shilishi hal qilinmagan.
10. Hosting joyi va shaxsiy ma'lumotlarni mahalliylashtirish talabi.
11. SEO uchun prerender yoki Next.js tanlovi.
12. ERI/E-IMZO bu loyihada emas.
13. Monitoring stek (Prometheus + Grafana).
14. Pro bosqichini boshlash sharti (MAU 20 000 yoki xarajat chegarasi) va Pro bepul imkoniyatlarni olib qo'ymasligi.
15. Bot tekshiruvi uchun Cloudflare Turnstile yoki shunga o'xshash xizmat.

---

## 18. Ochiq savollar

1. Platformaning yakuniy nomi va domeni qanday bo'ladi?
2. Bepul davrda server xarajatlarini kim qoplaydi va oylik byudjet chegarasi qancha?
3. Suiiste'molga qarshi limitlar (5-bo'lim) to'g'rimi yoki saxiyroq/qattiqroq bo'lsinmi?
4. Pro tarifni qachon qo'shish rejalashtirilgan: aniq sana bo'yicha yoki KPI'ga (foydalanuvchilar soni, xarajat) qarab?
5. Server qayerda joylashadi: O'zbekistondagi hosting yoki xorijiy bulut?
6. DOCX tahriri uchun "oddiy muharrir" (2-bosqich) yetarlimi yoki boshidanoq Word'ga yaqin to'liq muharrir (pullik litsenziya bo'lishi mumkin) kerakmi?
7. Ishga tushirish muddati qachon va jamoa tarkibi qanday (kim dasturlaydi)?
8. Bepul davrda reklama umuman bo'lmaydimi yoki minimal reklama mumkinmi?
9. Kelajakda B2B (kompaniyalar uchun API yoki jamoaviy obuna) rejalashtirilganmi?
10. Video/audio konvertatsiya keyinroq kerak bo'ladimi (hozir "Won't" deb belgilangan)?
