# ORIGINAL CREATOR: Luca Garofalo (Lucksi)
# AUTHOR: Luca Garofalo (Lucksi)
# Copyright (C) 2021-2024 Lucksi <lukege287@gmail.com>
# License: GNU General Public License v3.0

import os
import warnings
import urllib
import json
from Core.Support import Font
from Core.Support import Creds
from Core.Support import FileTransfer
from Core.Support import Proxies
from Core.proxy.manager import ProxyManager
from Core.Support import Requests_Search
from Core.Support.Username import Scraper
from Core.Support import Clear
from Core.Support import Dorks
from Core.Support import Logs
from Core.Support import Banner_Selector as banner
from Core.Support import Language
from Core.Support import Notification
from Core.Support import Recap
from Core.Support import DateFormat
from datetime import datetime
from Core.Support import Encoding
from Core.Support import Site_Counter as CO
from time import sleep
from Core.config.logging_config import get_logger

warnings.warn(
    "Core.Searcher is deprecated. Use Core.engine.ScanPipeline, "
    "Core.engine.DorkGenerator, and Core.engine.ProfileScraper instead.",
    DeprecationWarning,
    stacklevel=2,
)

filename = Language.Translation.Get_Language()
filename

_logger = get_logger(__name__)

class MrHolmes:

    @staticmethod
    def Scraping(report, username, http_proxy,InstagramParams,PostLocations, PostGpsCoordinates,TwitterParams):
        """Thin wrapper — ủy quyền cho ProfileScraper.scrape_all()."""
        from Core.engine.profile_scraper import ProfileScraper
        ProfileScraper.scrape_all(
            report=report,
            username=username,
            http_proxy=http_proxy,
            instagram_params=InstagramParams,
            post_locations=PostLocations,
            post_gps_coordinates=PostGpsCoordinates,
            twitter_params=TwitterParams,
        )
        
    
    @staticmethod
    def Controll(username, nomefile, identity, report, subject, successfull, ScraperSites, Writable, http_proxy2, successfullName, http_proxy, choice, Tags, MostTags):
        with open(nomefile) as f:
            data = json.loads(f.read())

        print(Font.Color.GREEN + "\n[+]" + Font.Color.WHITE +
              Language.Translation.Translate_Language(filename, "Default", "Proxy", "None").format(http_proxy2))
        if identity != "None":
            print(Font.Color.GREEN + "[+]" + Font.Color.WHITE + identity)
        json_file = "GUI/Reports/Usernames/{}/{}.json".format(username, username)
        json_file2 = "GUI/Reports/Usernames/{}/{}.json".format(username, "Name")

        for sites in data:
            for data1 in sites:

                site1 = sites[data1]["user"].replace("{}", username)
                site2 = sites[data1]["user2"].replace("{}", username)
                name = sites[data1]["name"]
                main = sites[data1]["main"]
                error = sites[data1]["Error"]
                exception_char = sites[data1]["exception"]
                is_scrapable = sites[data1]["Scrapable"]
                Tag = sites[data1]["Tag"]
                print(Font.Color.GREEN +
                      "\n[+]" + Font.Color.WHITE + Language.Translation.Translate_Language(filename, "Default", "Attempt", "None") .format(name))
                for errors in exception_char:
                    if errors in username:
                        alert = "NOT-CORRECT"
                        break
                    else:
                        alert = "CORRECT"
                if alert == "NOT-CORRECT":
                    print(
                        Font.Color.YELLOW2 + "[U]" + Font.Color.WHITE + Language.Translation.Translate_Language(filename, "Username", "Default", "Not_Valid"))
                else:
                    try:
                        Requests_Search.Search.search(error, report, site1, site2, http_proxy, sites, data1, username,
                                                      subject, successfull, name, successfullName, is_scrapable, ScraperSites, Writable, main, json_file, json_file2, Tag, Tags, MostTags)
                    except Exception as e:
                        _logger.warning(Language.Translation.Translate_Language(filename, "Default", "Connection_Error1", "None"))
                        http_proxy = None
                        try:
                            Requests_Search.Search.search(error, report, site1, site2, http_proxy, sites, data1, username,
                                                          subject, successfull, name, successfullName, is_scrapable, ScraperSites, Writable, main, json_file, json_file2, Tag, Tags, MostTags)
                        except Exception as e:
                            _logger.warning(Language.Translation.Translate_Language(filename, "Default", "Site_Error", "None"))
                if choice == 1:
                    _pm = ProxyManager()
                    _pm.configure(1)
                    http_proxy = _pm.get_proxy()
                    http_proxy2 = _pm.proxy_ip
                    identity = _pm.get_identity() or "None"

                else:
                    http_proxy = None
                    http_proxy2 = str(http_proxy)
                    identity = "None"

    @staticmethod
    def Banner(Mode):
        Clear.Screen.Clear()
        Folder = "Banners/Username"
        banner.Random.Get_Banner(Folder, Mode)

    @staticmethod
    def Google_dork(username):
        """Thin wrapper — ủy quyền cho DorkGenerator.google_dorks()."""
        from Core.engine.dork_generator import DorkGenerator
        DorkGenerator.google_dorks(username)

    @staticmethod
    def Yandex_dork(username):
        """Thin wrapper — ủy quyền cho DorkGenerator.yandex_dorks()."""
        from Core.engine.dork_generator import DorkGenerator
        DorkGenerator.yandex_dorks(username)

    @staticmethod
    def search(username, Mode):
        """
        Thin wrapper — ủy quyền toàn bộ scan logic cho ScanPipeline.

        Original: ~500 LOC God Method (lines 196-690).
        Refactored: Story 1.3 — ScanPipeline decomposition.
        """
        from Core.engine.scan_pipeline import ScanPipeline
        pipeline = ScanPipeline(username, Mode)
        pipeline.run()

