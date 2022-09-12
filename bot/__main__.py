from signal import signal, SIGINT
import random
from random import choice
from os import path as ospath, remove as osremove, execl as osexecl
from subprocess import run as srun, check_output
from datetime import datetime, timedelta
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, virtual_memory, net_io_counters, boot_time
from time import time
from sys import executable
from telegram import ParseMode, InlineKeyboardMarkup
from telegram.ext import CommandHandler
import requests
import pytz
from bot import bot, dispatcher, updater, botStartTime, TIMEZONE, IGNORE_PENDING_REQUESTS, LOGGER, Interval, INCOMPLETE_TASK_NOTIFIER, \
                    DB_URI, alive, app, main_loop, HEROKU_API_KEY, HEROKU_APP_NAME, SET_BOT_COMMANDS, AUTHORIZED_CHATS, EMOJI_THEME, \
                    START_BTN1_NAME, START_BTN1_URL, START_BTN2_NAME, START_BTN2_URL, CREDIT_NAME, TITLE_NAME, PICS, FINISHED_PROGRESS_STR, UN_FINISHED_PROGRESS_STR, \
                    SHOW_LIMITS_IN_STATS, LEECH_LIMIT, TORRENT_DIRECT_LIMIT, CLONE_LIMIT, MEGA_LIMIT, ZIP_UNZIP_LIMIT, TOTAL_TASKS_LIMIT, USER_TASKS_LIMIT
from .helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from .helper.ext_utils.db_handler import DbManger
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.message_utils import sendMessage, sendMarkup, editMessage, sendLogFile, sendPhoto
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker
from bot.modules.wayback import getRandomUserAgent
from .modules import authorize, list, cancel_mirror, mirror_status, mirror_leech, clone, ytdlp, shell, eval, \
                    delete, count, leech_settings, search, rss, wayback, speedtest, usage, anilist, bt_select, mediainfo, hash, sleep
from datetime import datetime

try: import heroku3
except ModuleNotFoundError: srun("pip install heroku3", capture_output=False, shell=True)
try: import heroku3
except Exception as f:
    LOGGER.warning("heroku3 cannot imported. add to your deployer requirements.txt file.")
    LOGGER.warning(f)
    HEROKU_APP_NAME = None
    HEROKU_API_KEY = None
    
