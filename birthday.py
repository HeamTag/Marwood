import discord
from discord.ext import commands, tasks
import json
from datetime import datetime, time
import os

# --- CONFIGURATION ---
BOT_TOKEN = "MTM3Mjk1MTc3ODM3MDI1NzAwOQ.GvbRrL.iA6nY76XIbXze5x_1qdhlrAp4NAv5xWVBMHEjo"  # Replace with your bot's token
COMMAND_PREFIX = "!"
BIRTHDAY_FILE = "birthdays.json"
# ID канала, куда будут отправляться сообщения о днях рождения по умолчанию.
# Чтобы получить ID канала, включите Режим Разработчика в Discord (Настройки пользователя > Расширенные),
# затем кликните правой кнопкой мыши по каналу и "Копировать ID".
DEFAULT_BIRTHDAY_CHANNEL_ID = 1175447652486369430 # Replace with your desired channel ID
DEFAULT_BIRTHDAY_MESSAGE = "🎉 С Днем Рождения, {mention}! Желаем фантастического дня! 🥳"

# --- INTENTS ---
intents = discord.Intents.default()
intents.guilds = True
intents.members = True # Необходимо для получения объектов участников по ID и для упоминаний
intents.messages = True
intents.message_content = True # Необходимо для чтения содержимого сообщений для команд

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# --- DATA HANDLING ---
def load_birthdays():
    """Загружает дни рождения из JSON файла."""
    if not os.path.exists(BIRTHDAY_FILE):
        with open(BIRTHDAY_FILE, 'w', encoding='utf-8') as f: # Добавлено encoding='utf-8'
            json.dump({}, f)
        return {}
    try:
        with open(BIRTHDAY_FILE, 'r', encoding='utf-8') as f: # Добавлено encoding='utf-8'
            data = json.load(f)
            # Обеспечиваем правильную структуру данных при загрузке
            return {str(guild_id): {
                        "config": guild_data.get("config", {}),
                        "users": {str(user_id): bday for user_id, bday in guild_data.get("users", {}).items()}
                    } for guild_id, guild_data in data.items()}
    except json.JSONDecodeError:
        print(f"Ошибка: Не удалось декодировать {BIRTHDAY_FILE}. Используется пустой список дней рождения.")
        return {}
    except Exception as e:
        print(f"Произошла непредвиденная ошибка при загрузке {BIRTHDAY_FILE}: {e}")
        return {}


def save_birthdays(birthdays):
    """Сохраняет дни рождения в JSON файл."""
    try:
        with open(BIRTHDAY_FILE, 'w', encoding='utf-8') as f: # Добавлено encoding='utf-8'
            json.dump(birthdays, f, indent=4, ensure_ascii=False) # Добавлено ensure_ascii=False
    except Exception as e:
        print(f"Произошла ошибка при сохранении {BIRTHDAY_FILE}: {e}")

# --- BOT EVENTS ---
@bot.event
async def on_ready():
    print(f'{bot.user.name} подключился к Discord!')
    print(f'ID Бота: {bot.user.id}')
    print(f'Отслеживает {len(bot.guilds)} серверов.')
    check_birthdays.start()

# --- COMMANDS ---
@bot.command(name='setbirthdaychannel', help='Устанавливает канал для объявлений о днях рождения. Пример: !setbirthdaychannel #канал')
@commands.has_permissions(administrator=True)
async def set_birthday_channel(ctx, channel: discord.TextChannel):
    birthdays_data = load_birthdays()
    guild_id_str = str(ctx.guild.id)

    if guild_id_str not in birthdays_data:
        birthdays_data[guild_id_str] = {"config": {}, "users": {}}
    elif "config" not in birthdays_data[guild_id_str]:
         birthdays_data[guild_id_str]["config"] = {}

    birthdays_data[guild_id_str]["config"]["birthday_channel_id"] = channel.id
    save_birthdays(birthdays_data)
    await ctx.send(f"Канал для поздравлений установлен на {channel.mention}")

@bot.command(name='setbirthdaymessage', help='Устанавливает сообщение для поздравления. Используйте {mention} для пинга. Пример: !setbirthdaymessage С Днем Рождения, {mention}!')
@commands.has_permissions(administrator=True)
async def set_birthday_message(ctx, *, message: str):
    birthdays_data = load_birthdays()
    guild_id_str = str(ctx.guild.id)

    if guild_id_str not in birthdays_data:
        birthdays_data[guild_id_str] = {"config": {}, "users": {}}
    elif "config" not in birthdays_data[guild_id_str]:
        birthdays_data[guild_id_str]["config"] = {}

    if "{mention}" not in message:
        await ctx.send("Внимание: Ваше сообщение не содержит '{mention}'. Пользователь не будет упомянут.")

    birthdays_data[guild_id_str]["config"]["birthday_message"] = message
    save_birthdays(birthdays_data)
    await ctx.send(f"Сообщение для поздравлений на этом сервере обновлено.")

