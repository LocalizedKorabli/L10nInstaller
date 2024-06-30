# Korabli Localization Installer
# Copyright © 2024 MikhailTapio
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not,
# see <https://www.gnu.org/licenses/>.
import json
import os.path
import shutil
import subprocess
import sys
import time
import urllib.request
# pip install urllib3==1.25.11
# The newer urllib has break changes.
import webbrowser
import xml.etree.ElementTree as ETree
import zipfile
from pathlib import Path
from typing import List, Dict

import polib
import requests

version = "2024.06.30.1912"

base_path: str = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
resource_path: str = os.path.join(base_path, "resources")

available_launchers = [
    "lgc_api.exe",
    "wgc_api.exe",
    "wgc360_api.exe"
]

launcher_file = ""

splitter_str = "*" * 36

text_welcome_message = f'''战舰世界本地化安装器
作者：北斗余晖
版本：{version}
许可证：GNU-AGPL-3.0-only
源代码地址：https://github.com/LocalizedKorabli/L10nInstaller
'''

text_builtin_cfg = '''<locale_config>
    <locale_id>ru</locale_id>
    <text_path>../res/texts</text_path>
    <text_domain>global</text_domain>

    <lang_mapping>
        <lang acceptLang="ru" egs="ru" fonts="CN" full="russian" languageBar="true" localeRfcName="ru" short="ru" />
    </lang_mapping>
</locale_config>
'''

text_mo_source = '''汉化文件来源：
1.（实验性，默认）下载最新[正式服]汉化文件；
2.（实验性）下载最新[测试服]汉化文件；
3.使用本地文件。
'''

text_mo_source_selection = "请选择汉化文件来源："

download_servers = {
    "r": [
        {
            "name": "Gitee",
            "url": "https://gitee.com/localized-korabli/Korabli-LESTA-L10N/raw/main/Localizations/latest/global.mo",
            "wrapped": False,
            "delay": True
        },
        {
            "name": "湖北S3",
            "url": "https://maven.nova-committee.cn/s3/korabli/localized/l10n/1.0.0/l10n-1.0.0.jar",
            "wrapped": True,
            "delay": False
        },
        {
            "name": "香港",
            "url": "https://maven.nova-committee.cn/releases/korabli/localized/l10n/1.0.0/l10n-1.0.0.jar",
            "wrapped": True,
            "delay": False
        },
        {
            "name": "GitHub",
            "url": "https://github.com/LocalizedKorabli/Korabli-LESTA-L10N/raw/main/Localizations/latest/global.mo",
            "wrapped": False,
            "delay": False
        }
    ],
    "pt": [
        {
            "name": "Gitee",
            "url": "https://gitee.com/localized-korabli/Korabli-LESTA-L10N-PublicTest/raw/Localizations/Localizations"
                   "/latest/global.mo",
            "wrapped": False,
            "delay": True
        },
        {
            "name": "湖北S3",
            "url": "https://maven.nova-committee.cn/s3/korabli/localized/l10n/2.0.0/l10n-2.0.0.jar",
            "wrapped": True,
            "delay": False
        },
        {
            "name": "香港",
            "url": "https://maven.nova-committee.cn/releases/korabli/localized/l10n/2.0.0/l10n-2.0.0.jar",
            "wrapped": True,
            "delay": False
        },
        {
            "name": "GitHub",
            "url": "https://github.com/LocalizedKorabli/Korabli-LESTA-L10N-PublicTest/raw/Localizations/Localizations"
                   "/latest/global.mo",
            "wrapped": False,
            "delay": False
        }
    ]
}

text_download_server_selection = "请选择下载线路："

text_use_builtin = "是否使用程序自带备用文件？输入Y以同意。若上次安装后游戏字符仍被显示为空心方块，请考虑使用备用文件。"

text_apply_mods = "是否将l10n_installer/mods/下的模组应用到汉化文件？留空或输入Y，并按回车以应用："

text_general_installation_mode = '''全局安装模式
1.（默认）快速安装（LESTA正式服）
2.快速安装（LESTA测试服）
3.自定义安装
4.退出程序
'''

text_server_list = '''服务器列表：
1.LESTA服（俄服）
2.直营服（美/亚/欧服）
3.360服（国服）
'''

text_select_server = "请选择客户端所在的服务器："

text_mode_selection = "请选择安装模式："

text_mo_replace_mode = '''汉化文件安装模式：
1.安装到res_mods文件夹下（推荐：客户端非版本大更新时不会重置语言文件）；
2.安装到res文件夹下，备份并覆盖原文件；
3.不安装。
'''