def getHerokuDetails(h_api_key, h_app_name):
    try: import heroku3
    except ModuleNotFoundError: run("pip install heroku3", capture_output=False, shell=True)
    try: import heroku3
    except Exception as f:
        LOGGER.warning("heroku3 cannot imported. add to your deployer requirements.txt file.")
        LOGGER.warning(f)
        return None
    if (not h_api_key) or (not h_app_name): return None
    try:
        heroku_api = "https://api.heroku.com"
        Heroku = heroku3.from_key(h_api_key)
        app = Heroku.app(h_app_name)
        useragent = getRandomUserAgent()
        user_id = Heroku.account().id
        headers = {
            "User-Agent": useragent,
            "Authorization": f"Bearer {h_api_key}",
            "Accept": "application/vnd.heroku+json; version=3.account-quotas",
        }
        path = "/accounts/" + user_id + "/actions/get-quota"
        session = requests.Session()
        result = (session.get(heroku_api + path, headers=headers)).json()
        abc = ""
        account_quota = result["account_quota"]
        quota_used = result["quota_used"]
        quota_remain = account_quota - quota_used
        if EMOJI_THEME is True:
            abc += f'<b></b>\n'
            abc += f'<b>╭─《🌐 HEROKU STATS 🌐》</b>\n'
            abc += f"<b>├ 💪🏻 FULL</b>: {get_readable_time(account_quota)}\n"
            abc += f"<b>├ 👎🏻 USED</b>: {get_readable_time(quota_used)}\n"
            abc += f"<b>├ 👍🏻 FREE</b>: {get_readable_time(quota_remain)}\n"
        else:
            abc += f'<b></b>\n'
            abc += f'<b>╭─《 HEROKU STATS 》</b>\n'
            abc += f"<b>├ FULL</b>: {get_readable_time(account_quota)}\n"
            abc += f"<b>├ USED</b>: {get_readable_time(quota_used)}\n"
            abc += f"<b>├ FREE</b>: {get_readable_time(quota_remain)}\n"
        # App Quota
        AppQuotaUsed = 0
        OtherAppsUsage = 0
        for apps in result["apps"]:
            if str(apps.get("app_uuid")) == str(app.id):
                try:
                    AppQuotaUsed = apps.get("quota_used")
                except Exception as t:
                    LOGGER.error("error when adding main dyno")
                    LOGGER.error(t)
                    pass
            else:
                try:
                    OtherAppsUsage += int(apps.get("quota_used"))
                except Exception as t:
                    LOGGER.error("error when adding other dyno")
                    LOGGER.error(t)
                    pass
        LOGGER.info(f"This App: {str(app.name)}")
        if EMOJI_THEME is True:
            abc += f"<b>├ 🎃 APP USAGE:</b> {get_readable_time(AppQuotaUsed)}\n"
            abc += f"<b>├ 🗑️ OTHER APP:</b> {get_readable_time(OtherAppsUsage)}\n"
            abc += f'<b>╰─《 ☣️ {CREDIT_NAME} ☣️ 》</b>'
        else:
            abc += f"<b>├ APP USAGE:</b> {get_readable_time(AppQuotaUsed)}\n"
            abc += f"<b>├ OTHER APP:</b> {get_readable_time(OtherAppsUsage)}\n"
            abc += f'<b>╰─《 {CREDIT_NAME} 》</b>'
        return abc
    except Exception as g:
        LOGGER.error(g)
        return None


def progress_bar(percentage):
    p_used = FINISHED_PROGRESS_STR
    p_total = UN_FINISHED_PROGRESS_STR
    if isinstance(percentage, str):
        return 'NaN'
    try:
        percentage=int(percentage)
    except:
        percentage = 0
    return ''.join(
        p_used if i <= percentage // 10 else p_total for i in range(1, 11)
    )

now=datetime.now(pytz.timezone(f'{TIMEZONE}'))

