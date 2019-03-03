#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Simple Bot to reply to Telegram messages.

This program is dedicated to the public domain under the CC0 license.

This Bot uses the Updater class to handle the bot.

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import logging
import os
import random

import pymongo
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

mongo = MongoClient(os.environ['DB_URL']).chfm_bot
user = mongo.user
user.create_index([("user_id", pymongo.DESCENDING), ], background=False, unique=True)

USER_STATE_FREE = 0
USER_STATE_START_ADDING_WAYS = 1
USER_STATE_ADDING_WAYS = 2
USER_STATE_FINISH_ADDING_WAYS = 3
USER_STATE_SORT = 4
USER_STATE_SORT_1 = 41
USER_STATE_SORT_2 = 42
USER_STATE_SCORE = 5
USER_STATE_RESULT = 6
USER_STATE_CANCEL = -1


def print_matrix(matrix):
    for i in matrix:
        print('\t'.join([str(num) for num in i]))
    print('\n')



def variant_processor(matrix, stack):
    reverse = {
        1: -1,
        -1: 1
    }
    if not stack:
        return matrix
    a, is_bigger, b = stack.pop()
    if matrix[a][b] != 0:
        return variant_processor(matrix, stack)

    matrix[a][b] = is_bigger
    if matrix[b][a] == 0:
        stack.append((b, reverse[is_bigger], a))
    for cell in range(len(matrix[b])):
        if matrix[b][cell] == is_bigger and cell != a:
            stack.append((a, is_bigger, cell))
    return variant_processor(matrix, stack)


