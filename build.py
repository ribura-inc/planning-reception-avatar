"""
VTuber受付システム ビルドスクリプト
Windows/Mac両対応の実行ファイル生成
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# プロジェクトルートディレクトリ
ROOT_DIR = Path(__file__).parent.resolve()
BUILD_DIR = ROOT_DIR / "dist"


def print_header(message: str):
    """ヘッダーメッセージを表示"""
    print("=" * 60)
    print(f"  {message}")
    print("=" * 60)


def print_info(message: str):
    """情報メッセージを表示"""
    print(f"[INFO] {message}")


def print_error(message: str):
    """エラーメッセージを表示"""
    print(f"[ERROR] {message}", file=sys.stderr)


def print_success(message: str):
    """成功メッセージを表示"""
    print(f"[SUCCESS] ✅ {message}")


def check_pyinstaller():
    """PyInstallerがインストールされているか確認"""
    try:
        import PyInstaller

        print_info(f"PyInstaller {PyInstaller.__version__} が見つかりました")
        return True
    except ImportError:
        print_error("PyInstallerがインストールされていません")
        print_info("インストール中...")
        try:
            subprocess.run(
                ["rye", "add", "--dev", "pyinstaller"], check=True, capture_output=True
            )
            subprocess.run(["rye", "sync"], check=True, capture_output=True)
            print_success("PyInstallerをインストールしました")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"PyInstallerのインストールに失敗しました: {e}")
            return False


def check_credentials():
    """credentials.jsonの存在を確認"""
    cred_file = ROOT_DIR / "credentials.json"
    if cred_file.exists():
        print_info("credentials.json が見つかりました")
        return True
    else:
        print_info("credentials.json が見つかりません（ビルドは続行します）")
        print_info("  → Google Meet機能を使用する場合は、実行時に設定が必要です")
        return False


def clean_build():
    """以前のビルド結果をクリーンアップ"""
    print_info("以前のビルド結果をクリーンアップ中...")

    # distディレクトリをクリーンアップ
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    # buildディレクトリをクリーンアップ
    build_dir = ROOT_DIR / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)

    print_success("クリーンアップが完了しました")


def build_app(spec_file: str, app_name: str):
    """アプリケーションをビルド"""
    print_header(f"{app_name} のビルド")

    spec_path = ROOT_DIR / spec_file
    if not spec_path.exists():
        print_error(f"{spec_file} が見つかりません")
        return False

    print_info(f"ビルド中: {spec_file}")

    try:
        # PyInstallerを実行
        cmd = ["rye", "run", "pyinstaller", str(spec_path), "--clean", "--noconfirm"]
        result = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)

        if result.returncode != 0:
            print_error(f"ビルドに失敗しました:\n{result.stderr}")
            return False

        print_success(f"{app_name} のビルドが完了しました")
        return True

    except Exception as e:
        print_error(f"ビルド中にエラーが発生しました: {e}")
        return False


def list_build_results():
    """ビルド結果を表示"""
    print_header("ビルド結果")

    if not BUILD_DIR.exists():
        print_error("ビルド結果が見つかりません")
        return

    system = platform.system()

    if system == "Darwin":  # macOS
        apps = list(BUILD_DIR.glob("*.app"))
        if apps:
            print_info("生成されたアプリケーション:")
            for app in apps:
                size_mb = sum(f.stat().st_size for f in app.rglob("*")) / (1024 * 1024)
                print(f"  • {app.name} ({size_mb:.1f} MB)")
                print(f"    場所: {app}")

    elif system == "Windows":
        exes = list(BUILD_DIR.glob("*.exe"))
        if exes:
            print_info("生成された実行ファイル:")
            for exe in exes:
                size_mb = exe.stat().st_size / (1024 * 1024)
                print(f"  • {exe.name} ({size_mb:.1f} MB)")
                print(f"    場所: {exe}")

    else:  # Linux等
        executables = [
            f for f in BUILD_DIR.iterdir() if f.is_file() and f.stat().st_mode & 0o111
        ]
        if executables:
            print_info("生成された実行ファイル:")
            for exe in executables:
                size_mb = exe.stat().st_size / (1024 * 1024)
                print(f"  • {exe.name} ({size_mb:.1f} MB)")
                print(f"    場所: {exe}")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="VTuber受付システムのビルドスクリプト")
    parser.add_argument(
        "--target",
        choices=["front", "remote", "both"],
        default="both",
        help="ビルドするターゲット (default: both)",
    )
    parser.add_argument(
        "--clean", action="store_true", help="ビルド前にクリーンアップを実行"
    )
    parser.add_argument(
        "--no-check", action="store_true", help="事前チェックをスキップ"
    )

    args = parser.parse_args()

    print_header("VTuber受付システム ビルドスクリプト")

    # OS情報を表示
    system = platform.system()
    arch = platform.machine()
    print_info(f"OS: {system} ({arch})")
    print_info(f"Python: {sys.version.split()[0]}")

    # 事前チェック
    if not args.no_check:
        if not check_pyinstaller():
            print_error("PyInstallerのセットアップに失敗しました")
            return 1

        check_credentials()

    # slack通知の確認
    print("🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨")
    print("SLACK_WEBHOOK_URLを文字列で設定してください (src/utils/slack.py)")
    print("🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨")
    input("すでに記入済みの場合はEnterキーを押して続行...")

    # クリーンアップ
    if args.clean:
        clean_build()

    # ビルド実行
    success = True

    if args.target in ["front", "both"]:
        if not build_app("front.spec", "フロントアプリケーション"):
            success = False

    if args.target in ["remote", "both"]:
        if not build_app("remote.spec", "リモートアプリケーション"):
            success = False

    # 結果表示
    if success:
        list_build_results()
        print_header("ビルド完了")
        print_success("すべてのビルドが正常に完了しました！")
        print_info(f"実行ファイルは {BUILD_DIR} に生成されました")

        # OS別の実行方法を案内
        if system == "Darwin":
            print_info("\n実行方法:")
            print_info("  1. Finderで dist フォルダを開く")
            print_info("  2. .app ファイルをダブルクリック")
            print_info("  または")
            print_info("  $ open dist/*.app")
        elif system == "Windows":
            print_info("\n実行方法:")
            print_info("  1. エクスプローラーで dist フォルダを開く")
            print_info("  2. .exe ファイルをダブルクリック")
            print_info("  または")
            print_info("  > .\\dist\\VTuberReceptionFront.exe")
            print_info("  > .\\dist\\VTuberReceptionRemote.exe")

        return 0
    else:
        print_error("ビルドに失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