def stats(update, context):
    if ospath.exists('.git'):
        if EMOJI_THEME is True:
            last_commit = check_output(["git log -1 --date=short --pretty=format:'%cd \n<b>├</b> 🛠<b>From</b> %cr'"], shell=True).decode()
            botVersion = check_output(["git log -1 --date=format:v%y.%m%d.%H%M --pretty=format:%cd"], shell=True).decode()
        else:
            last_commit = check_output(["git log -1 --date=short --pretty=format:'%cd \n<b>├</b> <b>From</b> %cr'"], shell=True).decode()
            botVersion = check_output(["git log -1 --date=format:v%y.%m%d.%H%M --pretty=format:%cd"], shell=True).decode()
    else:
        botVersion = 'No UPSTREAM_REPO'
        last_commit = 'No UPSTREAM_REPO'
    currentTime = get_readable_time(time() - botStartTime)
    current = now.strftime('%m/%d %I:%M:%S %p')
    osUptime = get_readable_time(time() - boot_time())
    total, used, free, disk= disk_usage('/')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(net_io_counters().bytes_sent)
    recv = get_readable_file_size(net_io_counters().bytes_recv)
    cpuUsage = cpu_percent(interval=0.5)
    p_core = cpu_count(logical=False)
    t_core = cpu_count(logical=True)
    swap = swap_memory()
    swap_p = swap.percent
    swap_t = get_readable_file_size(swap.total)
    swap_u = get_readable_file_size(swap.used)
    memory = virtual_memory()
    mem_p = memory.percent
    mem_t = get_readable_file_size(memory.total)
    mem_a = get_readable_file_size(memory.available)
    mem_u = get_readable_file_size(memory.used)
    if EMOJI_THEME is True:
            stats = f'<b>╭─《🌐 BOT STATISTICS 🌐》</b>\n' \
                    f'<b>├ 🛠 Updated On: </b>{last_commit}\n'\
                    f'<b>├ ⌛ Uptime: </b>{currentTime}\n'\
                    f'<b>├ 🟢 OS Uptime: </b>{osUptime}\n'\
                    f'<b>├ 🖥️ CPU:</b> [{progress_bar(cpuUsage)}] {cpuUsage}%\n'\
                    f'<b>├ 🎮 RAM:</b> [{progress_bar(mem_p)}] {mem_p}%\n'\
                    f'<b>├ 💾 Disk:</b> [{progress_bar(disk)}] {disk}%\n'\
                    f'<b>├ 💿 Disk Free:</b> {free}\n'\
                    f'<b>├ 🔺 Upload Data:</b> {sent}\n'\
                    f'<b>╰ 🔻 Download Data:</b> {recv}\n\n'

    else:
            stats = f'<b>╭─《 BOT STATISTICS 》</b>\n' \
                    f'<b>├  Updated On: </b>{last_commit}\n'\
                    f'<b>├  Uptime: </b>{currentTime}\n'\
                    f'<b>├  OS Uptime: </b>{osUptime}\n'\
                    f'<b>├  CPU usage:</b> [{progress_bar(cpuUsage)}] {cpuUsage}%\n'\
                    f'<b>├  RAM:</b> [{progress_bar(mem_p)}] {mem_p}%\n'\
                    f'<b>├  Disk:</b> [{progress_bar(disk)}] {disk}%\n'\
                    f'<b>├  Disk Free:</b> {free}\n'\
                    f'<b>├  Upload Data:</b> {sent}\n'\
                    f'<b>╰  Download Data:</b> {recv}\n\n'



    if SHOW_LIMITS_IN_STATS is True:
        if TORRENT_DIRECT_LIMIT is None:
            torrent_direct = 'No Limit Set'
        else:
            torrent_direct = f'{TORRENT_DIRECT_LIMIT}GB/Link'
        if CLONE_LIMIT is None:
            clone_limit = 'No Limit Set'
        else:
            clone_limit = f'{CLONE_LIMIT}GB/Link'
        if MEGA_LIMIT is None:
            mega_limit = 'No Limit Set'
        else:
            mega_limit = f'{MEGA_LIMIT}GB/Link'
        if LEECH_LIMIT is None:
            leech_limit = 'No Limit Set'
        else:
            leech_limit = f'{LEECH_LIMIT}GB/Link'
        if ZIP_UNZIP_LIMIT is None:
            zip_unzip = 'No Limit Set'
        else:
            zip_unzip = f'{ZIP_UNZIP_LIMIT}GB/Link'
        if TOTAL_TASKS_LIMIT is None:
            total_task = 'No Limit Set'
        else:
            total_task = f'{TOTAL_TASKS_LIMIT} Total Tasks/Time'
        if USER_TASKS_LIMIT is None:
            user_task = 'No Limit Set'
        else:
            user_task = f'{USER_TASKS_LIMIT} Tasks/user'


        if EMOJI_THEME is True: 
            stats += f'<b>╭─《 ⚠️ BOT LIMITS ⚠️ 》</b>\n'\
                     f'<b>├ 🧲 Torrent/Direct: </b>{torrent_direct}\n'\
                     f'<b>├ 🔐 Zip/Unzip: </b>{zip_unzip}\n'\
                     f'<b>├ 🔷 Leech: </b>{leech_limit}\n'\
                     f'<b>├ ♻️ Clone: </b>{clone_limit}\n'\
                     f'<b>├ 🔰 Mega: </b>{mega_limit}\n'\
                     f'<b>├ 💣 Total Tasks: </b>{total_task}\n'\
                     f'<b>╰ 🔫 User Tasks: </b>{user_task}\n\n'
        else: 
            stats += f'<b>╭─《  BOT LIMITS  》</b>\n'\
                     f'<b>├  Torrent/Direct: </b>{torrent_direct}\n'\
                     f'<b>├  Zip/Unzip: </b>{zip_unzip}\n'\
                     f'<b>├  Leech: </b>{leech_limit}\n'\
                     f'<b>├  Clone: </b>{clone_limit}\n'\
                     f'<b>├  Mega: </b>{mega_limit}\n'\
                     f'<b>├  Total Tasks: </b>{total_task}\n'\
                     f'<b>╰  User Tasks: </b>{user_task}\n\n'

                

    heroku = getHerokuDetails(HEROKU_API_KEY, HEROKU_APP_NAME)
    if heroku: stats += heroku 
    if PICS:
        sendPhoto(stats, context.bot, update.message, random.choice(PICS))
    else:
        sendMessage(stats, context.bot, update.message)