text_locale_cfg_replace_mode = '''语言配置文件安装模式：
1.安装到res_mods文件夹下（推荐：客户端非版本大更新时不会重置语言配置文件）；
2.安装到res文件夹下，备份并覆盖原文件；
3.不安装。
'''

text_report_desc = '''请以“汉化安装器报错”为标题创建一个新Issue，内容应包含：
1.程序输出的异常信息；
2.异常发生时，汉化安装正进行到哪一步。
'''

server_dict: Dict[str, str] = {
    '1': 'ru',
    '2': 'zh_sg',
    '3': 'zh'
}


def run():
    print(text_welcome_message)
    debug = input("确保本程序已位于战舰世界客户端安装目录，按回车键继续。")
    if debug == "debug":
        print("进入DEBUG模式，将抛出异常。")
        raise RuntimeError("DEBUG")
    global launcher_file
    for launcher in available_launchers:
        if os.path.isfile(launcher):
            launcher_file = launcher
            print(f"已找到战舰世界启动器程序{launcher_file}。")
            break
    if launcher_file == "":
        confirm = input(
            "未找到战舰世界启动器程序，程序位置错误或战舰世界安装不完整？若仍要继续，请输入Y后按回车键。")
        if str(confirm).lower() != "y":
            return

    if not os.path.isdir("bin"):
        input("未找到战舰世界客户端bin文件夹，程序位置错误或战舰世界安装不完整？程序无法继续运行。")
        return

    folder = Path("bin")
    subdirectories: List[str] = [subdir.name for subdir in folder.iterdir() if subdir.is_dir()]

    first = "0"
    second = "0"
    for dir_name in subdirectories:
        try:
            i = int(dir_name)
            if i > int(first):
                second = first
                first = str(i)
        except ValueError:
            continue

    if first == "0":
        input("未找到战舰世界客户端bin文件夹下的版本号子文件夹，程序位置错误或战舰世界安装不完整？程序无法继续运行。")
        return

    second_dir_exists = second != "0"

    print(
        f"已找到安装目录下最新的两个版本号子文件夹：{first}、{second}" if second_dir_exists else f"已找到安装目录下最新的版本号子文件夹：{first}")

    global_mo_path = _fetch_l10n_mo()

    while not os.path.isfile(global_mo_path):
        print("mo文件读取失败，请重新选择mo来源。")
        global_mo_path = _fetch_l10n_mo()

    apply_mods = input(text_apply_mods)
    if apply_mods == '' or apply_mods.lower() == "y":
        mods = _check_mods()
        if mods:
            source_mo = polib.mofile(global_mo_path)
            print(f"找到{len(mods)}个po/mo模组")
            for path in mods:
                print(f"应用{path}到{global_mo_path}……")
                try:
                    _process_modification_file(source_mo, path)
                except Exception as ex:
                    print(f"应用模组“{path}”时发生异常！异常信息：{ex}")
            print("修改完成，正在保存……")
            modified_mo_path = f"l10n_installer/processed/modified_{time.time_ns()}.mo"
            source_mo.save(modified_mo_path)
            print(f"修改后的本地化文件已保存到{modified_mo_path}。")
            global_mo_path = modified_mo_path
            print(f"mo来源变更为{modified_mo_path}。")
        else:
            print("未在l10n_installer/mods找到有效的po/mo本地化模组，使用原文件。")
    else:
        print("跳过模组应用，使用原文件。")

    installation_locale = None
    installation_cfg = None
    server = None
    use_builtin_cfg = None

    print(text_general_installation_mode)
    try:
        selected = input(text_mode_selection)
        if selected == '':
            mode = 1
        else:
            mode = int(selected)
    except ValueError:
        print("输入错误，默认为自定义安装")
        mode = 3
    if mode == 4:
        return
    if mode == 1:
        installation_locale = 1
        installation_cfg = 1
        server = "ru"
        use_builtin_cfg = True
    elif mode == 2:
        installation_locale = 2
        installation_cfg = 2
        server = "ru"
        use_builtin_cfg = True
    if not server:
        print(text_server_list)
        try:
            server = server_dict.get(input(text_select_server))
        except ValueError:
            server = server_dict.get('1')
            print("输入错误，默认为LESTA服")

    if not installation_locale:
        print(text_mo_replace_mode)
        try:
            installation_locale = int(input(text_mode_selection))
        except ValueError:
            installation_locale = 3

    logo_path_1 = Path("bin").joinpath(first).joinpath("res_mods").joinpath("gui").joinpath("game_loading")
    os.makedirs(logo_path_1, exist_ok=True)
    shutil.copy(os.path.join(resource_path, "game_logo.svg"), logo_path_1.joinpath("game_logo.svg"))
    shutil.copy(os.path.join(resource_path, "game_logo_static.svg"), logo_path_1.joinpath("game_logo_static.svg"))
    if second_dir_exists:
        logo_path_2 = Path("bin").joinpath(second).joinpath("res_mods").joinpath("gui").joinpath("game_loading")
        os.makedirs(logo_path_2, exist_ok=True)
        shutil.copy(os.path.join(resource_path, "game_logo.svg"), logo_path_2.joinpath("game_logo.svg"))
        shutil.copy(os.path.join(resource_path, "game_logo_static.svg"), logo_path_2.joinpath("game_logo_static.svg"))

    if installation_locale == 1:
        shutil.copy(global_mo_path, _get_res_mods_mo_path(first, server))
        if second_dir_exists:
            shutil.copy(global_mo_path, _get_res_mods_mo_path(second, server))
        if not installation_cfg:
            input("汉化文件安装完成，请不要退出程序，按回车键继续。")
    elif installation_locale == 2:
        first_mo_dir_found = os.path.isdir(_get_mo_dir_path(first, server))
        first_mo_path = _get_mo_path(first, server)
        first_mo_found = os.path.isfile(first_mo_path)
        if not first_mo_dir_found or not first_mo_found:
            print(f"未在{first}版本文件夹下找到global.mo文件")
        else:
            shutil.copy(first_mo_path, str(first_mo_path) + ".old")
        if first_mo_dir_found:
            shutil.copy(global_mo_path, first_mo_path)

        if second_dir_exists:
            second_mo_dir_found = os.path.isdir(_get_mo_dir_path(second, server))
            second_mo_path = _get_mo_path(second, server)
            second_mo_found = os.path.isfile(second_mo_path)
            if not second_mo_dir_found or not second_mo_found:
                print(f"未在{second}版本文件夹下找到global.mo文件")
            else:
                shutil.copy(second_mo_path, str(second_mo_path) + ".old")
            if second_mo_dir_found:
                shutil.copy(global_mo_path, second_mo_path)
        if not installation_cfg:
            input("汉化文件安装完成，请不要退出程序，按回车键继续。")
    else:
        input("已跳过汉化文件安装，按回车键继续。")

    needs_cfg = server == "ru"

    if not installation_cfg:
        if not needs_cfg:
            installation_cfg = 0
        else:
            print(text_locale_cfg_replace_mode)
            try:
                installation_cfg = int(input(text_mode_selection))
            except ValueError:
                installation_cfg = 0

    if needs_cfg and not use_builtin_cfg:
        use_builtin_cfg = input(text_use_builtin).lower() == "y"

    if needs_cfg and installation_cfg != 0:
        first_cfg_path = _get_locale_cfg_path(first)
        second_cfg_path = _get_locale_cfg_path(second)
        first_cfg_exists = os.path.isdir(_get_res_path(first)) and os.path.isfile(first_cfg_path)
        second_cfg_exists = os.path.isdir(_get_res_path(second)) and os.path.isfile(second_cfg_path)
        if not use_builtin_cfg and not first_cfg_exists and not second_cfg_exists:
            print("未在指定的文件夹下找到locale_config.xml文件，将使用程序自带的备用文件。")
            use_builtin_cfg = True
        if installation_cfg == 2:
            if not use_builtin_cfg:
                if not first_cfg_exists or not _modify_cfg(first_cfg_path, first_cfg_path, True):
                    use_builtin_cfg = True
                if second_dir_exists:
                    if not second_cfg_exists or not _modify_cfg(second_cfg_path, second_cfg_path, True):
                        use_builtin_cfg = True
                if use_builtin_cfg:
                    confirm = input(
                        "修改并安装locale_config.xml未成功，是否使用程序自带备用文件？若需要，请输入Y后按回车键。")
                    if str(confirm).lower() != "y":
                        input("安装已结束，按回车键继续。")
                        return
                else:
                    input("安装已结束，按回车键继续。")
                    return
            if first_cfg_exists:
                with open(first_cfg_path, "w", encoding="utf-8") as file:
                    file.write(text_builtin_cfg)
            if second_dir_exists and second_cfg_exists:
                with open(second_cfg_path, "w", encoding="utf-8") as file:
                    file.write(text_builtin_cfg)
            input("安装已结束，按回车键继续。")
        else:
            if not use_builtin_cfg:
                if not _modify_cfg(first_cfg_path, _get_res_mods_locale_cfg_path(first), False):
                    use_builtin_cfg = True
                if second_dir_exists:
                    if not _modify_cfg(second_cfg_path, _get_res_mods_locale_cfg_path(second), False):
                        use_builtin_cfg = True
                if use_builtin_cfg:
                    confirm = input(
                        "修改并安装locale_config.xml未成功，是否使用程序自带备用文件？若需要，请输入Y后按回车键。")
                    if str(confirm).lower() != "y":
                        input("安装已结束，按回车键继续。")
                        return
                else:
                    input("安装已结束，按回车键继续。")
                    return

            with open(_get_res_mods_locale_cfg_path(first), "w", encoding="utf-8") as file:
                file.write(text_builtin_cfg)
            if second_dir_exists:
                with open(_get_res_mods_locale_cfg_path(second), "w", encoding="utf-8") as file:
                    file.write(text_builtin_cfg)
            input("安装已结束，按回车键继续。")
    else:
        input("已跳过语言配置文件安装，按回车键继续。")


