# Learning English — ingliz tili o'quv platformasi (LMS)

Faqat ingliz tilini o'rgatish uchun. O'quvchi va o'qituvchi panellari hamda **Ustoz AI**.

```
learning-english/
├── main.py            ← hammasini ulaydi va ishga tushiradi (backend + frontend)
├── requirements.txt
├── .env               ← barcha sozlamalar va kalitlar shu yerda
├── backend/           (FastAPI: models/, routers/, services/, schemas/, uploads/)
└── frontend/          (React + Vite; dizayn o'zgartirilmagan)
```

## Nima yangilandi
- **Nom:** Learning English → *Learning English*, Ustoz AI → *Ustoz AI*. Kirish sahifasidan maktab / universitet / to'garak yo'nalishlari olib tashlandi (faqat o'quvchi/o'qituvchi tanlanadi).
- **Ustoz AI:** faqat ingliz tili bo'yicha. Model tanlovida faqat `.env` dagi `AI_MODEL` va `AI_MODELS` bilan belgilangan, tokeni sozlangan AI modellari ko'rsatiladi.
- **Davomat:** Keldi · Kech qoldi (−3) · Kelmadi (−5) · Sababli (0). **Uyga vazifa:** kechikib topshirsa −5, umuman topshirmasa −5. Hammasi Sozlamalarda o'zgaradi.
- **Testlar:** AI mavzu bo'yicha aynan kerakli savol va variantlar sonini yaratadi; o'qituvchi tahrirlaydi/almashtiradi va nashr qiladi.
- **Kitoblar:** Dars kitobi va Lug'at kitobi (PDF.js: qidiruv, sahifaga o'tish, zoom, full screen). Lug'at kitobidan Unit 1, Unit 2... va so'zlar avtomatik ajratiladi.
- **Lug'at imtihoni:** yodlash oynasi, "Topshirish" → to'liq ekran + kamera rasmi, qoidabuzarliklar (tab almashtirish, full screendan chiqish, copy/paste, o'ng tugma, PrintScreen), 2 ta ogohlantirishdan keyin avtomatik chiqarish. O'qituvchi "Topshirilgan lug'atlar" sahifasida topilgan/topilmagan so'zlar, ogohlantirishlar va rasmni ko'radi. Qayta topshirish so'rovlari ham shu yerda.
- **Darsdan tashqari topshiriqlar:** matn/rasm/fayl va maksimal ball; ball reytingga qo'shiladi.
- **Tekshirish:** AI-detektor, o'xshashlik (chegarasi Sozlamalarda) va o'quvchining Ustoz AI ga bergan savollari tarixi.

## Ishga tushirish

Kerak: **Python 3.11+** va **Node.js 18+**.

```bash
pip install -r requirements.txt
# .env ni to'ldiring
python main.py
```

Bu bitta buyruq:
1. jadvallarni yaratadi,
2. frontend paketlarini o'rnatadi (birinchi marta) va saytni ishga tushiradi,
3. backend serverni ishga tushiradi.

- Sayt: http://localhost:5173
- API hujjati: http://localhost:8000/docs

Foydali variantlar:
```bash
python main.py --demo          # demo o'qituvchi, 5 o'quvchi, 1 guruh bilan (parol: demo12345)
python main.py --no-frontend   # faqat backend
uvicorn main:app --reload      # backendni qo'lda
```
Demo login: `teacher@demo.uz`, `student1@demo.uz` … `student5@demo.uz`.

Production: `cd frontend && npm run build` — keyin `frontend/dist` ni backendning o'zi beradi (`uvicorn main:app`).

## Vercel + Railway

Frontend Vercel'da va backend Railway'da alohida ishlaganda, production frontend API so'rovlarini standart holatda
`https://aedu-production-bfdd9ae0.up.railway.app/api` ga yuboradi. Backend CORS uchun standart frontend manzili
`https://aedu-eight.vercel.app`. Boshqa domen yoki backend ishlatilsa:

- Railway Variables: `FRONTEND_URL=https://sizning-frontend-domeningiz`
- Vercel Environment Variables: `VITE_API_URL=https://sizning-backend-domeningiz/api`

`VITE_API_URL` o'zgartirilgandan keyin Vercel'da yangi deployment/build kerak.

## Kod avtomatik kiritilishi
- **DEV rejimi** (Resend / SMS kaliti yo'q): kod server konsoliga chiqadi va tasdiqlash sahifasida **avtomatik terib beriladi**.
- **SMS (production):** xabar oxirida `@domen #kod` qatori bor, Android Chrome kodni o'zi o'qiydi (WebOTP); iOS klaviaturada taklif qiladi. Maydon `autocomplete="one-time-code"`.
- **Email:** `RESEND_API_KEY` va `RESEND_FROM_EMAIL` ni kiriting. Kod brauzer/pochta ilovasidan kiritiladi (paste ham ishlaydi, 6 katakka bo'linadi).

## Yangi imkoniyatlar (3-yangilanish)
- **O'quvchi ro'yxatdan o'tishi:** guruhni tanlaydi → ismini qidiradi (faqat o'qituvchi kiritgan ismlar) → telefon/email + parol → ro'yxatdan o'tadi (`REQUIRE_OTP=true` bo'lsa kod ham so'raladi).
- **Vazifa topshirish:** uy vazifalari qoladi; alohida vaqtli Tasks bo'limi olib tashlangan.
- **Ustoz AI:** test yaratishda sozlangan AI modelini tanlash mumkin.

## Oldingi imkoniyatlar
- **O'quvchi ro'yxatdan o'tishi:** o'qituvchi "O'quvchilar jadvali" → "Ismlarni kiritish" orqali faqat ismlarni yozadi. O'quvchi ro'yxatdan o'tgach guruhini tanlaydi va FAQAT shu ismlar ichidan o'zini topib "Bu menman" deydi; baho va davomat unga avtomatik bog'lanadi. (Keyinroq ham `/join` sahifasidan qo'shilish mumkin.)
- **Jadvaldagi baho chegarasi:** bir katakka eng ko'pi 50 ball (o'qituvchi → Sozlamalar → "Jadvaldagi eng yuqori ball" orqali o'zgaradi).
- **Yordam:** faqat o'qituvchi menyusida, saytdan foydalanish qo'llanmasi.
- **Vazifa topshirish:** o'quvchi bir nechta fayl yuklay oladi va o'qituvchi tekshirmaguncha (muddat ichida) ishini o'zgartirishi yoki fayl qo'shishi mumkin.
- **Eski baza:** yangi ustunlar ishga tushganda avtomatik qo'shiladi, `aedu.db` ni o'chirish shart emas.

## Ma'lumotlar bazasi
- `users` umumiy akkaunt, login va aloqa ma'lumotlarini saqlaydi; `students` va `teachers` jadvallari tegishli rolga xos profil ma'lumotlarini alohida saqlaydi.
- `groups`, `assignments`, `submissions`, `attendance`, `tests` va boshqa jadvallar o'quv platformasining tegishli ma'lumotlarini saqlaydi; ular o'chirilmaydi.
- Eski bazadagi o'quvchi/o'qituvchi ma'lumotlari ishga tushishda yangi profil jadvallariga ko'chiriladi. Eski ustunlar saqlanib qoladi, mavjud yozuvlar o'chirilmaydi.

## .env
| Kalit | Izoh |
|---|---|
| `SECRET_KEY` | JWT uchun (yaratilgan) |
| `FRONTEND_URL` | Frontend domeni (standart: `https://aedu-eight.vercel.app`; CORS uchun) |
| `DB_TYPE`, `DB_NAME`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` | Ma'lumotlar bazasi: `sqlite` (standart) / `postgresql` / `mysql`. Yoki to'liq `DATABASE_URL` (u ustun turadi). PostgreSQL: `python -m pip install psycopg2-binary`, MySQL: `python -m pip install pymysql` |
| `RESEND_API_KEY`, `RESEND_FROM_EMAIL` | Email OTP |
| `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`, `AI_PROVIDER`, `AI_MODEL`, `OPENAI_BASE_URL` | Ustoz AI va PDF dan testni AI orqali ajratish. `AI_PROVIDER=gemini`, `anthropic`, `openai` yoki `auto`; Gemini kaliti `GEMINI_API_KEY` da saqlanadi |
| `VERCEL_AI_GATEWAY_API_KEY` | Vercel AI Gateway kaliti; Gateway modelini `AI_MODEL` yoki `AI_MODELS` da ko'rsatish kerak |
| `REQUIRE_OTP`, `AI_DAILY_LIMIT`, `RESUBMIT_PENALTY`, `APP_TZ_OFFSET` | Kod so'rash, AI kunlik limiti, qayta yuborish jarimasi, vaqt mintaqasi (Toshkent = 5) |
| `AI_MODELS` | Saytda ko'rsatiladigan qo'shimcha modellar, vergul bilan: `gpt-4o-mini,gemini:gemini-2.5-flash,vercel:openai/gpt-4o`; tokeni sozlanmagan provider o'tkazib yuboriladi |
| `SMS_PROVIDER` (`eskiz`/`generic`), `SMS_API_KEY`, `SMS_API_URL` | Telefon OTP |

## Asosiy qoidalar
- **Reyting** = test ballari (faqat birinchi urinish, foiz/10) + vazifa ballari − davomat jarimalari (`backend/services/scoring.py`).
- **Kelmadi** → −20 ball (o'qituvchi sozlamasida o'zgaradi); status o'zgarsa jarima qayta hisoblanadi, ikki marta ayrilmaydi.
- **Qayta topshirish:** tugallanmagan test uchun so'rov → o'qituvchi ruxsat bersa keyingi urinish "birinchi" hisoblanadi.
- Foydalanuvchi rollari: o'quvchi va o'qituvchi. Barcha API xatolari `X-Lang` bo'yicha uz/en/ru da.

## Logotip animatsiyasi
`frontend/src/components/ElectricLogo.jsx` (WebGL2, `ogl`) o'zgartirilmagan holda ishlatiladi. Logotip shakli `frontend/public/logo.svg` (Learning English) dan olinadi — shu faylni almashtirsangiz animatsiya yangi shaklga o'tadi.

shu yerni qil: ⤵

Qara, lug'at yodlashda rasmga qara: 1-Unitni yodlashda faqat 1-Unitning lug'atlari chiqsin. Topshirishda esa qayta topshirib ham bo'lmayapti. Va yana yodlashda jadvalga o'xshab chiqsin, faqat tepasida chiqmasin. Test ham shunday. Testda kamerani olib tashla. Topshirish bosilsa faqat shu Unitning savollari — masalan, "clever", pastda variantlar bo'lsin: "aqlli", "aqlsiz"... shular. Va 17 ta 1-Unit lug'ati va amaliy ham bo'lsin 3 ta, hammasida shunaqa. Kitob yuklasam lug'atga avto kitobdagi barcha lug'atlar tushsin. Va uni o'qituvchi ochsa topshirib bo'lsin, boshidagi 10 tasi o'zi ochiq bo'lsin. Va dizayni ham o'lib yotibdi, lug'atni topshirishga kirganda full ekran bo'lsin. Faqat shu yerini to'g'irla. Va ro'yxatdan o'tishni shunday qil va barcha ma'lumotlarni to'la — guruh va ismlarni, kitoblarni va boshqalarni (tozala).
Ketma-ketlik aynan shunday bo'lsin:

1. 1-qadam: Guruhni tanlash. Sahifa ochilishi bilan eng birinchi o'qituvchi yaratgan guruhlar ro'yxati chiqadi (karta ko'rinishida).
2. 2-qadam: Ism kiritish. Guruh tanlangach, ism-familiya kiritiladigan maydon chiqadi.
3. 3-qadam: Ro'yxatdan o'tish. Email yoki telefon raqam + parol (parolni takrorlash bilan).
4. Ro'yxatdan o'tgach o'quvchi avtomatik o'qituvchining "O'quvchilar jadvali"ga, tanlagan guruhi ichiga tushadi.

Qoida: agar o'qituvchi hali birorta ham guruh qo'shmagan bo'lsa, o'quvchi ro'yxatdan o'ta olmaydi — "Hozircha guruhlar mavjud emas. O'qituvchi guruh qo'shishi kerak" degan xabar chiqadi.
4. Kirish (login)

* O'qituvchi: telefon raqam yoki email + parol (birinchi o'qituvchi hisobi .env dagi TEACHER_PHONE / TEACHER_PASSWORD dan avtomatik yaratiladi).
* O'quvchi: ro'yxatdan o'tgan email/telefon + parol.
* Rolga qarab avtomatik tegishli panelga yo'naltiriladi.

Ro'yxatdan o'tishni shunday qil, sayt dizayniga tegmasdan.

faqat men aytgan ozgarishlarni qil bitta yam fileni olib tashlama va ozgartirma faqat qodlar ozgarsin
