import json
import requests
from tqdm import tqdm
import os
import uuid
import websocket

div_line = "-" * 50

def strip_http_prefix(url):
    return url.replace("http://", "").replace("https://", "")

def open_ws(url):
    server = strip_http_prefix(url)
    client_id = str(uuid.uuid4())
    ws = websocket.WebSocket()
    ws.connect(f"ws://{server}/ws?clientId={client_id}")
    return ws, client_id

def tqdm_progress(dict, node, value, max, workflow):
    node_name = workflow[node]["_meta"]["title"]
    if node not in dict:
        # 初始化新的节点进度条
        dict[node] = {
            "bar": tqdm(total=max, desc=f"⏳ {node_name}", unit="step", position=len(dict)),
            "last_value": 0
        }
    
    bar_info = dict[node]
    delta = value - bar_info["last_value"] # 必要的，不然进度条不增长

    if delta > 0:
        bar_info["bar"].update(delta)
        bar_info["last_value"] = value
    # 加上这个可以不二次显示进度条了
    if bar_info["last_value"] == max:
        bar_info["bar"].close()
    return dict

def get_output_path(output_dict_list, app_path_input):
    output_dir = os.path.join(app_path_input, "output")
    file_path_list = []
    for item in output_dict_list:
        for key, value_list in item.items():  # key: "images", "gifs", ...
            for entry in value_list:
                if isinstance(entry, dict):
                    filename = entry.get("filename")
                    subfolder = entry.get("subfolder", "")
                    if filename:
                        full_path = os.path.join(output_dir, subfolder, filename)
                        file_path_list.append(full_path)
    # ✅ 输出路径列表
    return file_path_list
        
def track_ws_progress(ws, prompt_id, workflow, app_path_input):
    print("🟡 开始跟踪进度...") #  WebSocket 
    start_time = None
    end_time = None
    progress_dict = {}
    # last_value = 0
    output_list = []
    output_file_path_list = []
    achieve_nodes = -1

    node_list = list(workflow.keys())
    node_total = len(node_list)
    # 得到节点列表和数量
    for msg in iter(ws.recv, None):
        data = json.loads(msg)
        # print("\n具体数据：\n", data) # 调试
        t = data.get("type")
        d = data.get("data", {})
        # prompt_id 能对上的信息才有价值
        if d.get("prompt_id") == prompt_id:
            if t == "execution_cached":
                cache_nodes = d.get('nodes')
                achieve_nodes += len(cache_nodes)
                if achieve_nodes > 0:
                    print(f"任务总进度：({achieve_nodes}/{node_total})")
                    # progress_dict = tqdm_progress(progress_dict, all_node_progress, achieve_nodes, node_total) # 不要了
            
            elif t == "progress":
                v, m = d.get("value"), d.get("max")
                progress_node = d.get('node')
                progress_dict = tqdm_progress(progress_dict, progress_node, v, m, workflow)
            
            elif t == 'execution_start':
                start_time = d.get('timestamp')
            elif t == 'execution_success':
                end_time = d.get('timestamp')
            elif t == "executing":
                if d.get('node') is not None:
                    achieve_nodes += 1
                    node_num = d.get('node')
                    node_name = workflow[node_num]["_meta"]["title"]
                    print(f"⏩ 正在执行 {node_name} ({achieve_nodes}/{node_total})")
                else:
                    print(f"任务总进度：({node_total}/{node_total})")
                    print("任务结束！")
                    break # 必须停止循环，才能进行下一个任务
            elif t == "executed":
                node_num = d.get('node')
                node_name = workflow[node_num]["_meta"]["title"]
                print(f"\n✅ {node_name} 执行完成")
                output = d.get('output')
                if output is not None:
                    output_list.append(output)
                    

        
    if output_list:
        output_file_path_list = get_output_path(output_list, app_path_input)
        # print("\n".join(output_file_path_list)) # 得到所有输出，以后不需要了
    # 完成时间统计
    if start_time is not None and end_time is not None:
        execution_time = round((end_time - start_time) / 1000, 2)
        print(f"\n🎉 执行完成，耗时：{execution_time} 秒")
    return output_file_path_list

# 提交工作流
def implement(workflow, back_app_url, app_path_input):
    output_file_path_list = []
    ws, client_id = open_ws(back_app_url)
    
    res = requests.post(f"{back_app_url}/prompt", json={"prompt": workflow, "client_id": client_id})
    launch_inf_dict = res.json()
    # print("看看res.json 是什么？？？？", launch_inf_dict)
    prompt_id = launch_inf_dict.get('prompt_id')
    if prompt_id is not None:
        print("✅ 任务提交成功，prompt_id:", prompt_id)
        output_file_path_list = track_ws_progress(ws, prompt_id, workflow, app_path_input)
    else:
        error_dict = launch_inf_dict.get('error')
        if error_dict is not None:
            error_message = error_dict.get('message')
            print("出现报错：", error_message)
    return output_file_path_list
    
if __name__ == "__main__":
    implement()