@bot.command(name='addbirthday', help='Добавляет день рождения пользователя. Пример: !addbirthday @Пользователь ММ-ДД')
@commands.has_permissions(manage_nicknames=True) # Разрешить пользователям, которые могут управлять никнеймами, или администраторам
async def add_birthday(ctx, user: discord.Member, birthday_str: str):
    try:
        datetime.strptime(birthday_str, '%m-%d')
    except ValueError:
        await ctx.send("Неверный формат даты. Пожалуйста, используйте ММ-ДД (например, 03-15 для 15 марта).")
        return

    birthdays_data = load_birthdays()
    guild_id_str = str(ctx.guild.id)
    user_id_str = str(user.id)

    if guild_id_str not in birthdays_data:
        birthdays_data[guild_id_str] = {"config": {}, "users": {}}
    if "users" not in birthdays_data[guild_id_str]: # Убедимся, что ключ "users" существует
        birthdays_data[guild_id_str]["users"] = {}


    birthdays_data[guild_id_str]["users"][user_id_str] = birthday_str
    save_birthdays(birthdays_data)
    await ctx.send(f"День рождения для {user.mention} установлен на {birthday_str}.")

@bot.command(name='removebirthday', help='Удаляет день рождения пользователя. Пример: !removebirthday @Пользователь')
@commands.has_permissions(manage_nicknames=True)
async def remove_birthday(ctx, user: discord.Member):
    birthdays_data = load_birthdays()
    guild_id_str = str(ctx.guild.id)
    user_id_str = str(user.id)

    if guild_id_str in birthdays_data and "users" in birthdays_data[guild_id_str] and user_id_str in birthdays_data[guild_id_str]["users"]:
        del birthdays_data[guild_id_str]["users"][user_id_str]
        save_birthdays(birthdays_data)
        await ctx.send(f"День рождения для {user.mention} удален.")
    else:
        await ctx.send(f"День рождения для {user.mention} на этом сервере не найден.")

@bot.command(name='viewbirthdays', help='Посмотреть все сохраненные дни рождения для этого сервера.')
async def view_birthdays(ctx):
    birthdays_data = load_birthdays()
    guild_id_str = str(ctx.guild.id)

    guild_data = birthdays_data.get(guild_id_str)
    if not guild_data or not guild_data.get("users"):
        await ctx.send("Для этого сервера еще не сохранено ни одного дня рождения.")
        return

    server_birthdays = guild_data["users"]
    if not server_birthdays: # Дополнительная проверка, если users пуст
        await ctx.send("Для этого сервера еще не сохранено ни одного дня рождения.")
        return

    embed = discord.Embed(title=f"Дни рождения на сервере {ctx.guild.name}", color=discord.Color.blue())
    description_parts = []
    for user_id_str, bday_str in server_birthdays.items():
        try:
            user = await bot.fetch_user(int(user_id_str))
            user_name = user.display_name if user else f"ID Пользователя: {user_id_str}"
            description_parts.append(f"{user_name}: {bday_str}")
        except discord.NotFound:
            description_parts.append(f"ID Пользователя {user_id_str} (Не найден): {bday_str}")
        except Exception as e:
            print(f"Ошибка при получении пользователя {user_id_str}: {e}")
            description_parts.append(f"ID Пользователя {user_id_str} (Ошибка): {bday_str}")

    if not description_parts:
        embed.description = "Дни рождения не найдены."
    else:
        embed.description = "\n".join(description_parts)
    await ctx.send(embed=embed)

@bot.command(name='mybirthday', help='Проверить свой сохраненный день рождения.')
async def my_birthday(ctx):
    birthdays_data = load_birthdays()
    guild_id_str = str(ctx.guild.id)
    user_id_str = str(ctx.author.id)

    guild_birthdays = birthdays_data.get(guild_id_str, {}).get("users", {})
    if user_id_str in guild_birthdays:
        bday = guild_birthdays[user_id_str]
        await ctx.send(f"{ctx.author.mention}, ваш день рождения установлен на: {bday}")
    else:
        await ctx.send(f"{ctx.author.mention}, ваш день рождения не установлен на этом сервере. Попросите администратора добавить его с помощью `!addbirthday @ВашеИмя ММ-ДД`.")