def start(update, context):
    if CustomFilters.authorized_user(update) or CustomFilters.authorized_chat(update):
        start_string = f'''<b>My Name is Millie Bobby Brown! An Advanced Mirror Bot to Leech Torrent and Direct Links...
Tap /{BotCommands.HelpCommand} to get a list of available commands

© Spidey | Mindflayer's Mirror</b>
'''
        if PICS:
            sendPhoto(start_string, context.bot, update.message, random.choice(PICS))
        else:
            sendMessage(start_string, context.bot, update.message)
    else:
        text = f"You're Not Authorized user!"
        if PICS:
            sendPhoto(text, context.bot, update.message, random.choice(PICS))
        else:
            sendMessage(text, context.bot, update.message)

def restart(update, context):
    cmd = update.effective_message.text.split(' ', 1)
    dynoRestart = False
    dynoKill = False
    if len(cmd) == 2:
        dynoRestart = (cmd[1].lower()).startswith('d')
        dynoKill = (cmd[1].lower()).startswith('k')
    if (not HEROKU_API_KEY) or (not HEROKU_APP_NAME):
        LOGGER.info("If you want Heroku features, fill HEROKU_APP_NAME HEROKU_API_KEY vars.")
        dynoRestart = False
        dynoKill = False
    if dynoRestart:
        LOGGER.info("Dyno Restarting.")
        restart_message = sendMessage("Dyno Restarting.", context.bot, update.message)
        with open(".restartmsg", "w") as f:
            f.truncate(0)
            f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
        heroku_conn = heroku3.from_key(HEROKU_API_KEY)
        app = heroku_conn.app(HEROKU_APP_NAME)
        app.restart()
    elif dynoKill:
        LOGGER.info("Killing Dyno. MUHAHAHA")
        sendMessage("Killed Dyno.", context.bot, update.message)
        alive.kill()
        clean_all()
        heroku_conn = heroku3.from_key(HEROKU_API_KEY)
        app = heroku_conn.app(HEROKU_APP_NAME)
        proclist = app.process_formation()
        for po in proclist:
            app.process_formation()[po.type].scale(0)
    else:
        LOGGER.info("Normally Restarting.")
        restart_message = sendMessage("Normally Restarting.", context.bot, update.message)
        if Interval:
            Interval[0].cancel()
            Interval.clear()
        alive.kill()
        clean_all()
        srun(["pkill", "-9", "-f", "gunicorn|chrome|firefox|megasdkrest|opera"])
        srun(["python3", "update.py"])
        with open(".restartmsg", "w") as f:
            f.truncate(0)
            f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
        osexecl(executable, executable, "-m", "bot")



def ping(update, context):
    if EMOJI_THEME is True:
        start_time = int(round(time() * 1000))
        reply = sendMessage("Starting_Ping ⛔", context.bot, update.message)
        end_time = int(round(time() * 1000))
        editMessage(f'{end_time - start_time} ms 🔥', reply)
    else:
        start_time = int(round(time() * 1000))
        reply = sendMessage("Starting_Ping ", context.bot, update.message)
        end_time = int(round(time() * 1000))
        editMessage(f'{end_time - start_time} ms ', reply)


def log(update, context):
    sendLogFile(context.bot, update.message)