def start(bot, update):
    keyboard = [[InlineKeyboardButton("Поїхали", callback_data=str(USER_STATE_START_ADDING_WAYS))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    user.update_one(
        {'user_id': update.effective_user.id},
        {'$set': {'state': USER_STATE_FREE}},
        upsert=True
    )
    message = 'Мяу! Я готовий допомогти вам зробити Ваш вибір!'
    if update.callback_query:
        bot.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            chat_id=update.callback_query.message.chat_id,
            message_id=update.callback_query.message.message_id
        )
    else:
        update.message.reply_text(
            text=message,
            reply_markup=reply_markup
        )


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def promote_enter_way(bot, update):
    bot.edit_message_text(
        text='Додайте один з варіантів вашого шляху.',
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id
    )


def promote_add_way(bot, update):
    keyboard = [
        [InlineKeyboardButton("Відмінити", callback_data=str(USER_STATE_CANCEL))],
    ]
    user_info = user.find_one({'user_id': update.effective_user.id})
    responce_count = len(user_info['choices_states'][-1]['choices_list'])
    text = (
        'Чудово! Додайте ще варіантів,  або скористайтесь кнопкою `Відмінити` для виходу.\n\n'
        'З.І. \nУ кожної проблеми є як мінімум два рішення,  хоч обидва можуть не подобатись'
    )
    if responce_count > 1:
        keyboard.insert(
            0,
            [InlineKeyboardButton("Більше нема варіантів", callback_data=str(USER_STATE_FINISH_ADDING_WAYS))]
        )
        text = (
            'Чудово! Додайте ще варіантів,  або скористайтесь кнопкою `Відмінити` для виходу або ж кнопкою '
            '`Більше нема варіантів` для того, аби перейти до наступного етапу в визначенні шляху'
        )
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


def choose_select_option(bot, update):
    keyboard = [
        [
            InlineKeyboardButton("Посортуэмо", callback_data=str(USER_STATE_SORT)),
            InlineKeyboardButton("Оцінимо", callback_data=str(USER_STATE_SCORE))
        ],
        [InlineKeyboardButton("Дай мені відповідь", callback_data=str(USER_STATE_RESULT))],
        [InlineKeyboardButton("Відмінити", callback_data=str(USER_STATE_CANCEL))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        text='Отож;)  Що далі?  Я рекомендую спочатку відсортувати ваші варіанти,  а потім оцінити їх.  '
             'Але пам\'ятайте,  що вибір завжди за вами)',
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


def get_result(bot, update):
    keyboard = [
        [InlineKeyboardButton("Вибери ще раз!", callback_data=str(USER_STATE_RESULT))],
        [InlineKeyboardButton("Відмінити", callback_data=str(USER_STATE_CANCEL))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user_info = user.find_one({'user_id': update.effective_user.id})
    choices_list = user_info['choices_states'][-1]['choices_list']
    decision_space = []
    for way in choices_list:
        if way['score']<1:
            way['score']=1
        decision_space.extend([way['text']] * way['score'])

    result = decision_space[random.randint(0, len(decision_space) - 1)]

    bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        text=f'Трррррррррдам!\n \nВаш варіант:\n\n**{result}**',
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


def get_random_variant(matrix):
    variants = []
    for i in range(len(matrix)):
        for j in range(len(matrix)):
            if i != j and matrix[i][j] == 0:
                variants.append((i, j))
    if variants:
        return variants[random.randint(0, len(variants) - 1)]
    return None


def promote_sort_variant(bot, update):
    user_info = user.find_one({'user_id': update.effective_user.id})
    user_state = user_info['state']
    user_response = user_info['choices_states'][-1]['choices_list']
    sort_state = user_info['choices_states'][-1]['order']

    a = sort_state.get('a')
    b = sort_state.get('b')
    is_bigger = 1
    if user_state == USER_STATE_SORT_1 or user_state == USER_STATE_SORT_2:
        if user_state == USER_STATE_SORT_2:
            a, b = b, a
    if a is not None and b is not None:
        sort_state['response_matrix'] = variant_processor(sort_state['response_matrix'], [(a, is_bigger, b)])
    next_variant = get_random_variant(sort_state['response_matrix'])
    if next_variant is not None:
        sort_state['a'], sort_state['b'] = next_variant

        text = (
            f"Виберіть один із варіантів::\n\n"
            f"1:: \n\n```{user_info['choices_states'][-1]['choices_list'][sort_state['a']]['text']}``` \n\n"
            f"2:: \n\n```{user_info['choices_states'][-1]['choices_list'][sort_state['b']]['text']}```"
        )
        keyboard = [
            [
                InlineKeyboardButton("1", callback_data=str(USER_STATE_SORT_1)),
                InlineKeyboardButton("2", callback_data=str(USER_STATE_SORT_2))
            ],
            [InlineKeyboardButton("Відмінити", callback_data=str(USER_STATE_CANCEL))],
        ]
    else:
        variant_count = len(sort_state['response_matrix'])
        reponce_position_index = [sum([c for c in row if c<0])*-1 for row in sort_state['response_matrix']]
        sorted_user_reponce = [0] * variant_count
        for position in range(variant_count):
            sorted_user_reponce[reponce_position_index[position]] = user_response[position]
            sorted_user_reponce[reponce_position_index[position]]['order'] = reponce_position_index[position]
        user_info['choices_states'][-1]['choices_list'] = sorted_user_reponce

        user_responces_list = '\n\n'.join([responce['text'] for responce in sorted_user_reponce])
        text = (
            f"Чудово,  все відсортовано,  що далі? \n\nЗ.І. Ось такий список вийшов::\n\n"
            f"{user_responces_list}"
        )
        keyboard = [
            [InlineKeyboardButton("Оцінимо", callback_data=str(USER_STATE_SCORE))],
            [InlineKeyboardButton("Дай мені відповідь", callback_data=str(USER_STATE_RESULT))],
            [InlineKeyboardButton("Відмінити", callback_data=str(USER_STATE_CANCEL))],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

    user.replace_one({'user_id': update.effective_user.id}, user_info)


def start_sort(bot, update):
    user_info = user.find_one({'user_id': update.effective_user.id})
    choices_states = user_info['choices_states'][-1]
    user.replace_one({'user_id': update.effective_user.id}, user_info)
    response_count = len(choices_states['choices_list'])
    choices_states['order'] = {
        'response_matrix': [[0] * response_count for _ in range(response_count)]
    }
    user.replace_one({'user_id': update.effective_user.id}, user_info)
    return promote_sort_variant(bot, update)


def sort_variant1(bot, update):
    user_info = user.find_one({'user_id': update.effective_user.id})
    user_info['state'] = USER_STATE_SORT_1

    user.replace_one({'user_id': update.effective_user.id}, user_info)
    return promote_sort_variant(bot, update)


def sort_variant2(bot, update):
    user_info = user.find_one({'user_id': update.effective_user.id})

    user_info['state'] = USER_STATE_SORT_2
    user.replace_one({'user_id': update.effective_user.id}, user_info)
    return promote_sort_variant(bot, update)

def set_next_score_propose(bot, update):
    user_info = user.find_one({'user_id': update.effective_user.id})

    user_info['state'] = USER_STATE_SCORE
    choices_states = user_info['choices_states'][-1]
    keyboard = None

    unscored_items = [
        i for i in range(len(choices_states['choices_list'])) if choices_states['choices_list'][i]['score']<0
    ]
    if 'score_item' not in choices_states:
        text = (
            "Далі будут відображенні пропозиції оцінити кожен з варіантів.\n"
               "Потрібно ввести ціле, дадтнє число.\n"
            "Чим це число буде більшим,  тим більше ймовірність що в результаті вийде саме той варіант.\n\n"
            "З.І.\n Наприклад якщо у А оцінка 9 а у Б оцінка 1, то якщо нескінченну кількість раз провести вибір,"
            "то співвідношення між А та Б буде рівне 9/1. Тобто на одне випадання Б буде дев'ять випадань А"

        )
        bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )

    if not unscored_items:
        text = "Кул)) Все оцінено,  можем перейти до священного Рандому!"
        keyboard = [
            [InlineKeyboardButton("Дай мені відповідь", callback_data=str(USER_STATE_RESULT))],
            [InlineKeyboardButton("Відмінити", callback_data=str(USER_STATE_CANCEL))],
        ]
    else:
        score_pos = unscored_items[random.randint(0, len(unscored_items) - 1)]
        choices_states['score_item']=score_pos
        text = f"Дайте оцінку варіанту\n\n```{choices_states['choices_list'][score_pos]['text']}```"

    bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=keyboard and InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


    user.replace_one({'user_id': update.effective_user.id}, user_info)


def choose_next_action(bot, update, state):
    return {
        USER_STATE_START_ADDING_WAYS: promote_enter_way,
        USER_STATE_ADDING_WAYS: promote_add_way,
        USER_STATE_CANCEL: start,
        USER_STATE_FINISH_ADDING_WAYS: choose_select_option,
        USER_STATE_RESULT: get_result,
        USER_STATE_SORT: start_sort,
        USER_STATE_SORT_1: sort_variant1,
        USER_STATE_SORT_2: sort_variant2,
        USER_STATE_SCORE: set_next_score_propose,
    }[state](bot, update)


def button(bot, update):
    query = update.callback_query
    command = int(query.data)

    user.update_one(
        {'user_id': update.effective_user.id},
        {'$set': {'state': command}},
    )
    choose_next_action(bot, update, command)


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def message_handler(bot, update):
    user_info = user.find_one({'user_id': update.effective_user.id})
    if user_info['state'] == USER_STATE_START_ADDING_WAYS:
        user_info['state'] = USER_STATE_ADDING_WAYS
        if 'choices_states' not in user_info:
            user_info['choices_states'] = []
        user_info['choices_states'].append({'choices_list': []})

    if user_info['state'] == USER_STATE_ADDING_WAYS:
        user_info['choices_states'][-1]['choices_list'].append(
            {
                'order': -1,
                'text': update.message.text,
                'score': -1,
            }
        )

    if user_info['state'] == USER_STATE_SCORE:
        try:
            num = int(update.message.text)
        except:
            num = -1
        user_info['choices_states'][-1]['choices_list'][user_info['choices_states'][-1]['score_item']]['score'] = num

    user.replace_one({'user_id': update.effective_user.id}, user_info)
    choose_next_action(bot, update, user_info['state'])

def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(os.environ['BOT_TOKEN'])

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("Поїхали", start))
    dp.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text, message_handler, edited_updates=True))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