# --- НОВАЯ КОМАНДА ТЕСТ ---
@bot.command(name='тест', help='Тестирует отправку поздравления пользователю по его ID. Пример: !тест 123456789012345678')
@commands.has_permissions(administrator=True) # Только администраторы могут использовать эту команду
async def test_congratulate(ctx, user_id_input: str):
    """Тестирует отправку поздравления конкретному пользователю по его ID."""
    guild = ctx.guild
    if not guild:
        await ctx.send("Эта команда должна быть использована на сервере.")
        return

    birthdays_data = load_birthdays()
    guild_id_str = str(guild.id)

    # Получаем конфигурацию сервера, или пустой словарь если ее нет
    guild_specific_data = birthdays_data.get(guild_id_str, {})
    guild_config = guild_specific_data.get("config", {})

    channel_id = guild_config.get("birthday_channel_id")
    if not channel_id: # Если в конфиге нет, используем дефолтный
        channel_id = DEFAULT_BIRTHDAY_CHANNEL_ID
        if channel_id == 123456789012345678: # Если дефолтный все еще плейсхолдер
             await ctx.send(f"Канал для поздравлений не настроен для этого сервера (`!setbirthdaychannel`) и ID канала по умолчанию недействителен.")
             return

    birthday_message_template = guild_config.get("birthday_message", DEFAULT_BIRTHDAY_MESSAGE)

    target_channel = guild.get_channel(int(channel_id)) # Убедимся что channel_id это int
    if not target_channel:
        await ctx.send(f"Канал для поздравлений (ID: {channel_id}) не найден на этом сервере. Проверьте настройки (`!setbirthdaychannel`) или ID канала по умолчанию.")
        return

    try:
        user_id_to_test = int(user_id_input)
    except ValueError:
        await ctx.send(f"'{user_id_input}' не является действительным ID пользователя. Пожалуйста, введите числовой ID.")
        return

    member_to_test = None
    try:
        member_to_test = await guild.fetch_member(user_id_to_test)
    except discord.NotFound:
        await ctx.send(f"Пользователь с ID `{user_id_to_test}` не найден на этом сервере.")
        return
    except discord.HTTPException as e:
        await ctx.send(f"Произошла ошибка при поиске пользователя: {e}")
        return

    if member_to_test:
        try:
            # Формируем сообщение, обрабатывая возможные отсутствующие ключи в format
            message_to_send = birthday_message_template.format(mention=member_to_test.mention, user=member_to_test, name=member_to_test.display_name)
            await target_channel.send(message_to_send)
            await ctx.send(f"Тестовое поздравление отправлено для {member_to_test.mention} в канал {target_channel.mention}.")
            print(f"Тестовое поздравление отправлено для {member_to_test.display_name} ({member_to_test.id}) в {guild.name} по команде от {ctx.author.name} ({ctx.author.id})")
        except discord.Forbidden:
            await ctx.send(f"Ошибка: У бота нет прав для отправки сообщений в канал {target_channel.mention}.")
            print(f"Ошибка прав доступа при тестовой отправке в {target_channel.name} ({target_channel.id}) на сервере {guild.name}.")
        except KeyError as e:
            await ctx.send(f"Ошибка в шаблоне сообщения: отсутствует ключ `{e}`. Убедитесь, что ваше сообщение использует только допустимые плейсхолдеры (например, {{mention}}, {{name}}).")
            print(f"Ошибка KeyError при форматировании сообщения: {e}")
        except Exception as e:
            await ctx.send(f"Произошла ошибка при отправке тестового сообщения: {e}")
            print(f"Ошибка при отправке тестового сообщения для {member_to_test.display_name}: {e}")
    # else: # Это условие уже покрыто обработкой fetch_member
    #     await ctx.send(f"Не удалось найти пользователя с ID `{user_id_to_test}` на этом сервере.")


