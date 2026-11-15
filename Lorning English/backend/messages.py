"""Foydalanuvchiga ko'rinadigan barcha xatolar 3 tilda (uz/en/ru)."""
from fastapi import Request

MSG = {
    # --- Kitoblar, lug'at imtihoni ---
    "vocab_no_words": {"uz": "PDF dan so'zlar topilmadi. Har qatorda \"so'z - tarjima\" ko'rinishida yozilgan bo'lishi kerak", "en": "No words found in the PDF. Each line should look like \"word - translation\"", "ru": "В PDF не найдены слова. Каждая строка должна быть вида «слово - перевод»"},
    "vocab_parse_failed": {"uz": "Kitobdagi lug'atlarni aniq ajratib bo'lmadi. PDF dagi Unit va so'zlarni tekshiring yoki AI modelini sozlang", "en": "Could not reliably extract vocabulary units. Check the PDF's unit/word formatting or configure an AI model", "ru": "Не удалось надёжно извлечь словарь. Проверьте формат юнитов/слов в PDF или настройте модель ИИ"},
    "vocab_attempt_done": {"uz": "Bu unit allaqachon topshirilgan. Qayta topshirish uchun o'qituvchidan ruxsat so'rang", "en": "This unit was already submitted. Ask your teacher for a retake", "ru": "Этот юнит уже сдан. Попросите у учителя разрешение на пересдачу"},
    "vocab_need_ai": {"uz": "Kitobda faqat inglizcha so'zlar bor, tarjima uchun AI sozlanishi kerak (.env dagi API kalit)", "en": "The book has English words only; configure an AI model (API key in .env) to translate them", "ru": "В книге только английские слова; для перевода нужно настроить ИИ (API-ключ в .env)"},
    "vocab_translate_failed": {"uz": "So'zlarni tarjima qilib bo'lmadi. Birozdan keyin qayta urinib ko'ring", "en": "Could not translate the words. Please try again in a moment", "ru": "Не удалось перевести слова. Повторите попытку чуть позже"},
    "vocab_attempts_over": {"uz": "3 ta imkoniyat ham tugadi. Qayta topshirish uchun o'qituvchidan ruxsat so'rang", "en": "All 3 attempts are used. Ask your teacher for a retake", "ru": "Все 3 попытки использованы. Попросите у учителя пересдачу"},
    "final_locked": {"uz": "Yakuniy test barcha unitlar topshirilgach ochiladi", "en": "The final test opens after all units are passed", "ru": "Итоговый тест откроется после сдачи всех юнитов"},
    "final_done": {"uz": "Yakuniy testdan allaqachon o'tgansiz", "en": "You already passed the final test", "ru": "Вы уже сдали итоговый тест"},
    "final_attempts_over": {"uz": "Yakuniy test uchun 3 ta imkoniyat ham tugadi", "en": "All 3 attempts for the final test are used", "ru": "Все 3 попытки итогового теста использованы"},
    "vocab_photo_required": {"uz": "Imtihon boshlanishi uchun kamera rasmi kerak", "en": "A camera photo is required to start the exam", "ru": "Для начала экзамена нужно фото с камеры"},
    "vocab_finished": {"uz": "Imtihon allaqachon tugagan", "en": "The exam is already finished", "ru": "Экзамен уже завершён"},
    "vocab_unit_locked": {"uz": "Bu Unit hali ochilmagan. O'qituvchingizdan ochib berishini so'rang", "en": "This unit is locked. Ask your teacher to open it", "ru": "Этот юнит закрыт. Попросите учителя открыть его"},
    "vocab_retake_not_needed": {"uz": "Avval shu unitni topshirgan bo'lishingiz kerak", "en": "Submit this unit first", "ru": "Сначала сдайте этот юнит"},
    "book_not_available": {"uz": "Bu kitob siz uchun mavjud emas", "en": "This book is not available to you", "ru": "Эта книга вам недоступна"},
    "invalid_credentials": {"uz": "Login yoki parol noto'g'ri", "en": "Invalid login or password", "ru": "Неверный логин или пароль"},
    "account_blocked": {"uz": "Hisobingiz bloklangan", "en": "Your account is blocked", "ru": "Ваш аккаунт заблокирован"},
    "not_authenticated": {"uz": "Avval tizimga kiring", "en": "Please sign in first", "ru": "Сначала войдите в систему"},
    "forbidden": {"uz": "Bu amal uchun ruxsat yo'q", "en": "You don't have permission", "ru": "Нет доступа к этому действию"},
    "not_found": {"uz": "Topilmadi", "en": "Not found", "ru": "Не найдено"},
    "group_not_found": {"uz": "Guruh topilmadi", "en": "Group not found", "ru": "Группа не найдена"},
    "invalid_phone": {"uz": "Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak", "en": "Phone must be in +998XXXXXXXXX format", "ru": "Телефон должен быть в формате +998XXXXXXXXX"},
    "invalid_email": {"uz": "Email noto'g'ri", "en": "Invalid email", "ru": "Неверный email"},
    "identifier_required": {"uz": "Email yoki telefon kiriting", "en": "Enter email or phone", "ru": "Введите email или телефон"},
    "user_exists": {"uz": "Bu email/telefon allaqachon ro'yxatdan o'tgan", "en": "This email/phone is already registered", "ru": "Этот email/телефон уже зарегистрирован"},
    "otp_wait": {"uz": "Kodni qayta yuborish uchun {seconds} soniya kuting", "en": "Wait {seconds} seconds before resending", "ru": "Подождите {seconds} сек. перед повторной отправкой"},
    "otp_rate_limit": {"uz": "Juda ko'p urinish. Keyinroq qayta urinib ko'ring", "en": "Too many attempts. Try again later", "ru": "Слишком много попыток. Повторите позже"},
    "otp_expired": {"uz": "Kod muddati tugagan. Yangi kod so'rang", "en": "Code expired. Request a new one", "ru": "Срок действия кода истёк. Запросите новый"},
    "otp_invalid": {"uz": "Kod noto'g'ri. Qolgan urinishlar: {left}", "en": "Wrong code. Attempts left: {left}", "ru": "Неверный код. Осталось попыток: {left}"},
    "otp_locked": {"uz": "Urinishlar tugadi. Yangi kod so'rang", "en": "Too many wrong attempts. Request a new code", "ru": "Попытки исчерпаны. Запросите новый код"},
    "otp_not_found": {"uz": "Avval kod so'rang", "en": "Request a code first", "ru": "Сначала запросите код"},
    "otp_send_failed": {"uz": "Kodni yuborib bo'lmadi. Keyinroq urinib ko'ring", "en": "Could not send the code. Try again later", "ru": "Не удалось отправить код. Повторите позже"},
    "reg_token_invalid": {"uz": "Ro'yxatdan o'tish sessiyasi yaroqsiz. Qaytadan boshlang", "en": "Registration session is invalid. Start again", "ru": "Сессия регистрации недействительна. Начните заново"},
    "wrong_old_password": {"uz": "Eski parol noto'g'ri", "en": "Old password is wrong", "ru": "Старый пароль неверен"},
    "already_onboarded": {"uz": "Yo'nalish va rol allaqachon tanlangan", "en": "Track and role already chosen", "ru": "Направление и роль уже выбраны"},
    "invalid_role_for_track": {"uz": "Bu yo'nalish uchun bunday rol yo'q", "en": "This role is not available for the track", "ru": "Такой роли нет для этого направления"},
    "file_type_not_allowed": {"uz": "Fayl turi ruxsat etilmagan", "en": "File type is not allowed", "ru": "Тип файла не разрешён"},
    "file_too_large": {"uz": "Fayl hajmi juda katta (maks. {mb} MB)", "en": "File is too large (max {mb} MB)", "ru": "Файл слишком большой (макс. {mb} МБ)"},
    "file_required": {"uz": "Fayl yuklash shart", "en": "A file is required", "ru": "Необходимо загрузить файл"},
    "bad_pdf": {"uz": "PDF faylni o'qib bo'lmadi", "en": "Could not read the PDF", "ru": "Не удалось прочитать PDF"},
    "pdf_no_text": {"uz": "PDF ichida matn topilmadi (skan qilingan bo'lishi mumkin)", "en": "No text found in the PDF (it may be scanned)", "ru": "В PDF не найден текст (возможно, это скан)"},
    "no_questions": {"uz": "PDF dan savollar ajratib bo'lmadi", "en": "Could not extract questions from the PDF", "ru": "Не удалось извлечь вопросы из PDF"},
    "deadline_passed": {"uz": "Topshirish muddati tugagan", "en": "The deadline has passed", "ru": "Срок сдачи истёк"},
    "task_not_started": {"uz": "Avval topshiriqni boshlang", "en": "Start the task first", "ru": "Сначала начните задание"},
    "task_time_over": {"uz": "Vaqt tugadi, topshirib bo'lmaydi", "en": "Time is up, submission is closed", "ru": "Время вышло, сдача закрыта"},
    "already_submitted": {"uz": "Allaqachon topshirilgan", "en": "Already submitted", "ru": "Уже сдано"},
    "submission_empty": {"uz": "Matn yoki fayl kiriting", "en": "Provide text or a file", "ru": "Введите текст или загрузите файл"},
    "invalid_score": {"uz": "Ball noto'g'ri (0 dan {max} gacha)", "en": "Invalid score (0 to {max})", "ru": "Неверный балл (от 0 до {max})"},
    "analysis_confirmation_required": {"uz": "Bahoni saqlashdan oldin AI va o'xshashlik tahlilini shaxsan ko'rib chiqing", "en": "Review the AI and similarity analysis yourself before saving this grade", "ru": "Лично проверьте анализ ИИ и сходства перед сохранением оценки"},
    "ai_no_text": {"uz": "AI tekshiruvi uchun topshiriqda matn yo'q", "en": "This submission has no text to check", "ru": "В работе нет текста для проверки ИИ"},
    "invalid_date": {"uz": "Sana noto'g'ri", "en": "Invalid date", "ru": "Неверная дата"},
    "invalid_value": {"uz": "Qiymat noto'g'ri", "en": "Invalid value", "ru": "Неверное значение"},
    "test_not_available": {"uz": "Test mavjud emas yoki e'lon qilinmagan", "en": "Test is unavailable or not published", "ru": "Тест недоступен или не опубликован"},
    "test_time_over": {"uz": "Test vaqti tugagan", "en": "Test time is over", "ru": "Время теста истекло"},
    "retake_required": {"uz": "Testni qayta ishlash uchun o'qituvchidan ruxsat so'rang", "en": "Ask your teacher for permission to retake", "ru": "Запросите у учителя разрешение на пересдачу"},
    "retake_not_needed": {"uz": "Bu test uchun qayta topshirish so'rovi kerak emas", "en": "No retake request is needed for this test", "ru": "Для этого теста запрос на пересдачу не нужен"},
    "retake_pending": {"uz": "So'rov allaqachon yuborilgan", "en": "A request is already pending", "ru": "Запрос уже отправлен"},
    "request_resolved": {"uz": "Bu so'rov allaqachon ko'rib chiqilgan", "en": "This request is already resolved", "ru": "Этот запрос уже рассмотрен"},
    "attempt_not_found": {"uz": "Urinish topilmadi", "en": "Attempt not found", "ru": "Попытка не найдена"},
    "ai_not_configured": {"uz": "AI hozircha ulanmagan", "en": "AI is not connected yet", "ru": "ИИ пока не подключён"},
    "ai_error": {"uz": "AI javob bera olmadi. Keyinroq urinib ko'ring", "en": "AI could not respond. Try again later", "ru": "ИИ не смог ответить. Повторите позже"},
    "document_read_failed": {"uz": "Hujjatni o'qib bo'lmadi. Fayl buzilmaganini tekshiring", "en": "Could not read the document. Check that the file is valid", "ru": "Не удалось прочитать документ. Проверьте файл"},
    "document_no_text": {"uz": "Hujjatdan matn olinmadi. Skan qilingan sahifani rasm sifatida yuboring", "en": "No text could be extracted. Send a scanned page as an image", "ru": "Не удалось извлечь текст. Отправьте отсканированную страницу как изображение"},
    "not_a_student": {"uz": "Bu foydalanuvchi o'quvchi emas", "en": "This user is not a student", "ru": "Этот пользователь не ученик"},
    "not_in_group": {"uz": "O'quvchi bu guruhda emas", "en": "Student is not in this group", "ru": "Ученик не состоит в этой группе"},
    "already_member": {"uz": "O'quvchi allaqachon guruhda", "en": "Student is already in the group", "ru": "Ученик уже в группе"},
    "no_parent_contact": {"uz": "Ota-ona kontakti kiritilmagan", "en": "No parent contact saved", "ru": "Контакт родителя не указан"},
    "message_not_allowed": {"uz": "Bu foydalanuvchiga xabar yuborib bo'lmaydi", "en": "You can't message this user", "ru": "Нельзя написать этому пользователю"},
    "cannot_block_self": {"uz": "O'zingizni bloklab bo'lmaydi", "en": "You can't block yourself", "ru": "Нельзя заблокировать себя"},
    "ai_bad_key": {"uz": "AI kaliti noto'g'ri yoki ruxsat yo'q. .env dagi kalitni tekshiring", "en": "The AI API key is invalid or has no access. Check the key in .env", "ru": "Ключ ИИ неверный или нет доступа. Проверьте ключ в .env"},
    "ai_bad_model": {"uz": "AI modeli topilmadi. .env dagi AI_MODEL ni tekshiring", "en": "AI model not found. Check AI_MODEL in .env", "ru": "Модель ИИ не найдена. Проверьте AI_MODEL в .env"},
    "ai_quota": {"uz": "AI limiti yoki balansi tugagan (yoki juda ko'p so'rov). Hisobingizni tekshiring", "en": "AI quota/balance exhausted or too many requests. Check your account", "ru": "Лимит или баланс ИИ исчерпан (или слишком много запросов). Проверьте аккаунт"},
    "grade_too_high": {"uz": "Baho 0 dan {max} gacha bo'lishi kerak ({max} dan yuqori qo'yib bo'lmaydi)", "en": "The grade must be between 0 and {max} (more than {max} is not allowed)", "ru": "Оценка должна быть от 0 до {max} (больше {max} ставить нельзя)"},
    "already_reviewed": {"uz": "O'qituvchi tekshirib bo'lgan ishni o'zgartirib bo'lmaydi", "en": "A submission that has been reviewed can't be changed", "ru": "Проверенную работу изменить нельзя"},
    "too_many_files": {"uz": "Eng ko'pi bilan {n} ta fayl yuklash mumkin", "en": "You can upload at most {n} files", "ru": "Можно загрузить не более {n} файлов"},
    "roster_not_found": {"uz": "Bu ism ro'yxatda topilmadi yoki allaqachon band", "en": "This name was not found or is already taken", "ru": "Это имя не найдено или уже занято"},
    "name_invalid": {"uz": "Ism kamida 2 ta belgidan iborat bo'lsin", "en": "The name must be at least 2 characters", "ru": "Имя должно содержать минимум 2 символа"},
    "subscription_required": {"uz": "Obunangiz tugagan. Davom etish uchun obuna sotib oling", "en": "Your subscription has expired. Buy a subscription to continue", "ru": "Подписка закончилась. Оформите подписку, чтобы продолжить"},
    "ai_limit": {"uz": "Bugungi {n} ta savol tugadi — ertaga yana yozing", "en": "Today's {n} questions are used up — write again tomorrow", "ru": "Сегодняшние {n} вопросов закончились — напишите завтра"},
    "pending_exists": {"uz": "Oldingi to'lovingiz hali tekshirilmoqda. Admin javobini kuting", "en": "Your previous payment is still being reviewed", "ru": "Предыдущий платёж ещё проверяется"},
    "invalid_plan": {"uz": "Bunday tarif yo'q", "en": "No such plan", "ru": "Такого тарифа нет"},
    "payment_resolved": {"uz": "Bu to'lov allaqachon ko'rib chiqilgan", "en": "This payment was already reviewed", "ru": "Этот платёж уже рассмотрен"},
    "telegram_not_configured": {"uz": "Telegram bot sozlanmagan (.env da TELEGRAM_BOT_TOKEN yo'q)", "en": "The Telegram bot is not configured (TELEGRAM_BOT_TOKEN is missing in .env)", "ru": "Telegram-бот не настроен (в .env нет TELEGRAM_BOT_TOKEN)"},
    "telegram_send_failed": {"uz": "Telegramga yuborib bo'lmadi. Ota-ona botni bloklagan bo'lishi mumkin", "en": "Could not send to Telegram. The parent may have blocked the bot", "ru": "Не удалось отправить в Telegram. Возможно, родитель заблокировал бота"},
    "parent_link_not_found": {"uz": "Bu ota-ona topilmadi yoki allaqachon uzilgan", "en": "This parent was not found or is already unlinked", "ru": "Этот родитель не найден или уже отвязан"},
    "ai_no_content": {"uz": "AI tekshiruvi uchun matn yoki kod topilmadi (rasm/zip fayllar tahlil qilinmaydi)", "en": "No text or code to check (images and zip files are not analysed)", "ru": "Нет текста или кода для проверки (изображения и zip не анализируются)"},
    "validation_error": {"uz": "Kiritilgan ma'lumotlar noto'g'ri", "en": "Invalid input data", "ru": "Неверные входные данные"},
    "server_error": {"uz": "Server xatosi", "en": "Server error", "ru": "Ошибка сервера"},
}


class AppError(Exception):
    def __init__(self, status: int, key: str, **fmt):
        self.status = status
        self.key = key
        self.fmt = fmt


def norm_lang(value) -> str:
    v = (value or "uz").lower()[:2]
    return v if v in ("uz", "en", "ru") else "uz"


def lang_from_request(request: Request) -> str:
    return norm_lang(request.headers.get("x-lang") or request.headers.get("accept-language"))


def t(key: str, lang: str = "uz", **fmt) -> str:
    entry = MSG.get(key)
    if not entry:
        return key
    text = entry.get(norm_lang(lang), entry["uz"])
    try:
        return text.format(**fmt)
    except (KeyError, IndexError):
        return text
