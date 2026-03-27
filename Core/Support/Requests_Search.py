# ORIGINAL CREATOR: Luca Garofalo (Lucksi)
# AUTHOR: Luca Garofalo (Lucksi)
# Copyright (C) 2021-2023 Lucksi <lukege287@gmail.com>
# License: GNU General Public License v3.0
# Refactored: Story 1.2 — Extract duplicated tag processing logic

import requests
import json
from Core.Support import Font
from Core.Support import Language
from Core.Support import Headers

filename = Language.Translation.Get_Language()

# Tags xuất hiện trong category đặc biệt — luôn được thêm vào MostTags
UNIQUE_TAGS = [
    "Chess", "Books", "Pokemon", "Lol/League of Legends", "Minecraft",
    "Roblox", "Modelling", "Anime", "Shopping", "Writing", "Stories",
    "OSU", "ThemeForest", "Meme", "Python", "Ruby", "Npm", "Health",
    "Map", "File-Sharing", "Colors", "Crypto", "Speedrun", "Steam",
    "BitCoin", "Playstation", "Gallery", "Chess.com", "Badge",
]


class Search:

    @staticmethod
    def _process_tags(tag_list, subject, all_tags, most_tags):
        """
        Xử lý tag accumulation logic — extract từ 3 duplicated blocks.

        Business logic:
          - Tags thuộc UNIQUE_TAGS → luôn thêm vào most_tags
          - Tags đã có trong all_tags nhưng chưa trong most_tags → thêm most_tags
          - Tags chưa có trong all_tags → thêm all_tags (first occurrence)
          - Nếu subject == "PHONE-NUMBER" → bỏ qua toàn bộ (phone scan không dùng tags)

        Args:
            tag_list:  list[str] — tags của site hiện tại
            subject:   str — subject type ("USERNAME", "PHONE-NUMBER", etc.)
            all_tags:  list[str] — accumulated unique tags (mutated in-place)
            most_tags: list[str] — accumulated most-seen/unique interest tags (mutated in-place)
        """
        if subject == "PHONE-NUMBER":
            return

        for tag in tag_list:
            if tag in UNIQUE_TAGS:
                most_tags.append(tag)
            if tag in all_tags:
                if tag not in most_tags:
                    most_tags.append(tag)
            else:
                all_tags.append(tag)

    @staticmethod
    def _handle_found_result(
        site1, name, main, tag, subject,
        writable, f,
        successfull, successfullName, is_scrapable, ScraperSites,
        Tags, MostTags,
    ):
        """
        Xử lý khi một site được tìm thấy — extract từ 3 duplicated blocks.

        Gom lại: print kết quả + ghi file + xử lý tags + append tracking lists.

        Args:
            site1:           str — display URL (ghi vào report)
            name:            str — tên site
            main:            str — main identifier (phone/email format)
            tag:             list[str] — tags của site này
            subject:         str — subject type
            writable:        bool — True: ghi URL, False: ghi name:main
            f:               file object — report file handle
            successfull:     list — accumulates found URLs (mutated)
            successfullName: list — accumulates found site names (mutated)
            is_scrapable:    str — "True"/"False" string từ site JSON
            ScraperSites:    list — accumulates scrapable site names (mutated)
            Tags:            list — all unique tags seen (mutated)
            MostTags:        list — most-seen/unique-interest tags (mutated)
        """
        print(Font.Color.YELLOW + "[v]" + Font.Color.WHITE +
              Language.Translation.Translate_Language(
                  filename, "Default", "Found", "None"
              ).format(subject, name if writable else main))
        print(Font.Color.YELLOW + "[v]" + Font.Color.WHITE +
              "LINK: {}".format(site1))

        if writable:
            f.write(site1 + "\r\n")
            print(Font.Color.BLUE + "[I]" + Font.Color.WHITE +
                  "TAGS:[{}]".format(Font.Color.GREEN + ",".join(tag) + Font.Color.WHITE))
            Search._process_tags(tag, subject, Tags, MostTags)
        else:
            f.write("{}:{}\r\n".format(name, main))

        successfull.append(site1)
        successfullName.append(name)
        if is_scrapable == "True":
            ScraperSites.append(name)

    @staticmethod
    def search(error, report, site1, site2, http_proxy, sites, data1, username,
               subject, successfull, name, successfullName, is_scrapable,
               ScraperSites, Writable, main, json_file, json_file2, Tag, Tags, MostTags):
        """
        Tìm kiếm username/subject trên 1 site và ghi kết quả vào report.

        Note: Signature giữ nguyên cho backward compatibility (Story 1.1 integration = Story 1.3).
        """
        headers = Headers.Get.classic()
        if name == "Twitter":
            headers = Headers.Get.Twitter()

        searcher = requests.get(
            url=site2, headers=headers, proxies=http_proxy, timeout=10, allow_redirects=True)

        with open(report, "a") as f:
            if error == "Status-Code":
                if searcher.status_code == 200:
                    Search._handle_found_result(
                        site1, name, main, Tag, subject, Writable, f,
                        successfull, successfullName, is_scrapable, ScraperSites,
                        Tags, MostTags,
                    )
                elif searcher.status_code == 404 or searcher.status_code == 204:
                    print(Font.Color.RED + "[!]" + Font.Color.WHITE +
                          Language.Translation.Translate_Language(
                              filename, "Default", "NotFound", "None"
                          ).format(subject, username))
                else:
                    print(Font.Color.BLUE + "[N]" + Font.Color.WHITE +
                          Language.Translation.Translate_Language(
                              filename, "Default", "Connection_Error2", "None"
                          ) + str(searcher.status_code))

            elif error == "Message":
                text = sites[data1]["text"]
                if text in searcher.text:
                    print(Font.Color.RED + "[!]" + Font.Color.WHITE +
                          Language.Translation.Translate_Language(
                              filename, "Default", "NotFound", "None"
                          ).format(subject, username))
                else:
                    Search._handle_found_result(
                        site1, name, main, Tag, subject, Writable, f,
                        successfull, successfullName, is_scrapable, ScraperSites,
                        Tags, MostTags,
                    )

            elif error == "Response-Url":
                response = sites[data1]["response"]
                if searcher.url == response:
                    print(Font.Color.RED + "[!]" + Font.Color.WHITE +
                          Language.Translation.Translate_Language(
                              filename, "Default", "NotFound", "None"
                          ).format(subject, username))
                else:
                    Search._handle_found_result(
                        site1, name, main, Tag, subject, Writable, f,
                        successfull, successfullName, is_scrapable, ScraperSites,
                        Tags, MostTags,
                    )

        # Write JSON output files
        with open(json_file2, "w") as d:
            d.write('{\n    "Names":[\n\n    ]\n}')

        with open(json_file, "w") as f:
            f.write('{\n    "List":[\n\n    ]\n}')

        for element in successfullName:
            data = {"name": "{}".format(element)}
            with open(json_file2, 'r+') as file2:
                file_data2 = json.load(file2)
                file_data2["Names"].append(data)
                file2.seek(0)
                json.dump(file_data2, file2, indent=4)

        for element in successfull:
            data = {"site": "{}".format(element)}
            with open(json_file, 'r+') as file:
                file_data = json.load(file)
                file_data["List"].append(data)
                file.seek(0)
                json.dump(file_data, file, indent=4)