def _get_mo_dir_path(game_version: str, server: str) -> Path:
    return Path("bin").joinpath(game_version).joinpath("res").joinpath("texts").joinpath(server).joinpath(
        "LC_MESSAGES")


def _get_mo_path(game_version: str, server: str) -> Path:
    return Path("bin").joinpath(game_version).joinpath("res").joinpath("texts").joinpath(server).joinpath(
        "LC_MESSAGES").joinpath("global.mo")


def _get_res_mods_mo_path(game_version: str, server: str) -> Path:
    dir_path = Path("bin").joinpath(game_version).joinpath("res_mods").joinpath("texts").joinpath(server).joinpath(
        "LC_MESSAGES")
    os.makedirs(dir_path, exist_ok=True)
    return dir_path.joinpath("global.mo")


def _get_res_path(game_version: str) -> Path:
    return Path("bin").joinpath(game_version).joinpath("res")


def _get_locale_cfg_path(game_version: str) -> Path:
    return Path("bin").joinpath(game_version).joinpath("res").joinpath("locale_config.xml")


def _get_res_mods_locale_cfg_path(game_version: str) -> Path:
    dir_path = Path("bin").joinpath(game_version).joinpath("res_mods")
    os.makedirs(dir_path, exist_ok=True)
    return dir_path.joinpath("locale_config.xml")


