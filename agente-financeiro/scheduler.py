import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from telegram.ext import Application

from config import DB_PATH, TELEGRAM_GROUP_ID
from database import list_dividas
from reports import format_daily_summary, format_monthly_summary

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("America/Sao_Paulo")


def setup_scheduler(application: Application) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")

    async def daily_summary() -> None:
        try:
            today = datetime.now(_TZ).date()
            text = format_daily_summary(DB_PATH, today.isoformat())
            await application.bot.send_message(chat_id=TELEGRAM_GROUP_ID, text=text)
        except Exception as exc:
            logger.error("daily_summary job error: %s", exc)

    async def monthly_summary() -> None:
        try:
            today = datetime.now(_TZ).date()
            first_of_month = today.replace(day=1)
            prev_month_last = first_of_month - timedelta(days=1)
            text = format_monthly_summary(DB_PATH, prev_month_last.year, prev_month_last.month)
            await application.bot.send_message(chat_id=TELEGRAM_GROUP_ID, text=text)
        except Exception as exc:
            logger.error("monthly_summary job error: %s", exc)

    async def debt_alert() -> None:
        try:
            today = datetime.now(_TZ).date()
            upcoming_dates = [today + timedelta(days=i) for i in range(1, 4)]

            dividas = list_dividas(DB_PATH)
            alertas = []
            for d in dividas:
                if d.get("status") == "quitado":
                    continue
                venc = d.get("vencimento_dia")
                if venc is None:
                    continue
                for upcoming in upcoming_dates:
                    if upcoming.day == venc:
                        dias_restantes = (upcoming - today).days
                        alertas.append((d["nome"], upcoming.isoformat(), dias_restantes))
                        break

            if alertas:
                lines = ["⚠️ *Dívidas com vencimento próximo:*\n"]
                for nome, venc_date, dias in alertas:
                    nome_safe = escape_markdown(nome, version=1)
                    lines.append(f"• *{nome_safe}* — vence em {venc_date} ({dias} dia(s))")
                text = "\n".join(lines)
                await application.bot.send_message(
                    chat_id=TELEGRAM_GROUP_ID, text=text, parse_mode=ParseMode.MARKDOWN
                )
        except Exception as exc:
            logger.error("debt_alert job error: %s", exc)

    scheduler.add_job(daily_summary, "cron", hour=22, minute=0, id="daily_summary")
    scheduler.add_job(monthly_summary, "cron", day=1, hour=8, minute=0, id="monthly_summary")
    scheduler.add_job(debt_alert, "cron", hour=9, minute=0, id="debt_alert")

    scheduler.start()
    return scheduler
