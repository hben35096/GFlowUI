import gradio as gr
import os
import json
import random
import shutil
import importlib
from func import functions, model_dl

div_line = "-" * 50

self_dir = os.path.abspath(os.path.dirname(__file__))
workflow_dir = os.path.join(self_dir, 'workflow_files')
config_dir = os.path.join(self_dir, 'config_files')

main_config = functions.load_config(os.path.join(config_dir, 'main_config.yaml'))
model_config = functions.load_config(os.path.join(config_dir, main_config.get('model_config_file')))
model_names = list(model_config.keys())
model_name_a = model_names[0]
resolution_list = model_config[model_name_a].get('resolution_list')

# 例子配置，顺便把标题放一起
ex_config = functions.load_config(os.path.join(config_dir, main_config.get('ex_config_file')))
main_name = ex_config.get('main_name')
main_description = ex_config.get('main_description')
main_logo = ex_config.get('main_logo')
examples_dict = ex_config.get('examples_dict')
example_list = list(examples_dict.values())
examples_norm = [t for t in example_list]

WAN_MODELS = ["Wan2.1-T2V-1.3B-480P", "Wan2.1-T2V-14B-720P"]
HUNYUAN_MODELS = ["HunyuanVideo-T2V-720P"]
FLUX_MODELS = ["Flux-T2I-FP16"]
SD35_MODELS = ["SD35-Large-T2I-FP16"]
LTX_MODELS = ["LTX-098-I2V-13B", "LTX-098-T2V-13B"]
HID_MODELS = ["HiDream-I1-T2I"]

NO_CFG_MODELS = HUNYUAN_MODELS + FLUX_MODELS + HID_MODELS
NO_NEG_MODELS = HUNYUAN_MODELS + FLUX_MODELS + SD35_MODELS + HID_MODELS
# NO_SHIFT_MODELS = WAN_MODELS + HUNYUAN_MODELS + FLUX_MODELS + SD35_MODELS + LTX_MODELS


# 迟早要弄成配置表
def get_switch_and_name(model_name):
    cfg_name = 'CFG'
    if model_name in NO_CFG_MODELS:
        if model_name in HID_MODELS:
            cfg_name = '模型采样位移'
        else:
            cfg_name = '条件引导系数'
        
    neg_prompt_display = True
    if model_name in NO_NEG_MODELS:
        neg_prompt_display = False
        
    return cfg_name, neg_prompt_display

cfg_name, neg_prompt_display = get_switch_and_name(model_name_a)

def img_display(model_name):
    model_type = model_config[model_name].get('model_type')
    if model_type in ["I2V", "I2I"]:
        return True
    else:
        return False
        
input_img_display = img_display(model_name_a)

def clear_outputs():
    return None

def model_switch(model_name=None):
    info_t = f"已选择模型 {model_name}"
    gr.Info(info_t, duration=3)
    
    resolution_list = model_config[model_name].get('resolution_list')
    input_img_display = img_display(model_name)
    
    return gr.update(choices=resolution_list, value=resolution_list[0]), input_img_display, gr.update(visible=input_img_display)
    # 更新给 分辨率列表、输入图片存储、输入图片显示项

def seed_update(seed, seed_fixed, all_output):
    if seed_fixed == "🎲" and all_output is not None:
        seed = random.randint(1, 999999999999999)
    return gr.update(value=seed)

def get_workflow(model, scale=None):
    width, height = 0, 0
    workflow_file = f'{model}.json'
    workflow_path = os.path.join(workflow_dir, workflow_file) # 工作流文件路径
    with open(workflow_path, "r") as f:
        workflow = json.load(f)
    # 拆分成宽和高
    if scale is not None:
        width_str, height_str = scale.split("x")
        width = int(width_str)
        height = int(height_str)
    return workflow, width, height

def edit_workflow(model, input_img, steps):
    workflow, _, _ = get_workflow(model)
    # print("看看采样器名称：", sampler_name)
    workflow["1996"]["inputs"]["image"] = input_img
    workflow["1944"]["inputs"]["steps"] = steps

    return workflow


def edit_workflow_ex(model_name, input_img_bg, input_img_fg, zoom, x_move, y_move):
    workflow, _, _ = get_workflow(model_name)
    x, y = functions.get_xy_value(input_img_bg, x_move, y_move)
    print("看看数值：", input_img_bg, x, y)

    if model_name == "LBM-Relight-ex":
        workflow["3"]["inputs"]["image"] = input_img_bg
        workflow["2"]["inputs"]["image"] = input_img_fg

        workflow["16"]["inputs"]["scale_by"] = zoom
        workflow["24"]["inputs"]["offset_x"] = x
        workflow["24"]["inputs"]["offset_y"] = y

    return workflow