# --- BACKGROUND TASK ---
# Запускает проверку ежедневно в указанное время (например, 7:00 UTC)
@tasks.loop(time=time(hour=7, minute=0, second=0))
async def check_birthdays():
    await bot.wait_until_ready()
    print(f"Запуск ежедневной проверки дней рождения в {datetime.now()}...")
    birthdays_data = load_birthdays()
    today_str = datetime.now().strftime('%m-%d')

    for guild_id_str, data in birthdays_data.items():
        guild = bot.get_guild(int(guild_id_str))
        if not guild:
            print(f"Сервер {guild_id_str} не найден. Пропуск.")
            continue

        config = data.get("config", {})
        users_birthdays = data.get("users", {})

        channel_id = config.get("birthday_channel_id")
        if not channel_id:
            channel_id = DEFAULT_BIRTHDAY_CHANNEL_ID
            if channel_id == 123456789012345678: # Плейсхолдер
                print(f"Канал для поздравлений не настроен для сервера {guild.name} ({guild_id_str}) и ID канала по умолчанию недействителен. Пропуск.")
                continue


        birthday_message_template = config.get("birthday_message", DEFAULT_BIRTHDAY_MESSAGE)

        target_channel = guild.get_channel(int(channel_id))
        if not target_channel:
            print(f"Канал для поздравлений ID {channel_id} не найден на сервере {guild.name} ({guild_id_str}).")
            continue

        for user_id_str, birthday_date_str in users_birthdays.items():
            if birthday_date_str == today_str:
                member = guild.get_member(int(user_id_str))
                if not member: # Если нет в кэше, пробуем загрузить
                    try:
                        member = await guild.fetch_member(int(user_id_str))
                    except discord.NotFound:
                        print(f"Участник с ID {user_id_str} не найден на сервере {guild.name} для поздравления.")
                        continue
                    except discord.HTTPException as e:
                        print(f"Не удалось получить участника с ID {user_id_str} на сервере {guild.name} из-за ошибки HTTP: {e}")
                        continue

                if member:
                    try:
                        message_to_send = birthday_message_template.format(mention=member.mention, user=member, name=member.display_name)
                        await target_channel.send(message_to_send)
                        print(f"Отправлено поздравление {member.display_name} на сервере {guild.name}")
                    except discord.Forbidden:
                        print(f"Ошибка: У бота нет прав для отправки сообщений в канал {target_channel.name} ({target_channel.id}) на сервере {guild.name}.")
                    except KeyError as e:
                        print(f"Ошибка в шаблоне сообщения для ежедневной рассылки: отсутствует ключ `{e}`. Сервер: {guild.name}")
                    except Exception as e:
                        print(f"Ошибка при отправке поздравления для {member.display_name}: {e}")

@check_birthdays.before_loop
async def before_check_birthdays():
    await bot.wait_until_ready()
    print("Цикл проверки дней рождения запускается.")

# --- ERROR HANDLING FOR COMMANDS ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Неверная команда. Попробуйте `!help` для просмотра доступных команд.")
    elif isinstance(error, commands.MissingRequiredArgument):
        param = error.param.name
        usage = f"`!{ctx.command.name} {ctx.command.signature}`"
        await ctx.send(f"Отсутствует обязательный аргумент: `{param}`. \nПример использования: {usage}")
    elif isinstance(error, commands.BadArgument):
        usage = f"`!{ctx.command.name} {ctx.command.signature}`"
        await ctx.send(f"Неверный аргумент. Пожалуйста, проверьте справку по команде. \nПример использования: {usage}")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("У вас нет необходимых прав для выполнения этой команды.")
    elif isinstance(error, commands.BotMissingPermissions):
        perms_needed = "\n- ".join(error.missing_permissions)
        await ctx.send(f"У меня нет необходимых прав для выполнения этого действия. Мне нужны права:\n- {perms_needed}")
    elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.NotFound):
        if ctx.command.name == 'тест': # Уже обрабатывается внутри команды
            pass
        else:
            print(f"Произошла ошибка выполнения команды (NotFound): {error.original}")
            await ctx.send("Произошла ошибка: Ресурс не найден.")
    else:
        print(f"Произошла ошибка ({type(error).__name__}): {error}")
        await ctx.send("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже или свяжитесь с разработчиком бота, если проблема повторяется.")

# --- RUN THE BOT ---
if __name__ == "__main__":
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ОШИБКА: Пожалуйста, замените 'YOUR_BOT_TOKEN_HERE' на ваш актуальный токен бота в скрипте.")
    elif DEFAULT_BIRTHDAY_CHANNEL_ID == 123456789012345678: # Проверяем плейсхолдер
        print("ПРЕДУПРЕЖДЕНИЕ: DEFAULT_BIRTHDAY_CHANNEL_ID установлен на плейсхолдер. "
              "Убедитесь, что вы установили действительный ID по умолчанию или используйте !setbirthdaychannel на каждом сервере, иначе бот не сможет отправлять сообщения по умолчанию или в ежедневной проверке без настроенного канала.")
    # else: # Бот запустится даже если DEFAULT_BIRTHDAY_CHANNEL_ID плейсхолдер, но с предупреждением
    try:
        bot.run(BOT_TOKEN)
    except discord.LoginFailure:
        print("Ошибка входа: Убедитесь, что ваш BOT_TOKEN указан верно и вы включили необходимые намерения (intents) на Портале разработчиков Discord.")
    except Exception as e:
        print(f"Произошла ошибка при попытке запуска бота: {e}")
