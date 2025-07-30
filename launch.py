import argparse
import os
import subprocess

parser = argparse.ArgumentParser(description="GFlowUI 启动脚本", add_help=True)
parser.add_argument('--back-port', nargs='?', const=8188, default=8188, type=int, help='指定后端服务端口号，不指定则为8188')
parser.add_argument('--port', nargs='?', const=7860, default=7860, type=int, help='指定前端服务端口号，不指定则为7860') # default 完全不提供 --port 的情况下
parser.add_argument('--dl-way', nargs='?', const='ms', default='ms', help='指定缺失模型下载方式，如 ms 或 cg')
parser.add_argument('--ui-test', action='store_true', help="允许在不启动后端的模式下启动，以测试部分UI功能")
args = parser.parse_args()

self_dir = os.path.abspath(os.path.dirname(__file__))
back_app_path = os.path.join(self_dir, 'backend', 'comfyui_musa')
launch_keywords = ["Python version:", "Total VRAM", "pytorch version:", "device detected:"]

# 未使用，备用于模型下载方式，需要结合配置表
if args.dl_way not in ['ms', 'cg']:
    print(f"⚠️  不支持的下载方式: '{args.dl_way}'，将使用默认方式 'ms'")
    args.dl_way = 'ms'

def launch_app(command, back_app_path=None):
    app_url = None
    url_prefix = "To see the GUI go to:"
    try:
        process = subprocess.Popen(
            command,
            cwd=back_app_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        percentage_line_seen = False
        for line in process.stdout:
            if url_prefix in line:
                line = line.strip()
                # print(line)
                if line.startswith(url_prefix):
                    app_url = line[len(url_prefix):].strip()

                if app_url:
                    print("✅ 后端启动完成")
                    # from frontend import common as grui
                    # from frontend import audio_ui as grui
                    from frontend import re_paint as grui
                    demo = grui.gradio_ui(app_url, back_app_path, args.dl_way)
                    demo.launch(server_port=int(args.port),)
            elif any(keyword in line for keyword in launch_keywords):
                print(line.strip())
            # else:
            #     print(line.strip())
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)
    except KeyboardInterrupt:
        print("\n❌ 用户中断了进程")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    if args.ui_test:
        app_url = "http://127.0.0.1:8188"
        # from frontend import common as grui
        # from frontend import audio_ui as grui
        from frontend import re_paint as grui
        demo = grui.gradio_ui(app_url, back_app_path, args.dl_way)
        demo.launch(server_port=int(args.port),)
    else:
        command = command = ["python", "main.py"] + [f"--port={int(args.back_port)}"]
        launch_app(command, back_app_path)
