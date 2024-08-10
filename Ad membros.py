
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters
from telegram.error import BadRequest
from datetime import datetime, timedelta

# Configurações básicas
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Armazenamento simples para números e grupos
numbers = {}
groups_to_search = []
group_to_add = ""
member_count = 0

def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Adicionar números", callback_data='add_numbers')],
        [InlineKeyboardButton("Adicionar membros", callback_data='add_members')],
        [InlineKeyboardButton("Buscar grupos", callback_data='search_groups')],
        [InlineKeyboardButton("Adicionar ao grupo", callback_data='add_to_group')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Escolha uma opção:', reply_markup=reply_markup)

def add_numbers(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Adicionar", callback_data='add_number')],
        [InlineKeyboardButton("Voltar", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(
        'Números cadastrados: ' + ', '.join(numbers.keys()) if numbers else 'Nenhum número cadastrado.',
        reply_markup=reply_markup
    )

def add_number(update: Update, context: CallbackContext):
    update.callback_query.message.reply_text('Envie o número de Telegram para adicionar:')
    return 'WAITING_FOR_NUMBER'

def handle_number(update: Update, context: CallbackContext):
    number = update.message.text
    if number in numbers:
        update.message.reply_text('Número já cadastrado.')
    else:
        numbers[number] = []
        update.message.reply_text('Número adicionado.')
    start(update, context)
    return 'START'

def add_members(update: Update, context: CallbackContext):
    update.callback_query.message.reply_text('Quantos membros deseja adicionar (máx. 50 por número)?')
    return 'WAITING_FOR_MEMBER_COUNT'

def handle_member_count(update: Update, context: CallbackContext):
    global member_count
    try:
        count = int(update.message.text)
        if count <= 50:
            member_count = count
            update.message.reply_text('Quantos membros deseja adicionar ao grupo?')
            return 'WAITING_FOR_GROUP_NAME'
        else:
            update.message.reply_text('O número máximo é 50.')
            return 'WAITING_FOR_MEMBER_COUNT'
    except ValueError:
        update.message.reply_text('Por favor, envie um número válido.')
        return 'WAITING_FOR_MEMBER_COUNT'

def search_groups(update: Update, context: CallbackContext):
    update.callback_query.message.reply_text('Envie o nome dos grupos (máx. 5), separados por vírgula:')
    return 'WAITING_FOR_GROUP_NAMES'

def handle_group_names(update: Update, context: CallbackContext):
    group_names = update.message.text.split(',')
    if len(group_names) > 5:
        update.message.reply_text('Você pode adicionar no máximo 5 grupos.')
    else:
        global groups_to_search
        groups_to_search = [name.strip() for name in group_names]
        update.message.reply_text('Grupos cadastrados para busca: ' + ', '.join(groups_to_search))
    start(update, context)
    return 'START'

def add_to_group(update: Update, context: CallbackContext):
    update.callback_query.message.reply_text('Envie o nome do grupo para adicionar membros:')
    return 'WAITING_FOR_GROUP_NAME'

def handle_group_name(update: Update, context: CallbackContext):
    global group_to_add
    group_to_add = update.message.text
    update.message.reply_text(f'Grupo {group_to_add} registrado para adicionar membros.')
    start(update, context)
    return 'START'

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    if query.data == 'start':
        start(update, context)
    elif query.data == 'add_numbers':
        add_numbers(update, context)
    elif query.data == 'add_number':
        return add_number(update, context)
    elif query.data == 'add_members':
        return add_members(update, context)
    elif query.data == 'search_groups':
        return search_groups(update, context)
    elif query.data == 'add_to_group':
        return add_to_group(update, context)

def add_members_to_group(bot: Bot, group_id: int, user_ids: list):
    for user_id in user_ids:
        try:
            bot.add_chat_members(chat_id=group_id, user_ids=[user_id])
        except BadRequest as e:
            logger.error(f'Não foi possível adicionar o usuário {user_id}: {e}')

def handle_add_members(update: Update, context: CallbackContext):
    global group_to_add, member_count
    if group_to_add and member_count > 0:
        bot = context.bot
        chat = bot.get_chat(group_to_add)
        members = bot.get_chat_administrators(chat.id)
        active_members = [member.user.id for member in members if (datetime.now() - member.user.last_seen) < timedelta(hours=72)]
        
        for number in numbers.keys():
            if len(active_members) >= member_count:
                break
            for user_id in numbers[number]:
                if len(active_members) >= member_count:
                    break
                if user_id not in active_members:
                    add_members_to_group(bot, chat.id, [user_id])
        
        update.message.reply_text('Membros adicionados com sucesso.')
    else:
        update.message.reply_text('Nenhum grupo registrado ou número de membros inválido.')

def main():
    updater = Updater("7334268988:AAG-AQs4xa12rKls8DtRCad3JCuIZrORZxQ", use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_number))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_member_count))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_group_names))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_group_name))

    dp.add_handler(CallbackQueryHandler(button))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
