import logging

from .socket_client import RemotePCSocketClient

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_communication():
    """通信テスト関数"""
    # テスト用フロントPCのIPアドレス（実際の環境に合わせて変更）
    FRONT_PC_IP = "211.7.126.192"  # 実際のフロントPCのIPアドレスに変更

    client = RemotePCSocketClient(FRONT_PC_IP)

    print("=== Socket通信テスト ===")
    print(f"接続先: {FRONT_PC_IP}:9999")
    print("注意: フロントPCでsocket_server.pyを起動してからテストしてください")

    try:
        # 接続テスト
        print("\n1. 接続テスト...")
        if not client.connect():
            print("❌ 接続失敗")
            return False
        print("✅ 接続成功")

        # テキストメッセージ送信テスト
        print("\n2. テキストメッセージ送信テスト...")
        test_messages = [
            "こんにちは、フロントPC！",
            "受付業務開始の準備ができました",
            "テストメッセージです",
        ]

        for i, message in enumerate(test_messages, 1):
            print(f"  {i}. '{message}' 送信中...")
            if client.send_text_message(message):
                print("    ✅ 送信成功")
            else:
                print("    ❌ 送信失敗")

        # JSON形式メッセージ送信テスト
        print("\n3. JSON形式メッセージ送信テスト...")
        json_tests = [
            ("notification", "受付呼び出し"),
            ("status", "オペレーター待機中"),
            ("command", "アバター表示開始"),
            ("alert", "緊急事態発生"),
        ]

        for i, (msg_type, content) in enumerate(json_tests, 1):
            print(f"  {i}. タイプ:'{msg_type}', 内容:'{content}' 送信中...")
            if client.send_json_message(
                msg_type, content, sender="remote-pc", priority="normal"
            ):
                print("    ✅ 送信成功")
            else:
                print("    ❌ 送信失敗")

        # コマンド送信テスト
        print("\n4. コマンド送信テスト...")
        commands = [
            ("start_avatar", {"avatar_name": "receptionist", "mood": "happy"}),
            ("play_animation", {"animation": "bow", "duration": 3}),
            ("display_message", {"text": "いらっしゃいませ", "duration": 5}),
        ]

        for i, (command, params) in enumerate(commands, 1):
            print(f"  {i}. コマンド:'{command}' 送信中...")
            if client.send_command(command, params):
                print("    ✅ 送信成功")
            else:
                print("    ❌ 送信失敗")

        print("\n✅ 全てのテストが完了しました")
        return True

    except Exception as e:
        logger.error(f"テスト実行エラー: {e}")
        print(f"❌ テスト失敗: {e}")
        return False

    finally:
        client.disconnect()
        print("接続を切断しました")


def interactive_test():
    """対話式テスト"""
    FRONT_PC_IP = input(
        "フロントPCのIPアドレスを入力してください (デフォルト: 192.168.1.100): "
    ).strip()
    if not FRONT_PC_IP:
        FRONT_PC_IP = "192.168.1.100"

    client = RemotePCSocketClient(FRONT_PC_IP)

    try:
        if not client.connect():
            print("❌ 接続できませんでした")
            return

        print("\n=== 対話式メッセージ送信テスト ===")
        print("コマンド:")
        print("  text: <メッセージ> - テキスト送信")
        print("  json: <タイプ> <内容> - JSON送信")
        print("  cmd: <コマンド> - コマンド送信")
        print("  quit - 終了")

        while True:
            try:
                command = input("\n> ").strip()

                if command.lower() == "quit":
                    break
                elif command.startswith("text:"):
                    message = command[5:].strip()
                    client.send_text_message(message)
                elif command.startswith("json:"):
                    parts = command[5:].strip().split(None, 1)
                    if len(parts) >= 2:
                        msg_type, content = parts[0], parts[1]
                        client.send_json_message(msg_type, content)
                    else:
                        print("使用法: json: <タイプ> <内容>")
                elif command.startswith("cmd:"):
                    cmd_name = command[4:].strip()
                    client.send_command(cmd_name)
                else:
                    print("不明なコマンドです")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"エラー: {e}")

    finally:
        client.disconnect()


def main():
    """メイン関数"""
    print("Socket通信テストプログラム")
    print("1. 自動テスト")
    print("2. 対話式テスト")

    choice = input("選択してください (1/2): ").strip()

    if choice == "1":
        test_communication()
    elif choice == "2":
        interactive_test()
    else:
        print("無効な選択です")


if __name__ == "__main__":
    main()