def _modify_cfg(cfg_path_old: Path, cfg_path_new: Path, backup: bool) -> bool:
    tree = ETree.parse(cfg_path_old)
    if backup:
        tree_copy = ETree.parse(cfg_path_old)
        tree_copy.write(str(cfg_path_old) + '.old')
    root = tree.getroot()
    executed = False
    for lang_elem in root.findall('.//lang'):
        accept_lang = lang_elem.get('acceptLang')
        if accept_lang == 'ru':
            lang_elem.set('fonts', 'CN')
            lang_elem.set('languageBar', 'true')
            executed = True

    tree.write(cfg_path_new)
    return executed


def _fetch_l10n_mo() -> str:
    print(text_mo_source)
    selection = input(text_mo_source_selection)
    release_selected = selection == '1' or selection == ''
    if release_selected or selection == '2':
        download_settings: List[Dict[str, str]] = _get_download_settings().get('r' if release_selected else 'pt')
        _list_download_server(download_settings)
        download_server_selection_raw = input(text_download_server_selection)
        if download_server_selection_raw == '0':
            return ""
        download_server_selection = 0 if download_server_selection_raw == '' else (
                int(download_server_selection_raw) - 1)
        server: Dict[str, str] = download_settings[download_server_selection]
        return _download_mo(release_selected, server.get('url'), server.get('wrapped'), server.get('delay'))
    return input("请输入您下载的mo文件的绝对路径，您可以尝试将文件直接拖入本程序运行的命令行页面以快速输入：")


def _list_download_server(download_settings: List[Dict[str, str]]):
    if len(download_settings) == 0:
        print("配置文件中没有适用于该类型的下载路线！输入0并回车以重新选择。")
    else:
        print("下载线路：")
        i = 0
        for server in download_settings:
            defaulted = "（默认）" if i == 0 else ""
            server_name = server.get("name")
            print(f"{i + 1}. {defaulted}{server_name}")
            i += 1


