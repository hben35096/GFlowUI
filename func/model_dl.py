import os
import shutil
import gradio as gr
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
def ms_model_download(repoid, dir_path, path):
    from modelscope.hub.file_download import model_file_download
    full_file_path = ''
    model_file_download(
        model_id=repoid,
        file_path=path,
        local_dir=dir_path
    )
    full_file_path = os.path.join(dir_path, path)
    return full_file_path
    
# 克隆仓库
def ms_repo_clone(repoid, dir_path):
    wholeness_files = True
    file_paths = get_repo_files(repoid)
    if file_paths:
        for path in file_paths:
            try:
                ms_model_download(repoid, dir_path, path)
            except Exception as e:
                wholeness_files = False
                print(f"❌ 文件 {path} 下载失败")
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


def check_models(back_app_path, model_dl_dict):
    repo_id = model_dl_dict.get('repo_id')
    model_file_dict = model_dl_dict.get('files')
    model_file_list = list(model_file_dict.keys())
    print(f"正在检测模型完整性...") # \n{model_file_list}
    
    model_dir = os.path.join(back_app_path, model_dl_dict.get('basic_dir'))
    
    temp_dir = os.path.join(model_dir, 'temp_models')
    os.makedirs(temp_dir, exist_ok=True)
    
    for file in model_file_list:
        try:
            file_path = os.path.join(model_dir, file)
            if not os.path.exists(file_path): # not
                info_t = f"检测到模型 {os.path.basename(file_path)} 不存在，正在尝试下载，请耐心等待..."
                print(info_t)
                gr.Info(info_t, duration=6)
                remote_file = model_file_dict.get(file)
                temp_file_path = ms_model_download(repo_id, temp_dir, remote_file)
                
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