help_string = '''
<b>List of Commands :-</b>

<i>NOTE: After the Command Leave a single Space</i>

/mirror2: [url] Start mirroring to Google Drive.

<code>/mirror2 https://yoururl.com</code>

or (Reply with URL)

/qbmirror2: [magnet link] or Reply with Torrent - Start Mirroring to Google Drive using qBittorrent.

<code>/qbmirror2 magnet:?xt=urn:btih:f2cd08296a3...</code>

or (Reply with Torrent)

/clone2 [drive_url]: Copy Others file/folder to Google Drive.

<code>/clone2 https://drive.google.com/file/d/1e-fy8zXyz</code>'''

def bot_help(update, context):
    sendMessage(help_string, context.bot, update.message)

       


if SET_BOT_COMMANDS:
    botcmds = [
        (f'{BotCommands.MirrorCommand}', 'Mirror'),
        (f'{BotCommands.ZipMirrorCommand}','Mirror and upload as zip'),
        (f'{BotCommands.UnzipMirrorCommand}','Mirror and extract files'),
        (f'{BotCommands.QbMirrorCommand}','Mirror torrent using qBittorrent'),
        (f'{BotCommands.QbZipMirrorCommand}','Mirror torrent and upload as zip using qb'),
        (f'{BotCommands.QbUnzipMirrorCommand}','Mirror torrent and extract files using qb'),
        (f'{BotCommands.WatchCommand}','Mirror yt-dlp supported link'),
        (f'{BotCommands.ZipWatchCommand}','Mirror yt-dlp supported link as zip'),
        (f'{BotCommands.CloneCommand}','Copy file/folder to Drive'),
        (f'{BotCommands.LeechCommand}','Leech'),
        (f'{BotCommands.ZipLeechCommand}','Leech and upload as zip'),
        (f'{BotCommands.UnzipLeechCommand}','Leech and extract files'),
        (f'{BotCommands.QbLeechCommand}','Leech torrent using qBittorrent'),
        (f'{BotCommands.QbZipLeechCommand}','Leech torrent and upload as zip using qb'),
        (f'{BotCommands.QbUnzipLeechCommand}','Leech torrent and extract using qb'),
        (f'{BotCommands.LeechWatchCommand}','Leech yt-dlp supported link'),
        (f'{BotCommands.LeechZipWatchCommand}','Leech yt-dlp supported link as zip'),
        (f'{BotCommands.CountCommand}','Count file/folder of Drive'),
        (f'{BotCommands.DeleteCommand}','Delete file/folder from Drive'),
        (f'{BotCommands.CancelMirror}','Cancel a task'),
        (f'{BotCommands.CancelAllCommand}','Cancel all downloading tasks'),
        (f'{BotCommands.ListCommand}','Search in Drive'),
        (f'{BotCommands.SearchCommand}','Search in Torrent'),
        (f'{BotCommands.LeechSetCommand}','Leech settings'),
        (f'{BotCommands.SetThumbCommand}','Set thumbnail'),
        (f'{BotCommands.StatusCommand}','Get mirror status message'),
        (f'{BotCommands.StatsCommand}','Bot usage stats'),
        (f'{BotCommands.UsageCommand}','Heroku Dyno usage'),
        (f'{BotCommands.SpeedCommand}','Speedtest'),
        (f'{BotCommands.WayBackCommand}','Internet Archive'),
        (f'{BotCommands.MediaInfoCommand}','Get Information of telegram Files'),
        (f'{BotCommands.HashCommand}','Get Hash of telegram Files'),
        (f'{BotCommands.PingCommand}','Ping the bot'),
        (f'{BotCommands.RestartCommand}','Restart the bot'),
        (f'{BotCommands.LogCommand}','Get the bot Log'),
        (f'{BotCommands.HelpCommand}','Get detailed help'),
        (f'{BotCommands.AuthorizedUsersCommand}','Authorized Users/Chats'),
        (f'{BotCommands.AuthorizeCommand}','Authorize user/chat'),
        (f'{BotCommands.UnAuthorizeCommand}','UnAuthorize user/chat'),
        (f'{BotCommands.AddSudoCommand}','Add Sudo'),
        (f'{BotCommands.RmSudoCommand}','Remove Sudo'),
        (f'{BotCommands.AddleechlogCommand}','Add Leech Log Channel'),
        (f'{BotCommands.RmleechlogCommand}','Remove Leech Log Channel'),
        (f'{BotCommands.SleepCommand}','Sleep Bot')
    ]


