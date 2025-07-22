import os
import shutil
import gradio as gr

# autodl 模型下载，备用
def cg_model_download(dir_path, repoid, file):
    import codewithgpu as cg
    full_file_path = ''
    
    folder_name = repoid.split('/')[1]
    dl_link = f"{repoid.strip()}/{file.strip()}"
    cg.model.download(dl_link, dir_path)
    
    full_file_path = os.path.join(dir_path, folder_name, file)
    return full_file_path

# ############################ 魔搭下载的
# 获取仓库文件列表
def get_repo_files(repoid):
    from modelscope.hub.api import HubApi
    api = HubApi()
    file_paths = []
    try:
        files = api.get_model_files(
            model_id=repoid,
            root=None,
            recursive=True
        )
        
        file_paths = [f['Path'] for f in files if f.get('Type') == 'blob']
        return file_paths
    except Exception as e:
        print(f"❌ 获取仓库 {repoid} 文件列表失败：\n", e)

# 单文件下载
def ms_model_download(dir_path, repoid, file):
    from modelscope.hub.file_download import model_file_download
    full_file_path = ''
    model_file_download(
        model_id=repoid,
        file_path=file,
        local_dir=dir_path
    )
    full_file_path = os.path.join(dir_path, file)
    return full_file_path
    
# 克隆仓库
def ms_repo_clone(repoid, dir_path):
    wholeness_files = True
    file_paths = get_repo_files(repoid)
    if file_paths:
        for file in file_paths:
            try:
                ms_model_download(dir_path, repoid, file)
            except Exception as e:
                wholeness_files = False
                print(f"❌ 文件 {file} 下载失败")
    return wholeness_files

# 检测本地文件是否齐全，应该没什么用
def check_repo_wholeness(repoid, dir_path):
    absence = False
    if not os.path.exists(dir_path):
        absence = True
    else:
        file_paths = get_repo_files(repoid)
        if file_paths:
            for path in file_paths:
                if not os.path.exists(os.path.join(dir_path, path)):
                    absence = True
    return absence

# 模型检测和下载，现在支持两种下载方式
# 可能要统一成用拆分法，这样可以去拿不同仓库的文件
def check_models(back_app_path, model_dl_dict, dl_way):
    if dl_way not in model_dl_dict:
        dl_way = list(model_dl_dict.keys())[0] # 用第一个就对了

    # repo_id = model_dl_dict[dl_way].get('repo_id')
    model_file_dict = model_dl_dict[dl_way].get('files')
    model_file_list = list(model_file_dict.keys())
    print(f"正在检测模型完整性...") # \n{model_file_list}
    model_dir = os.path.join(back_app_path, model_dl_dict[dl_way].get('basic_dir'))
    
    temp_dir = os.path.join(model_dir, 'temp_models')
    os.makedirs(temp_dir, exist_ok=True)
    
    for file in model_file_list:
        try:
            file_path = os.path.join(model_dir, file)
            if not os.path.exists(file_path): # not
                info_t = f"检测到模型 {os.path.basename(file_path)} 不存在，正在尝试下载，请耐心等待..."
                print(info_t)
                gr.Info(info_t, duration=6)
                
                remote_file_link = model_file_dict.get(file)
                parts = remote_file_link.split('/', 2)  # 最多拆 3 段
                repo_id = f"{parts[0]}/{parts[1]}"
                remote_file = parts[2]
                
                if dl_way == "ms":
                    temp_file_path = ms_model_download(temp_dir, repo_id, remote_file)
                elif dl_way == "cg":
                    temp_file_path = cg_model_download(temp_dir, repo_id, remote_file)
                    if not os.path.exists(temp_file_path):
                        print("“cg” 下载方式失败，改成从 ModelScope 下载")
                        temp_file_path = ms_model_download(temp_dir, repo_id, remote_file)
                
                if os.path.exists(temp_file_path):
                    shutil.move(temp_file_path, file_path)
                if os.path.exists(file_path):
                    print('文件已下载到：', file_path)
        except KeyboardInterrupt:
            print("\n❌ 用户中断了进程")
        except Exception as e:
            print(f"❌ 下载过程发生错误: {e}")
            if "please try again" in str(e):
                print("报错信息显示，可以尝试点击按钮重新下载")
        # 可能还要返回一个模型路径字典
