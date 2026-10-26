import re
import logging
from datetime import date, datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

import config
from config import (
    TELEGRAM_BOT_TOKEN,
    ANTHROPIC_API_KEY,
    DB_PATH,
    USER_MAP,
    VALID_CATEGORIES,
)
from database import (
    init_db,
    add_transaction,
    set_limit,
)
from claude_parser import parse_transaction, parse_extrato
from reports import (
    format_daily_summary,
    format_monthly_summary,
    format_dividas,
    check_category_alert,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── helpers ─────────────────────────────────────────────────────────────────

EXTRATO_DATE_VALUE_RE = re.compile(
    r"(\d{1,2}[/\-]\d{1,2}|\d{4}-\d{2}-\d{2}).*?R?\$\s*[\d.,]+",
    re.IGNORECASE,
)


def _is_extrato(text: str) -> bool:
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) <= 5:
        return False
    matches = EXTRATO_DATE_VALUE_RE.findall(text)
    return len(matches) >= 3


def _get_pessoa(update: Update) -> str | None:
    uid = update.effective_user.id if update.effective_user else None
    return USER_MAP.get(uid)


# ─── handlers ────────────────────────────────────────────────────────────────


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pessoa = _get_pessoa(update)
    if pessoa is None:
        return

    text = update.message.text or ""

    # Detect extrato
    if _is_extrato(text):
        try:
            transacoes = parse_extrato(text, ANTHROPIC_API_KEY)
        except Exception as exc:
            logger.error("parse_extrato error: %s", exc)
            await update.message.reply_text(
                "❌ Erro ao processar extrato. Tente novamente.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        if not transacoes:
            await update.message.reply_text(
                "Não encontrei transações no extrato enviado.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        context.user_data["pending_extrato"] = {"transacoes": transacoes, "pessoa": pessoa}
        n = len(transacoes)
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"Registrar {n} transações", callback_data="extrato_confirm"
                    ),
                    InlineKeyboardButton("Cancelar", callback_data="extrato_cancel"),
                ]
            ]
        )
        await update.message.reply_text(
            f"Encontrei *{n} transações* no extrato. Deseja registrá-las?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
        return

    # Regular transaction
    try:
        resultado = parse_transaction(text, pessoa, ANTHROPIC_API_KEY)
    except Exception as exc:
        logger.error("parse_transaction error: %s", exc)
        await update.message.reply_text(
            "❌ Erro ao processar mensagem. Tente novamente.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if resultado is None:
        await update.message.reply_text(
            "Não entendi. Ex: *gastei R$45 no iFood* ou *recebi salário R$4500*",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    hoje = date.today()
    # Security: identity and date always come from server, never from LLM output
    add_transaction(
        DB_PATH,
        pessoa=pessoa,
        valor=resultado["valor"],
        descricao=resultado.get("descricao", ""),
        categoria=resultado.get("categoria", "outros"),
        tipo=resultado["tipo"],
        data=hoje.isoformat(),
    )

    # Security: escape description to prevent Markdown injection
    descricao_safe = escape_markdown(resultado.get("descricao", ""), version=1)
    tipo_label = "💸 Gasto" if resultado["tipo"] == "gasto" else "💰 Receita"
    msg = (
        f"{tipo_label} registrado!\n"
        f"*{descricao_safe}* — R$ {resultado['valor']:.2f}\n"
        f"Categoria: _{resultado.get('categoria', 'outros')}_"
    )

    # Category alert
    try:
        alert = check_category_alert(
            DB_PATH,
            resultado.get("categoria", "outros"),
            resultado["valor"],
            hoje.year,
            hoje.month,
        )
    except Exception as e:
        logger.warning("check_category_alert falhou: %s", e)
        alert = None
    if alert:
        msg += f"\n\n⚠️ {alert}"

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def handle_extrato_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    pessoa = _get_pessoa(update)
    if pessoa is None:
        await query.edit_message_text("Usuário não autorizado.")
        return

    data = context.user_data.get("pending_extrato")
    if not data:
        await query.edit_message_text("Sessão expirada. Envie o extrato novamente.")
        return

    if query.data == "extrato_cancel":
        context.user_data.pop("pending_extrato", None)
        await query.edit_message_text("Extrato cancelado.")
        return

    # confirm
    transacoes = data["transacoes"]
    pessoa_extrato = data.get("pessoa", pessoa)
    hoje = date.today()
    registradas = 0
    for t in transacoes:
        try:
            add_transaction(
                DB_PATH,
                pessoa=t.get("pessoa", pessoa_extrato),
                valor=t["valor"],
                descricao=t.get("descricao", ""),
                categoria=t.get("categoria", "outros"),
                tipo=t["tipo"],
                data=t.get("data", hoje.isoformat()),
            )
            registradas += 1
        except Exception as exc:
            logger.error("Error saving extrato transaction: %s", exc)

    context.user_data.pop("pending_extrato", None)
    await query.edit_message_text(
        f"✅ *{registradas} transações* registradas com sucesso!",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── commands ────────────────────────────────────────────────────────────────


async def cmd_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pessoa = _get_pessoa(update)
    if pessoa is None:
        return
    hoje = date.today()
    msg = format_monthly_summary(DB_PATH, hoje.year, hoje.month)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_hoje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pessoa = _get_pessoa(update)
    if pessoa is None:
        return
    hoje = date.today()
    msg = format_daily_summary(DB_PATH, hoje.isoformat())
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_dividas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pessoa = _get_pessoa(update)
    if pessoa is None:
        return
    msg = format_dividas(DB_PATH)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_limite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pessoa = _get_pessoa(update)
    if pessoa is None:
        return
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "Uso: /limite *<categoria>* *<valor>*\nEx: /limite alimentacao 500",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    categoria = args[0].lower()
    if categoria not in VALID_CATEGORIES:
        cats = ", ".join(f"`{c}`" for c in VALID_CATEGORIES)
        await update.message.reply_text(
            f"Categoria inválida. Válidas: {cats}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        valor = float(args[1].replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            "Valor inválido. Use números, ex: /limite alimentacao 500",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    set_limit(DB_PATH, categoria, valor)
    await update.message.reply_text(
        f"✅ Limite de *{categoria}* definido para R$ {valor:.2f}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_categorias(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    pessoa = _get_pessoa(update)
    if pessoa is None:
        return
    cats = "\n".join(f"• `{c}`" for c in VALID_CATEGORIES)
    await update.message.reply_text(
        f"*Categorias disponíveis:*\n{cats}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pessoa = _get_pessoa(update)
    if pessoa is None:
        return
    msg = (
        "*Comandos disponíveis:*\n\n"
        "/resumo — Resumo mensal de gastos e receitas\n"
        "/hoje — Resumo do dia de hoje\n"
        "/dividas — Lista de dívidas abertas\n"
        "/limite <categoria> <valor> — Define limite de gasto por categoria\n"
        "/categorias — Lista todas as categorias disponíveis\n"
        "/ajuda — Exibe esta mensagem\n\n"
        "*Para registrar uma transação*, envie uma mensagem como:\n"
        "• _gastei R$45 no iFood_\n"
        "• _recebi salário R$4500_\n"
        "• _paguei R$120 de luz_"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


# ─── main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    init_db(DB_PATH)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("resumo", cmd_resumo))
    app.add_handler(CommandHandler("hoje", cmd_hoje))
    app.add_handler(CommandHandler("dividas", cmd_dividas))
    app.add_handler(CommandHandler("limite", cmd_limite))
    app.add_handler(CommandHandler("categorias", cmd_categorias))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))

    # Callback for extrato inline buttons
    app.add_handler(
        CallbackQueryHandler(handle_extrato_confirm, pattern="^extrato_")
    )

    # Text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
