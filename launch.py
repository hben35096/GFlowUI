import argparse
import os
import subprocess

parser = argparse.ArgumentParser(description="GFlowUI 启动脚本", add_help=True)
parser.add_argument('--back-port', nargs='?', const=8188, default=8188, type=int, help='指定后端服务端口号，不指定则为8188')
parser.add_argument('--port', nargs='?', const=7860, default=7860, type=int, help='指定前端服务端口号，不指定则为7860') # default 完全不提供 --port 的情况下
args = parser.parse_args()

self_dir = os.path.abspath(os.path.dirname(__file__))
back_app_path = os.path.join(self_dir, 'backend', 'ComfyUI')
launch_keywords = ["Python version:", "Total VRAM", "pytorch version:", "device detected:"]


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
                    from frontend import common as grui
                    demo = grui.gradio_ui(app_url, back_app_path)
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


command = command = ["python", "main.py"] + [f"--port={int(args.back_port)}"]
launch_app(command, back_app_path)
