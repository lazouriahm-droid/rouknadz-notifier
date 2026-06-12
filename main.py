from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx, os, logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()

ULTRAMSG_INSTANCE = os.getenv("ULTRAMSG_INSTANCE", "instance180585")
ULTRAMSG_TOKEN    = os.getenv("ULTRAMSG_TOKEN", "0aszesi0oq4dexbd")
ULTRAMSG_URL      = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"

MESSAGES = {
    "commande_recue":              "📦 مرحباً {name}!\n\nتم استلام طلبك *{tracking}* ✅\nالمنتج: {product}\nالمبلغ: *{amount} دج*\n\nسنجهز طلبك قريباً 🚀\n_Rouknadz_",
    "dispatch":                    "🚚 {name}، طلبك خرج من المستودع!\n\nرقم التتبع: *{tracking}* ✅\n_Rouknadz_",
    "vers_wilaya":                 "📍 {name}، طلبك وصل ولايتك!\n\nرقم التتبع: *{tracking}*\nسيتم التسليم خلال 1-2 يوم ⏰\n_Rouknadz_",
    "confirme_au_bureau":          "🏪 {name}، طلبك جاهز للاستلام من المكتب!\n\nرقم التتبع: *{tracking}*\n_Rouknadz_",
    "sortie_en_livraison":         "🛵 {name}، المندوب في الطريق إليك الآن!\n\nرقم التتبع: *{tracking}*\n⚠️ يرجى التواجد والرد على المكالمات\n_Rouknadz_",
    "livre":                       "✅ {name}، تم تسليم طلبك!\n\nشكراً لثقتك بـ *Rouknadz* 🙏\nنرحب بتقييمك ⭐",
    "recouvert":                   "✅ {name}، تم تسليم طلبك!\n\nشكراً لثقتك بـ *Rouknadz* 🙏\nنرحب بتقييمك ⭐",
    "encaisse":                    "✅ {name}، تم تسليم طلبك!\n\nشكراً لثقتك بـ *Rouknadz* 🙏",
    "retour":                      "↩️ {name}، تم إرجاع طلبك\n\nرقم التتبع: *{tracking}*\nتواصل معنا لأي استفسار 💬\n_Rouknadz_",
    "ne_repond_pas_1":             "📞 {name}، حاولنا الاتصال بك!\n\nطلبك *{tracking}* جاهز للتسليم\nيرجى الرد على المكالمات القادمة 📱\n_Rouknadz_",
    "ne_repond_pas_2":             "📞 {name}، محاولة اتصال ثانية!\n\nطلبك *{tracking}* لا يزال ينتظرك\nيرجى الرد على المكالمات ⚠️\n_Rouknadz_",
    "ne_repond_pas_3":             "⚠️ {name}، آخر محاولة اتصال!\n\nطلبك *{tracking}* سيُرجع إذا لم نتواصل\nاتصل بنا الآن: تواصل معنا 🆘\n_Rouknadz_",
    "injoignable":                 "📵 {name}، لم نتمكن من الوصول إليك\n\nطلبك *{tracking}* في انتظارك\nيرجى التواصل معنا على هذا الرقم 📱\n_Rouknadz_",
    "reportee_a_une_date_ulterieure": "📅 {name}، تم تأجيل توصيل طلبك\n\nرقم التتبع: *{tracking}*\nسنتواصل معك لتحديد موعد مناسب 🗓️\n_Rouknadz_",
    "en_attente_du_client":        "⏳ {name}، طلبك في انتظارك!\n\nرقم التتبع: *{tracking}*\nيرجى التواصل معنا لتأكيد موعد التسليم 📞\n_Rouknadz_",
    "commune_erronee":             "📍 {name}، يوجد خطأ في عنوان التوصيل!\n\nرقم التتبع: *{tracking}*\nيرجى تأكيد عنوانك الصحيح بالرد على هذه الرسالة 🗺️\n_Rouknadz_",
    "commande_annulee":            "❌ {name}، تم إلغاء طلبك\n\nرقم التتبع: *{tracking}*\nللاستفسار تواصل معنا 💬\n_Rouknadz_",
}

async def send_whatsapp(phone: str, message: str):
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("0"):
        phone = "213" + phone[1:]
    elif not phone.startswith("213"):
        phone = "213" + phone
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(ULTRAMSG_URL, data={
            "token": ULTRAMSG_TOKEN,
            "to": phone,
            "body": message
        })
        logger.info(f"Sent to {phone}: {r.json()}")
        return r.json()

@app.post("/webhook/zrexpress")
async def webhook(request: Request):
    try:
        body = await request.json()
    except:
        raise HTTPException(400, "Invalid JSON")
    p        = body.get("parcel") or body.get("data") or body
    state    = (p.get("stateName") or p.get("state") or p.get("status") or "").lower().replace(" ", "_")
    tracking = p.get("trackingNumber") or p.get("barcode") or p.get("id") or "—"
    name     = p.get("recipientName") or p.get("clientName") or p.get("nom") or "العميل"
    phone    = p.get("recipientPhone") or p.get("phone") or p.get("telephone") or ""
    product  = p.get("productName") or p.get("description") or "المنتج"
    amount   = p.get("totalAmount") or p.get("price") or ""
    logger.info(f"Webhook: tracking={tracking} state={state} phone={phone}")
    if not phone:
        return JSONResponse({"status": "skipped", "reason": "no phone"})
    template = MESSAGES.get(state, "📦 {name}، تم تحديث طلبك *{tracking}*\nالحالة: {state}\n_Rouknadz_")
    message  = template.format(name=name, tracking=tracking, product=product, amount=amount, state=state)
    result   = await send_whatsapp(phone, message)
    return JSONResponse({"status": "sent", "tracking": tracking, "state": state, "result": result})

@app.post("/test/send")
async def test_send(request: Request):
    body     = await request.json()
    phone    = body.get("phone", "")
    state    = body.get("state", "sortie_en_livraison")
    name     = body.get("name", "العميل")
    tracking = body.get("tracking", "ZR-TEST-001")
    product  = body.get("product", "Strobe LED")
    amount   = body.get("amount", "3450")
    if not phone:
        raise HTTPException(400, "phone required")
    template = MESSAGES.get(state, MESSAGES["sortie_en_livraison"])
    message  = template.format(name=name, tracking=tracking, product=product, amount=amount, state=state)
    result   = await send_whatsapp(phone, message)
    return JSONResponse({"status": "sent", "message": message, "result": result})

@app.get("/")
async def home():
    return {"app": "Rouknadz Notifier", "status": "running ✅", "time": datetime.now().isoformat()}

@app.get("/health")
async def health():
    return {"status": "ok"}