def preview_location(launch_state, input_img_bg, input_img_fg, zoom, x_move, y_move):
    app_url, back_app_path, dl_way = launch_state
    if input_img_bg is None or input_img_fg is None:
        gr.Info("背景图或主体图为空", duration=10)
        return None
    model_name = "LBM-Relight-ex"
    workflow = edit_workflow_ex(model_name, input_img_bg, input_img_fg, zoom, x_move, y_move)
    
    from frontend import to_api
    output_file_path_list = to_api.implement(workflow, app_url, back_app_path)
    
    display_outputs = output_file_path_list[0]
    print("看看保存到哪里了", display_outputs)
    return display_outputs

def video_generate(launch_state, input_img_bg, input_img_fg, zoom, x_move, y_move, steps):
    from frontend import to_api
    importlib.reload(to_api) # 实时更改生效，以后就不需要了

    app_url, back_app_path, dl_way = launch_state
    
    workflow_model_name = model_name_a

    output_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(output_dir, exist_ok=True)

    all_output_file_path = []
    model_dl_dict = model_config[workflow_model_name].get('download_way')
    model_dl.check_models(back_app_path, model_dl_dict, dl_way) # 检测模型 合成
    gr.Info("任务已提交，可以到后台查看任务进度", duration=10)

    input_img = preview_location(launch_state, input_img_bg, input_img_fg, zoom, x_move, y_move)
    workflow = edit_workflow(workflow_model_name, input_img, steps)
    
    output_file_path_list = to_api.implement(workflow, app_url, back_app_path)
    # 要复制到工作目录才行
    for generate_file_path in output_file_path_list:
        filename = os.path.basename(generate_file_path)
        target_path = os.path.join(output_dir, filename)
        shutil.copy(generate_file_path, target_path)
        if os.path.exists(target_path):
            print("生成文件已保存到：", target_path)
            all_output_file_path.append(target_path)
    print(div_line)
        
    display_outputs = all_output_file_path[0]
    return (input_img, display_outputs)

js_func = """
function refresh() {
    const url = new URL(window.location);

    if (url.searchParams.get('__theme') !== 'dark') {
        url.searchParams.set('__theme', 'dark');
        window.location.href = url.href;
    }
}
"""
# js_func = None

generate_btn_css="""
.custom-btn {
    height: 90px;
    font-size: 18px;
}
"""
img_h = 396

# 如果是热加载，不能放 def 里面的
def gradio_ui(app_url, back_app_path, dl_way):
    
    with gr.Blocks(theme="soft", js=js_func, css=generate_btn_css) as demo:
        gr.HTML(f"""
        <div style="display: flex; align-items: center; justify-content: flex-start; gap: 12px; margin-bottom: 1.5em;">
          <img src={main_logo} 
               alt="Logo" style="height: 48px; auto;">
          <div>
            <div style="font-size: 22px; font-weight: bold;">{main_name}</div>
            <div style="font-size: 14px; color: gray;">{main_description}</div>
          </div>
        </div>
        """)
        with gr.Column(scale=4):
            with gr.Row():
                input_img_bg = gr.Image(label="上传背景图", interactive=True, type="filepath", height=img_h, scale=4)
                input_img_fg = gr.Image(label="上传主体图", interactive=True, type="filepath", height=img_h, scale=4, visible=True)
    
                # gr.Markdown("#### 编辑主体位置和大小")
                img_preview = gr.Image(label="拼接预览", interactive=False, type="filepath", height=img_h, scale=5, visible=True)
                
                with gr.Column(scale=3, min_width=290, ):
                    
                    with gr.Group():
                        zoom = gr.Slider(value=1, label='🔍 缩放主体', minimum=0.1, maximum=2, step=0.05)
                        x_move = gr.Slider(value=0, label='↔️ 左右位移', minimum=-1.0, maximum=1, step=0.05)
                        y_move = gr.Slider(value=0, label='↕️ 上下位移', minimum=-1.0, maximum=1, step=0.05)
                    prefabricate_btn = gr.Button("🔄 预合成", variant='secondary')
                    steps = gr.Slider(value=20, label='迭代步数 Steps', minimum=1, maximum=128, step=1)
            with gr.Row():
                all_output = gr.ImageSlider(label="生成结果", interactive=False, height=600, type="numpy", scale=9)
                with gr.Column(scale=2, min_width=290, ):
                    generate_btn = gr.Button("生 成", variant="primary", elem_classes="custom-btn")
                    examples = gr.Examples(
                        label="示例", 
                        examples=examples_norm,
                        inputs=[input_img_bg, input_img_fg],
                    )
                                    
        launch_state = gr.State(value=(app_url, back_app_path, dl_way)) # 多个参数放这里方便传递
        img_display_state = gr.State(input_img_display) # 用它来记录吧，别用全局，其实最后没用到
        
        preview_kwargs = {
            "fn": preview_location,
            "inputs": [launch_state, input_img_bg, input_img_fg, zoom, x_move, y_move],
            "outputs": [img_preview]
        }
        prefabricate_btn.click(**preview_kwargs)

        generate_kwargs = {
            "fn": video_generate,
            "inputs": [launch_state, input_img_bg, input_img_fg, zoom, x_move, y_move, steps],
            "outputs": [all_output]
        }
        generate_btn.click(**generate_kwargs)
    return demo

if __name__ == "__main__":
    demo.launch()