def _get_download_settings() -> Dict[str, List[Dict[str, str]]]:
    if not os.path.isfile('l10n_installer/settings/download.json'):
        with open('l10n_installer/settings/download.json', 'w', encoding='utf-8') as file:
            json.dump(download_servers, file, ensure_ascii=False, indent=4)
    with open('l10n_installer/settings/download.json', 'r', encoding='utf-8') as file:
        return json.load(file)


def _download_mo(release: bool, url: str, wrapped: bool, delay: bool) -> str:
    f_suffix = "release" if release else "pt"
    f_prefix = "l10n_" if wrapped else "global_"
    f_ext = "zip" if wrapped else "mo"
    output_file = f"l10n_installer/downloads/{f_prefix}{f_suffix}.{f_ext}"
    proxies = {scheme: proxy for scheme, proxy in urllib.request.getproxies().items()}
    print("连接中……")
    try:
        response = requests.get(url, stream=True, proxies=proxies)
        status = response.status_code
        if status == 200:
            print("连接成功，开始下载……")
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            extracted_file = f"l10n_installer/downloads/global_{f_suffix}.mo"
            print("下载完成！")
            if delay:
                print("请注意，考虑到同步延迟，该线路下载的文件可能不是最新版本。")
            if wrapped:
                print("解压中……")
                with zipfile.ZipFile(output_file, 'r') as mo_zip:
                    manifest_files = [info for info in mo_zip.filelist if info.filename.endswith("MANIFEST.MF")]
                    if manifest_files:
                        manifest_file_name = manifest_files[0].filename
                        mo_zip.extract(manifest_file_name, "l10n_installer/downloads")
                        properties: Dict[str, str] = {}
                        with open(os.path.join("l10n_installer/downloads", manifest_file_name), 'r', encoding='utf-8') \
                                as file:
                            for line in file:
                                if line.strip() and not line.strip().startswith('#'):
                                    key, value = line.strip().split(':', 1)
                                    properties[key] = value.strip()
                        if len(properties) > 0:
                            print(splitter_str)
                            print("汉化包信息：")
                            prop_title = properties.get("Title")
                            if prop_title:
                                print(f"项目名：{prop_title}")
                            prop_author = properties.get("Author")
                            if prop_author:
                                print(f"项目作者：{prop_author}")
                            prop_version = properties.get("Version")
                            if prop_version:
                                print(f"适用版本：{prop_version}")
                            prop_timestamp = properties.get("Timestamp")
                            if prop_timestamp:
                                timestamp_splitted = prop_timestamp.split('T')
                                timestamp_date = timestamp_splitted[0]
                                timestamp_time = timestamp_splitted[1].split('+')[0]
                                print(f"打包时间：{timestamp_date} {timestamp_time}")
                            print(splitter_str)
                            prop_message = properties.get("Message")
                            if prop_message and prop_message.replace(" ", "") != "":
                                print("")
                                print("来自服务器的消息：")
                                print(prop_message)

                    mo_files = [info for info in mo_zip.filelist if info.filename.endswith('.mo')]
                    if mo_files:
                        mo_file_name = mo_files[0].filename
                        mo_zip.extract(mo_file_name, "l10n_installer/downloads")
                        shutil.move(os.path.join("l10n_installer/downloads", mo_file_name),
                                    os.path.join("l10n_installer/downloads", f'global_{f_suffix}.mo'))
                        print("解压完成！")
                        return extracted_file
                    else:
                        print("未在已下载的文件中找到mo文件！请尝试重新下载，或与开发者联系。")
                        return ""
            else:
                return extracted_file
        else:
            print(f"连接失败，返回状态码：{status}")
            return ""
    except requests.exceptions.RequestException as ex:
        print(f"发生异常！异常信息：\n{ex}\n如果您在使用代理，请先关闭代理再尝试！")
        return ""


def _check_mods() -> List[str]:
    files = os.listdir("l10n_installer/mods")
    return [("l10n_installer/mods/" + file) for file in files if (file.endswith(".po") or file.endswith(".mo"))]


def _notify_modification(msgid: str, old_str: str, new_str: str):
    print("")
    print(splitter_str)
    print(f"修改“{msgid}”键：")
    print(old_str)
    print(">>>")
    print(new_str)
    print(splitter_str)
    print("")


def _notify_modification_plural(msgid: str, old_strs: Dict[int, str], new_strs: Dict[int, str]):
    print("")
    print(splitter_str)
    print(f"修改“{msgid}”键：")
    for o in old_strs:
        print(o)
    print(">>>")
    for n in new_strs:
        print(n)
    print(splitter_str)
    print("")


