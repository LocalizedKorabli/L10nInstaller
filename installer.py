# Consumable Camouflage replacer
# Copyright (C) 2024 MikhailTapio
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

import os.path
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
import xml.etree.ElementTree as ETree
import zipfile
from pathlib import Path

import requests

version = "2024.03.24.2339"

available_launchers = [
    "lgc_api.exe",
    "wgc_api.exe"
]

launcher_file = ""

text_welcome_message = f'''战舰世界本地化安装器
作者：北斗余晖
版本：{version}
许可证：GNU-AGPL-3.0-only
源代码地址：https://github.com/Nova-Committee/Korabli-LESTA-L10N/tree/Installer
（国内访问：https://gitee.com/nova-committee/korabli-LESTA-L10N/tree/Installer）
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
1.（实验性）下载最新[正式服]汉化文件；
2.（实验性）下载最新[测试服]汉化文件；
3.使用本地文件。
'''

text_mo_source_selection = "请选择汉化文件来源："

text_use_builtin = "是否使用程序自带备用文件？输入Y以同意。若上次安装后游戏字符仍被显示为空心方块，请考虑使用备用文件。"

text_general_installation_mode = '''全局安装模式
1.快速安装（LESTA服）
2.自定义安装
3.退出程序
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

server_dict: dict[str, str] = {
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
    subdirectories: list[str] = [subdir.name for subdir in folder.iterdir() if subdir.is_dir()]

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

    print(text_mode_selection)
    try:
        mode = int(input(text_general_installation_mode))
    except ValueError:
        mode = 2
    if mode == 3:
        return
    quick = mode == 1
    installation = 0
    server = "ru"
    if not quick:
        print(text_server_list)
        try:
            server = server_dict.get(input(text_select_server))
        except ValueError:
            server = server_dict.get('1')
            print("输入错误，默认为LESTA服")
        print(text_mo_replace_mode)
        try:
            installation = int(input(text_mode_selection))
        except ValueError:
            installation = 0

    if quick or installation == 1:
        shutil.copy(global_mo_path, _get_res_mods_mo_path(first, server))
        if second_dir_exists:
            shutil.copy(global_mo_path, _get_res_mods_mo_path(second, server))
        if not quick:
            input("汉化文件安装完成，请不要退出程序，按回车键继续。")
    elif installation == 2:
        first_mo_path = _get_mo_path(first, server)
        first_mo_found = os.path.isfile(first_mo_path)
        if not first_mo_found:
            print(f"未在{first}版本文件夹下找到global.mo文件")
        else:
            shutil.copy(first_mo_path, str(first_mo_path) + ".old")
        shutil.copy(global_mo_path, first_mo_path)

        second_mo_path = _get_mo_path(second, server)
        second_mo_found = os.path.isfile(second_mo_path)
        if second_dir_exists:
            if not second_mo_found:
                print(f"未在{second}版本文件夹下找到global.mo文件")
            else:
                shutil.copy(second_mo_path, str(second_mo_path) + ".old")
            shutil.copy(global_mo_path, second_mo_path)
        input("汉化文件安装完成，请不要退出程序，按回车键继续。")
    else:
        input("已跳过汉化文件安装，按回车键继续。")

    needs_locale = server == "ru"

    if not quick:
        if not needs_locale:
            installation = 0
        else:
            print(text_locale_cfg_replace_mode)
            try:
                installation = int(input(text_mode_selection))
            except ValueError:
                installation = 0

    use_builtin_cfg = False

    if needs_locale:
        use_builtin_cfg = quick or input(text_use_builtin).lower() == "y"

    if needs_locale and (quick or installation == 1 or installation == 2):
        first_cfg_path = _get_locale_cfg_path(first)
        second_cfg_path = _get_locale_cfg_path(second)
        if not use_builtin_cfg and not os.path.isfile(first_cfg_path) and not os.path.isfile(second_cfg_path):
            print("未在指定的文件夹下找到locale_config.xml文件，将使用程序自带的备用文件。")
            use_builtin_cfg = True
        if installation == 2:
            if not use_builtin_cfg:
                if not _modify_cfg(first_cfg_path, first_cfg_path, True):
                    use_builtin_cfg = True
                if second_dir_exists:
                    if not _modify_cfg(second_cfg_path, second_cfg_path, True):
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
            with open(first_cfg_path, "w", encoding="utf-8") as file:
                file.write(text_builtin_cfg)
            if second_dir_exists:
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


def _get_mo_path(game_version: str, server: str) -> Path:
    return Path("bin").joinpath(game_version).joinpath("res").joinpath("texts").joinpath(server).joinpath(
        "LC_MESSAGES").joinpath("global.mo")


def _get_res_mods_mo_path(game_version: str, server: str) -> Path:
    dir_path = Path("bin").joinpath(game_version).joinpath("res_mods").joinpath("texts").joinpath(server).joinpath(
        "LC_MESSAGES")
    os.makedirs(dir_path, exist_ok=True)
    return dir_path.joinpath("global.mo")


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
    if selection == '1' or '2':
        return _download_mo(selection == '1')
    return input("请输入您下载的mo文件的绝对路径，您可以尝试将文件直接拖入本程序运行的命令行页面以快速输入：")


def _download_mo(release: bool) -> str:
    suffix = "release" if release else "pt"
    artifact_version = "1.0.0" if release else "2.0.0"
    output_file = f"l10n_installer/downloads/l10n_{suffix}.zip"
    artifact_url = "https://maven.nova-committee.cn/releases/korabli/localized/l10n/" \
                   f"{artifact_version}/l10n-{artifact_version}.jar"
    proxies = {scheme: f"{scheme}://{proxy}" for scheme, proxy in urllib.request.getproxies().items()}
    print("连接中……")
    try:
        response = requests.get(artifact_url, proxies=proxies)
        status = response.status_code
        if status == 200:
            print("连接成功，开始下载……")
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print("下载完成！解压中……")
            with zipfile.ZipFile(output_file, 'r') as mo_zip:
                extracted_file = f"l10n_installer/downloads/global_{suffix}.mo"
                mo_files = [info for info in mo_zip.filelist if info.filename.endswith('.mo')]
                if mo_files:
                    mo_file_name = mo_files[0].filename
                    mo_zip.extract(mo_file_name, "l10n_installer/downloads")
                    shutil.move(os.path.join("l10n_installer/downloads", mo_file_name),
                                os.path.join("l10n_installer/downloads", f'global_{suffix}.mo'))
                    print("解压完成！")
                    return extracted_file
                else:
                    print("未在已下载的文件中找到mo文件！请尝试重新下载，或与开发者联系。")
                    return ""
        else:
            print(f"连接失败，返回状态码：{status}")
            return ""
    except requests.exceptions.RequestException as ex:
        print(f"发生异常！异常信息：\n{ex}\n如果您在使用代理，请先关闭代理再尝试！")
        return ""


def get_report_choice(str_path: str) -> str:
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


os.makedirs('l10n_installer/downloads', exist_ok=True)
os.makedirs('l10n_installer/logs', exist_ok=True)
log_file_path = f'l10n_installer/logs/output_{time.time_ns()}.log'
with open(log_file_path, 'w') as log:
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
        feedback = input(f"发生异常！异常信息：\n{e}\n" + get_report_choice(log_file_path))
        if feedback == "1":
            webbrowser.open("https://gitee.com/nova-committee/korabli-LESTA-L10N/issues/new")
        elif feedback == "2":
            webbrowser.open("https://github.com/LocalizedKorabli/L10nInstaller/issues/new")
    if exit_with_confirm:
        input("按回车键退出。")
