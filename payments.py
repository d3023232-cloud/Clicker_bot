"""Telegram Stars payments"""
import config
import data_manager

async def pre_checkout_handler(update, context):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_handler(update, context):
    user_id = update.effective_user.id
    successful_payment = update.message.successful_payment
    payload = successful_payment.invoice_payload
    if payload.startswith("donat_"):
        item_key = payload[6:]
        if item_key in config.DONAT_SHOP:
            item = config.DONAT_SHOP[item_key]
            data_manager.user_data[user_id]["donate_coins"] += item["cost"]
            data_manager.save_data()
            await update.message.reply_text(
                "Payment successful!" + chr(10) + f"You got: {item['name']} ({item['cost']} diamonds)"
            )
        else:
            await update.message.reply_text("Unknown item.")
    else:
        await update.message.reply_text("Unknown payment.")