def main():
    if SET_BOT_COMMANDS:
        bot.set_my_commands(botcmds)
    start_cleanup()
    date = now.strftime('%d/%m/%y')
    time = now.strftime('%I:%M:%S %p')
    notifier_dict = False
    if INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
        if notifier_dict := DbManger().get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                if ospath.isfile(".restartmsg"):
                    with open(".restartmsg") as f:
                        chat_id, msg_id = map(int, f)
                    msg = f"😎Restarted successfully❗\n"
                    msg += f" DATE: {date}\n"
                    msg += f" TIME: {time}\n"
                    msg += f" TIMEZONE: {TIMEZONE}\n"
                else:
                    msg = f"Bot Restarted!\n"
                    msg += f"DATE: {date}\n"
                    msg += f"TIME: {time}\n"
                    msg += f"TIMEZONE: {TIMEZONE}"

                for tag, links in data.items():
                     msg += f"\n{tag}: "
                     for index, link in enumerate(links, start=1):
                         msg += f" <a href='{link}'>{index}</a> |"
                         if len(msg.encode()) > 4000:
                             if '😎Restarted successfully❗' in msg and cid == chat_id:
                                 bot.editMessageText(msg, chat_id, msg_id, parse_mode='HTML', disable_web_page_preview=True)
                                 osremove(".restartmsg")
                             else:
                                 try:
                                     bot.sendMessage(cid, msg, 'HTML', disable_web_page_preview=True)
                                 except Exception as e:
                                     LOGGER.error(e)
                             msg = ''
                if '😎Restarted successfully❗' in msg and cid == chat_id:
                     bot.editMessageText(msg, chat_id, msg_id, parse_mode='HTML', disable_web_page_preview=True)
                     osremove(".restartmsg")
                else:
                    try:
                        bot.sendMessage(cid, msg, 'HTML', disable_web_page_preview=True)
                    except Exception as e:
                        LOGGER.error(e)

    if ospath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        msg = f"😎Restarted successfully❗\n DATE: {date}\n TIME: {time}\n TIMEZONE: {TIMEZONE}\n"
        bot.edit_message_text(msg, chat_id, msg_id)
        osremove(".restartmsg")
    elif not notifier_dict and AUTHORIZED_CHATS:
        text = f" Bot Restarted! \nDATE: {date} \nTIME: {time} \nTIMEZONE: {TIMEZONE}"
        for id_ in AUTHORIZED_CHATS:
            try:
                bot.sendMessage(chat_id=id_, text=text, parse_mode=ParseMode.HTML)
            except Exception as e:
                LOGGER.error(e)


    start_handler = CommandHandler(BotCommands.StartCommand, start, run_async=True)
    ping_handler = CommandHandler(BotCommands.PingCommand, ping,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    restart_handler = CommandHandler(BotCommands.RestartCommand, restart,
                                     filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    help_handler = CommandHandler(BotCommands.HelpCommand,
                                      bot_help, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    stats_handler = CommandHandler(BotCommands.StatsCommand,
                                   stats, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    log_handler = CommandHandler(BotCommands.LogCommand, log, filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(ping_handler)
    dispatcher.add_handler(restart_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(log_handler)
    updater.start_polling(drop_pending_updates=IGNORE_PENDING_REQUESTS)
    LOGGER.info("💥𝐁𝐨𝐭 𝐒𝐭𝐚𝐫𝐭𝐞𝐝❗")
    signal(SIGINT, exit_clean_up)

app.start()
main()

main_loop.run_forever()