def _notify_addition(msgid: str, new_str: str):
    print("")
    print(splitter_str)
    print(f"添加“{msgid}”键：")
    print(new_str)
    print(splitter_str)
    print("")


def _notify_addition_plural(msgid: str, new_strs: Dict[int, str]):
    print("")
    print(splitter_str)
    print(f"添加“{msgid}”键：")
    for n in new_strs:
        print(n)
    print(splitter_str)
    print("")


def _process_modification_file(source_po, translated_path: str):
    if translated_path.endswith("po"):
        translated = polib.pofile(translated_path)
    else:
        translated = polib.mofile(translated_path)
    source_dict_singular = {entry.msgid: entry.msgstr for entry in source_po}
    translation_dict_singular = {entry.msgid: entry.msgstr for entry in translated if entry.msgid != ""}
    translation_dict_plural: Dict[str, List[str]] = {entry.msgid_plural: entry.msgstr_plural for entry in
                                                     translated if entry.msgid_plural != ""}
    singular_count = len(translation_dict_singular)
    plural_count = len(translation_dict_singular)
    for entry in source_po:
        if singular_count != 0 and entry.msgid and entry.msgid in translation_dict_singular:
            old_str = entry.msgstr
            target_str = translation_dict_singular[entry.msgid]
            del translation_dict_singular[entry.msgid]
            singular_count -= 1
            if entry.msgid == "IDS_RIGHTS_RESERVED":
                continue
            entry.msgstr = target_str
            _notify_modification(entry.msgid, old_str, entry.msgstr)
        if plural_count != 0 and entry.msgid_plural and entry.msgid_plural in translation_dict_plural:
            old_strs = entry.msgstr_plural.copy()
            entry.msgstr_plural = translation_dict_plural.get(entry.msgid_plural)
            _notify_modification_plural(entry.msgid_plural, old_strs, entry.msgstr_plural)
            del translation_dict_plural[entry.msgid_plural]
            plural_count -= 1
    if singular_count > 0 or plural_count > 0:
        for t_entry in translated:
            if t_entry.msgid and t_entry.msgid not in source_dict_singular:
                source_po.append(t_entry)
                if entry.msgid_plural and entry.msgid_plural != "":
                    _notify_addition_plural(t_entry.msgid, t_entry.msgstr_plural)
                else:
                    _notify_addition(t_entry.msgid, t_entry.msgstr)


def _get_report_choice(str_path: str) -> str:
    return f'''
日志文件位于{Path(str_path).absolute().resolve()}
您可以直接退出程序，或进行以下操作：
1.向Gitee仓库镜像报告程序错误，并附上运行目录下的l10n_installer_output.log文件；
2.（需要科学上网）向GitHub仓库报告程序错误，并附上运行目录下的l10n_installer_output.log文件。
'''


class SavedOut(object):
    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for file in self.files:
            file.write(obj)
            file.flush()

    def flush(self):
        for file in self.files:
            file.flush()


os.makedirs('l10n_installer/cache', exist_ok=True)
os.makedirs('l10n_installer/downloads', exist_ok=True)
os.makedirs('l10n_installer/logs', exist_ok=True)
os.makedirs('l10n_installer/mods', exist_ok=True)
os.makedirs('l10n_installer/processed', exist_ok=True)
os.makedirs('l10n_installer/settings', exist_ok=True)
log_file_path = f'l10n_installer/logs/output_{time.time_ns()}.log'
with open(log_file_path, 'w', encoding="utf-8") as log:
    exit_with_confirm = True
    sys.stdout = SavedOut(sys.stdout, log)
    try:
        run()
        if launcher_file != "" and os.path.isfile(launcher_file):
            run_game = input("是否启动战舰世界？输入Y后按回车键启动。")
            if run_game.lower() == "y":
                exit_with_confirm = False
                subprocess.run(launcher_file)
    except Exception as e:
        feedback = input(f"发生异常！异常信息：\n{e}\n\n" + _get_report_choice(log_file_path))
        if feedback == "1":
            webbrowser.open("https://gitee.com/nova-committee/korabli-LESTA-L10N/issues/new")
        elif feedback == "2":
            webbrowser.open("https://github.com/LocalizedKorabli/L10nInstaller/issues/new")
    if exit_with_confirm:
        input("按回车键退出。")

# pyinstaller -i icon.ico --onefile --add-data "resources\*;resources" installer.py --clean
