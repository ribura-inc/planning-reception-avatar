# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

# プロジェクトのルートディレクトリを取得
ROOT_DIR = Path(SPECPATH).resolve()

# OSに応じたアイコンファイルを選択
if sys.platform == 'darwin':
    icon_file = str(ROOT_DIR / 'assets' / 'icon.icns')
elif sys.platform == 'win32':
    icon_file = str(ROOT_DIR / 'assets' / 'icon.ico')
else:
    icon_file = str(ROOT_DIR / 'assets' / 'icon.png')

a = Analysis(
    ['src/front/main.py'],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('credentials.json', '.') if os.path.exists('credentials.json') else ('', ''),
    ],
    hiddenimports=[
        'fastapi',
        'uvicorn',
        'websockets',
        'google.auth',
        'google.oauth2',
        'google_auth_oauthlib',
        'googleapiclient',
        'google_apps_meet',
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.common.by',
        'selenium.webdriver.support',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.expected_conditions',
        'psutil',
        'pyautogui',
        'pydantic',
        'pydantic_settings',
        'aiofiles',
        'httpx',
        'tenacity',
        'structlog',
        'click',
        'dotenv',
        'flet',
        'flet_core',
        'flet_runtime',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
    ],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='VTuber受付システム_フロント' if sys.platform == 'darwin' else 'VTuberReceptionFront',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUIアプリケーションとして動作
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

# macOS用のアプリケーションバンドル作成
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='VTuber受付システム_フロント.app',
        icon=icon_file,
        bundle_identifier='com.ribura.vtuber-reception-front',
        info_plist={
            'CFBundleName': 'VTuber受付システム フロント',
            'CFBundleDisplayName': 'VTuber受付システム フロント',
            'CFBundleGetInfoString': "VTuber Hotel Reception System - Front",
            'CFBundleIdentifier': 'com.ribura.vtuber-reception-front',
            'CFBundleVersion': '0.1.0',
            'CFBundleShortVersionString': '0.1.0',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.15.0',
            'NSRequiresAquaSystemAppearance': False,
            'NSMicrophoneUsageDescription': 'このアプリケーションはGoogle Meetでの通話のためにマイクを使用します。',
            'NSCameraUsageDescription': 'このアプリケーションはGoogle Meetでの通話のためにカメラを使用します。',
        },
    )